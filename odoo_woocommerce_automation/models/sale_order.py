# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class SaleOrder(models.Model):
    """Extend sale.order for WooCommerce integration"""
    _inherit = 'sale.order'

    woocommerce_order_id = fields.Integer(
        string='WooCommerce Order ID',
        help='WooCommerce order ID for this sale order'
    )
    
    woocommerce_sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('error', 'Error'),
    ], string='WooCommerce Sync Status', default='pending')
    
    woocommerce_last_sync = fields.Datetime(
        string='Last WooCommerce Sync',
        help='Last time this order was synchronized with WooCommerce'
    )
    
    woocommerce_sync_error = fields.Text(
        string='WooCommerce Sync Error',
        help='Error message from last WooCommerce synchronization attempt'
    )
    
    woocommerce_status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
        ('on-hold', 'On Hold'),
    ], string='WooCommerce Status', default='pending') 