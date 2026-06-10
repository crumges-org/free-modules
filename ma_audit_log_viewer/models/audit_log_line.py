from odoo import fields, models

_MAX_LEN = 500


class AuditLogLine(models.Model):
    _name = 'audit.log.line'
    _description = 'Audit Log Line'
    _order = 'date desc, id desc'
    _rec_name = 'res_name'
    _log_access = False

    config_id = fields.Many2one('audit.config', ondelete='cascade', index=True)
    model_name = fields.Char(index=True)
    res_id = fields.Integer()
    res_name = fields.Char()
    field_name = fields.Char()
    field_label = fields.Char()
    old_value = fields.Char(size=_MAX_LEN)
    new_value = fields.Char(size=_MAX_LEN)
    user_id = fields.Many2one('res.users', ondelete='set null', index=True)
    operation = fields.Selection([
        ('create', 'Create'),
        ('write', 'Write'),
        ('unlink', 'Unlink'),
    ], index=True)
    date = fields.Datetime(default=fields.Datetime.now, index=True)

    def action_view_diff(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'audit.log.line',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'flags': {'mode': 'readonly'},
        }
