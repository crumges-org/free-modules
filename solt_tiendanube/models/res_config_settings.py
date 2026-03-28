# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    use_sale_multi_stock = fields.Boolean(string='Use multi warehouse in Sales Orders', readonly=False, related='company_id.use_sale_multi_stock')

    @api.model
    def set_values(self):
        self.env.company.write({
            'use_sale_multi_stock': self.use_sale_multi_stock or self.env.company.use_sale_multi_stock
        })
        super(ResConfigSettings, self).set_values()

