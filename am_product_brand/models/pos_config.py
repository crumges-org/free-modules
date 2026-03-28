# -*- coding: utf-8 -*-
from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    use_product_brand = fields.Boolean(
        string='Use Product Brands',
        default=True,
        help='Enable brand filtering in POS'
    )

    available_brand_ids = fields.Many2many(
        'product.brand',
        'pos_config_brand_rel',
        'pos_config_id',
        'brand_id',
        string='Available Brands',
        help='Select brands available in this POS. Leave empty for all brands.'
    )

    default_brand_id = fields.Many2one(
        'product.brand',
        string='Default Brand',
        help='Default brand filter when opening POS'
    )

    show_brand_images = fields.Boolean(
        string='Show Brand Images',
        default=True,
        help='Display brand images in the brand selector'
    )

    def _get_available_brand_ids(self):
        """Get available brand IDs for this POS"""
        self.ensure_one()
        if self.available_brand_ids:
            return self.available_brand_ids.ids
        return self.env['product.brand'].search([('active', '=', True)]).ids
