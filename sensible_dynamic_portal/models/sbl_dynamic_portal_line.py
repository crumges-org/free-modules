# Powered by Sensible Consulting Services
# -*- coding: utf-8 -*-
# © 2025 Sensible Consulting Services (<https://sensiblecs.com/>)
from odoo import fields, models, api


class SblDynamicPortalLine(models.Model):
    _name = 'sbl.dynamic.portal.line'
    _description = 'Dynamic Portal Line'
    _order = 'sequence'

    sbl_dynamic_portal_id = fields.Many2one('sbl.dynamic.portal', string='Dynamic Portal')
    sequence = fields.Integer()
    sbl_model_id = fields.Many2one('ir.model', string='Model')
    sbl_field_id = fields.Many2one('ir.model.fields', string='Field')
    sbl_ttype = fields.Selection(related='sbl_field_id.ttype', string='Type')
    sbl_display_currency = fields.Boolean('Display Currency')
