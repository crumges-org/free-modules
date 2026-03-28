from odoo import api, fields, models


class KwCrmStageHistory(models.Model):
    _name = 'kw.crm.stage.history'
    _description = 'CRM Stage Change History'
    _order = 'date_in desc'

    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        string='Lead/Opportunity',
        required=True,
        ondelete='cascade',
        index=True,
    )
    stage_from_id = fields.Many2one(
        comodel_name='crm.stage',
        string='Stage From',
        ondelete='restrict',
    )
    stage_to_id = fields.Many2one(
        comodel_name='crm.stage',
        string='Stage To',
        required=True,
        ondelete='restrict',
    )
    date_in = fields.Datetime()
    date_in_by_id = fields.Many2one(
        comodel_name='res.users',
        string='Date In By',
    )
    date_out = fields.Datetime()
    date_out_by_id = fields.Many2one(
        comodel_name='res.users',
        string='Date Out By',
    )
    day_diff = fields.Integer(
        compute='_compute_time_diff',
        store=True,
    )
    time_diff = fields.Float(
        string='Time Diff (Hours)',
        compute='_compute_time_diff',
        store=True,
    )
    total_time_diff = fields.Float(
        compute='_compute_time_diff',
        store=True,
    )

    @api.depends('date_in', 'date_out')
    def _compute_time_diff(self):
        for rec in self:
            if rec.date_in and rec.date_out:
                delta = rec.date_out - rec.date_in
                total_seconds = delta.total_seconds()
                rec.day_diff = delta.days
                rec.time_diff = (total_seconds % 86400) / 3600.0
                rec.total_time_diff = total_seconds / 3600.0
            else:
                rec.day_diff = 0
                rec.time_diff = 0.0
                rec.total_time_diff = 0.0
