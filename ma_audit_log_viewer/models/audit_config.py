import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)
_MAX_LEN = 500
_SKIP_TYPES = frozenset({'binary'})


class AuditConfig(models.Model):
    _name = 'audit.config'
    _description = 'Audit Configuration'
    _rec_name = 'model_id'

    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', store=True, index=True)
    field_ids = fields.Many2many(
        'ir.model.fields',
        'audit_config_field_rel',
        'config_id',
        'field_id',
        domain="[('model_id', '=', model_id), ('ttype', 'not in', ['binary', 'one2many'])]",
        string='Fields to Track',
    )
    notify_user_id = fields.Many2one(
        'res.users', ondelete='set null', string='Alert Recipient'
    )
    notify_on_field_ids = fields.Many2many(
        'ir.model.fields',
        'audit_config_notify_rel',
        'config_id',
        'field_id',
        domain="[('id', 'in', field_ids)]",
        string='Alert on Field Change',
    )
    retention_days = fields.Integer(
        default=30, required=True, string='Keep Logs (days)'
    )
    active = fields.Boolean(default=True)

    # ------------------------------------------------------------------
    # Registry hook — patch configured models at startup
    # ------------------------------------------------------------------

    @api.model
    def _register_hook(self):
        super()._register_hook()
        self._setup_audit_hooks()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._setup_audit_hooks()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'model_id' in vals or 'active' in vals:
            self._setup_audit_hooks()
        return result

    def _setup_audit_hooks(self):
        configs = self.sudo().search([('active', '=', True)])
        for model_name in set(configs.mapped('model_name')):
            if not model_name or model_name not in self.env:
                continue
            model_cls = type(self.env[model_name])
            if getattr(model_cls, '_audit_hooked', False):
                continue
            self._patch_model_class(model_cls, model_name)
            _logger.info('audit_log_viewer: hooked %s', model_name)

    @api.model
    def _patch_model_class(self, model_cls, model_name: str):
        original_write = model_cls.write
        original_create = model_cls.create
        original_unlink = model_cls.unlink
        model_cls._audit_hooked = True

        # ---- write ----
        def _audit_write(self_rec, vals):
            config = self_rec.env['audit.config']._get_active_config(model_name)
            if not config:
                return original_write(self_rec, vals)
            tracked = {f.name for f in config.field_ids}
            relevant = [k for k in vals if k in tracked]
            if not relevant:
                return original_write(self_rec, vals)

            # Batch guard — more than 500 records: log summary only
            if len(self_rec) > 500:
                result = original_write(self_rec, vals)
                self_rec.env['audit.log.line'].sudo().create({
                    'config_id': config.id,
                    'model_name': model_name,
                    'res_id': 0,
                    'res_name': f'{len(self_rec)} records',
                    'field_name': '[batch]',
                    'field_label': '[batch]',
                    'old_value': f'{len(self_rec)} records changed',
                    'new_value': '',
                    'user_id': self_rec.env.uid,
                    'operation': 'write',
                })
                return result

            before = {
                rec.id: config._read_field_values(rec, relevant)
                for rec in self_rec
            }
            result = original_write(self_rec, vals)
            all_lines = []
            for rec in self_rec:
                after = config._read_field_values(rec, relevant)
                lines = config._log_changes(rec, before[rec.id], after, 'write')
                all_lines.extend(lines)

            # Alert — single-record writes only
            if (
                len(self_rec) == 1
                and all_lines
                and config.notify_user_id
                and config.notify_on_field_ids
            ):
                notify_fnames = set(config.notify_on_field_ids.mapped('name'))
                for ld in all_lines:
                    if ld['field_name'] in notify_fnames:
                        config._send_alert(self_rec, ld)
                        break

            return result

        # ---- create ----
        def _audit_create(self_rec, vals_list):
            config = self_rec.env['audit.config']._get_active_config(model_name)
            if not config:
                return original_create(self_rec, vals_list)
            records = original_create(self_rec, vals_list)
            tracked = [f.name for f in config.field_ids]
            for rec in records:
                after = config._read_field_values(rec, tracked)
                before = {fname: '' for fname in after}
                config._log_changes(rec, before, after, 'create')
            return records

        # ---- unlink ----
        def _audit_unlink(self_rec):
            config = self_rec.env['audit.config']._get_active_config(model_name)
            if not config:
                return original_unlink(self_rec)
            tracked = [f.name for f in config.field_ids]
            snapshots = {}
            for rec in self_rec:
                snapshots[rec.id] = {
                    'name': (rec.display_name or '')[:_MAX_LEN],
                    'vals': config._read_field_values(rec, tracked),
                }
            result = original_unlink(self_rec)
            for rec_id, snap in snapshots.items():
                for fname, old_val in snap['vals'].items():
                    field = self_rec._fields.get(fname)
                    self_rec.env['audit.log.line'].sudo().create({
                        'config_id': config.id,
                        'model_name': model_name,
                        'res_id': rec_id,
                        'res_name': snap['name'],
                        'field_name': fname,
                        'field_label': field.string if field else fname,
                        'old_value': old_val,
                        'new_value': '',
                        'user_id': self_rec.env.uid,
                        'operation': 'unlink',
                    })
            return result

        model_cls.write = _audit_write
        model_cls.create = _audit_create
        model_cls.unlink = _audit_unlink

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @api.model
    def _get_active_config(self, model_name: str):
        return self.sudo().search(
            [('model_name', '=', model_name), ('active', '=', True)],
            limit=1,
        )

    def _field_to_str(self, field, val) -> str:
        if val is False or val is None:
            return ''
        if field.type == 'many2one':
            return (val.display_name or '') if val else ''
        if field.type in ('many2many', 'one2many'):
            return ', '.join(val.mapped('display_name'))
        s = str(val)
        if len(s) > 10000:
            return s[:_MAX_LEN] + ' [truncated]'
        return s[:_MAX_LEN]

    def _read_field_values(self, record, fnames) -> dict:
        result = {}
        for fname in fnames:
            field = record._fields.get(fname)
            if not field or field.type in _SKIP_TYPES:
                continue
            result[fname] = self._field_to_str(field, record[fname])
        return result

    def _log_changes(self, record, before: dict, after: dict, operation: str) -> list:
        lines = []
        for fname, new_val in after.items():
            old_val = before.get(fname, '')
            if operation == 'write' and old_val == new_val:
                continue
            field = record._fields.get(fname)
            lines.append({
                'config_id': self.id,
                'model_name': self.model_name,
                'res_id': record.id,
                'res_name': (record.display_name or '')[:_MAX_LEN],
                'field_name': fname,
                'field_label': field.string if field else fname,
                'old_value': old_val,
                'new_value': new_val,
                'user_id': record.env.uid,
                'operation': operation,
            })
        if lines:
            self.env['audit.log.line'].sudo().create(lines)
        return lines

    # ------------------------------------------------------------------
    # Alert
    # ------------------------------------------------------------------

    def _send_alert(self, record, log_data: dict):
        subject = (
            f"Audit Alert: {log_data['field_label']} changed on {log_data['res_name']}"
        )
        body = (
            f"<p><b>{log_data['field_label']}</b> changed on "
            f"<b>{log_data['res_name']}</b>:</p>"
            f"<ul>"
            f"<li><b>From:</b> {log_data['old_value'] or '(empty)'}</li>"
            f"<li><b>To:</b> {log_data['new_value'] or '(empty)'}</li>"
            f"</ul>"
        )
        self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body,
            'email_to': self.notify_user_id.email,
            'auto_delete': True,
        }).send()

    # ------------------------------------------------------------------
    # Retention cron
    # ------------------------------------------------------------------

    @api.model
    def _cron_delete_old_logs(self):
        for config in self.search([('active', '=', True), ('retention_days', '>', 0)]):
            cutoff = fields.Datetime.now() - timedelta(days=config.retention_days)
            domain = [('config_id', '=', config.id), ('date', '<', cutoff)]
            deleted = 0
            while True:
                batch = self.env['audit.log.line'].sudo().search(domain, limit=1000)
                if not batch:
                    break
                deleted += len(batch)
                batch.unlink()
            if deleted:
                _logger.info(
                    'audit_log_viewer: deleted %d old log lines for %s',
                    deleted,
                    config.model_name,
                )
