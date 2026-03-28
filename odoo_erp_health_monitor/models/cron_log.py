from odoo import models, fields, api
from datetime import datetime, timedelta

class ErpHealthCronLog(models.Model):
    _name = 'erp.health.cron.log'
    _description = 'Cron Job Execution Log'
    _order = 'execution_date desc'

    cron_id = fields.Many2one('ir.cron', string='Cron Job', readonly=True, ondelete='cascade')
    cron_name = fields.Char(string='Job Name', readonly=True)
    execution_date = fields.Datetime(string='Execution Date', readonly=True, default=fields.Datetime.now)
    duration = fields.Float(string='Duration (seconds)', readonly=True)
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed')
    ], string='Status', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    is_slow = fields.Boolean(string='Slow Execution', compute='_compute_is_slow', store=True)

    @api.depends('duration')
    def _compute_is_slow(self):
        threshold = float(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_erp_health_monitor.slow_cron_threshold', '10.0'
        ))
        for record in self:
            record.is_slow = record.duration and record.duration > threshold