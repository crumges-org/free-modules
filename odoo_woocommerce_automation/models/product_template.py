# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    """Extend product.template for WooCommerce integration"""
    _inherit = 'product.template'

    woocommerce_product_id = fields.Integer(
        string='WooCommerce Product ID',
        help='WooCommerce product ID for this product'
    )
    
    woocommerce_sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('error', 'Error'),
    ], string='WooCommerce Sync Status', default='pending')
    
    woocommerce_last_sync = fields.Datetime(
        string='Last WooCommerce Sync',
        help='Last time this product was synchronized with WooCommerce'
    )
    
    woocommerce_sync_error = fields.Text(
        string='WooCommerce Sync Error',
        help='Error message from last WooCommerce synchronization attempt'
    )
    
    woocommerce_sku = fields.Char(
        string='WooCommerce SKU',
        help='SKU used in WooCommerce for this product'
    ) 