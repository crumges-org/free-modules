# Powered by Sensible Consulting Services
# -*- coding: utf-8 -*-
# © 2025 Sensible Consulting Services (<https://sensiblecs.com/>)
import ast

from odoo import fields, models, api


class SblDynamicPortalKpisLine(models.Model):
    _name = 'sbl.dynamic.portal.kpis.line'
    _inherit = ['image.mixin']
    _description = 'Dynamic Portal Kpis Line'
    _order = 'sequence'

    sbl_dynamic_portal_id = fields.Many2one('sbl.dynamic.portal', string='Dynamic Portal')
    sbl_dynamic_portal_dashboard_id = fields.Many2one('sbl.dynamic.portal', string='Dynamic Portal Dashboard')
    sequence = fields.Integer()
    name = fields.Char(required=True)
    sbl_domain = fields.Char('Domain')
    sbl_model_name = fields.Char(string='Model Name')
    sbl_color = fields.Char('Card Color', default="#875A7B")
    sbl_record_count = fields.Integer('Record Count', compute='_compute_sbl_record_count')
    sbl_chart_color = fields.Char('Color in Chart')

    @api.depends('sbl_domain', 'sbl_model_name')
    def _compute_sbl_record_count(self):
        for rec in self:
            count = 0
            domain = []
            if rec.sbl_domain and rec.sbl_model_name:
                if rec.sbl_domain:
                    domain += ast.literal_eval(rec.sbl_domain)
                if rec.sbl_dynamic_portal_id.sbl_domain:
                    domain += ast.literal_eval(rec.sbl_dynamic_portal_id.sbl_domain)
                count += rec.env[rec.sbl_model_name].sudo().search_count(domain)
            rec.sbl_record_count = count
