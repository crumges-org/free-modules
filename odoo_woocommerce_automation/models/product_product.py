# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class ProductProduct(models.Model):
    """Extend product.product for WooCommerce integration"""
    _inherit = 'product.product'

    woocommerce_variant_id = fields.Integer(
        string='WooCommerce Variant ID',
        help='WooCommerce variant ID for this product variant'
    )
    
    woocommerce_sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('error', 'Error'),
    ], string='WooCommerce Sync Status', default='pending')
    
    woocommerce_last_sync = fields.Datetime(
        string='Last WooCommerce Sync',
        help='Last time this product variant was synchronized with WooCommerce'
    )
    
    woocommerce_sync_error = fields.Text(
        string='WooCommerce Sync Error',
        help='Error message from last WooCommerce synchronization attempt'
    ) 