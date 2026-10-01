import logging

from odoo import api, fields, models

from .aam_constants import PARAM_ENABLED

_logger = logging.getLogger(__name__)


class AamAuditLog(models.Model):
    """Record of access denials and login activity.

    Rule *changes* are already tracked by the chatter on ``aam.rule``; this
    model is for the things chatter cannot capture - a user hitting a wall, or
    signing in and out. Denial logging is off by default because a
    misconfigured rule on a busy model can write thousands of rows an hour.
    """

    _name = 'aam.audit.log'
    _description = 'Access Audit Log'
    _order = 'create_date desc, id desc'
    _rec_name = 'summary'

    user_id = fields.Many2one('res.users', 'User', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', 'Company', index=True)
    event_type = fields.Selection(
        [('denial', 'Access Denied'),
         ('login', 'Login'),
         ('logout', 'Logout'),
         ('login_blocked', 'Login Blocked'),
         ('impersonate', 'Impersonation')],
        required=True, index=True)
    model_name = fields.Char('Model', index=True)
    res_id = fields.Integer('Record ID')
    operation = fields.Char('Operation')
    rule_id = fields.Many2one('aam.rule', 'Caused By', ondelete='set null')
    detail = fields.Text()
    summary = fields.Char(compute='_compute_summary')

    @api.depends('event_type', 'user_id', 'model_name', 'operation')
    def _compute_summary(self):
        labels = dict(self._fields['event_type'].selection)
        for log in self:
            parts = [labels.get(log.event_type, log.event_type), log.user_id.name or '']
            if log.model_name:
                parts.append('%s (%s)' % (log.model_name, log.operation or 'read'))
            log.summary = ' - '.join(p for p in parts if p)

    @api.model
    def _log(self, event_type, **values):
        """Write a log row without ever breaking the caller.

        Audit logging must not be able to turn a denial into a traceback, so
        every failure here is swallowed.

        Denials are written on a **separate cursor** because an AccessError
        rolls the request back and would take the log row with it. Everything
        else is written on the current cursor, and that distinction matters:
        a separate cursor inserting a row whose foreign key points at a
        res_users row the main transaction is mid-UPDATE on (force logout does
        exactly that) blocks on the FK lock and loses the row.
        """
        if not self._logging_enabled(event_type):
            return
        values.update({
            'event_type': event_type,
            'user_id': values.get('user_id') or self.env.uid,
            'company_id': values.get('company_id') or self.env.company.id,
        })
        try:
            if event_type == 'denial':
                with self.pool.cursor() as cr:
                    self.with_env(self.env(cr=cr)).sudo().create(values)
            else:
                self.sudo().create(values)
        except Exception:  # pragma: no cover - logging must never raise
            _logger.warning("Could not write access audit log (%s)", event_type,
                            exc_info=True)

    @api.model
    def _logging_enabled(self, event_type):
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param(PARAM_ENABLED, '1') not in ('1', 'True', 'true'):
            return False
        if event_type == 'denial':
            return params.get_param('aam.log_denials') in ('1', 'True', 'true')
        return params.get_param('aam.log_activity', '1') in ('1', 'True', 'true')

    @api.autovacuum
    def _gc_audit_log(self):
        """Drop rows older than the configured retention (default 90 days)."""
        days = int(self.env['ir.config_parameter'].sudo().get_param(
            'aam.log_retention_days', 90) or 90)
        if days <= 0:
            return
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        self.sudo().search([('create_date', '<', cutoff)]).unlink()
