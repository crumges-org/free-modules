# Powered by Sensible Consulting Services
# -*- coding: utf-8 -*-
# © 2025 Sensible Consulting Services (<https://sensiblecs.com/>)
from odoo import fields, models


class SblDynamicPortal(models.Model):
    _inherit = 'sbl.dynamic.portal'

    sbl_color = fields.Char('Card Color', default="#875A7B")
    sbl_kpis_ids = fields.One2many('sbl.dynamic.portal.kpis.line', 'sbl_dynamic_portal_id', string='KPIs')
    sbl_dashboard_kpis_ids = fields.One2many('sbl.dynamic.portal.kpis.line', 'sbl_dynamic_portal_dashboard_id', string='Dashboard KPIs')