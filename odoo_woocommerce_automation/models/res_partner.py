# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class ResPartner(models.Model):
    """Extend res.partner for WooCommerce integration"""
    _inherit = 'res.partner'

    woocommerce_customer_id = fields.Integer(
        string='WooCommerce Customer ID',
        help='WooCommerce customer ID for this partner'
    )
    
    woocommerce_sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('error', 'Error'),
    ], string='WooCommerce Sync Status', default='pending')
    
    woocommerce_last_sync = fields.Datetime(
        string='Last WooCommerce Sync',
        help='Last time this partner was synchronized with WooCommerce'
    )
    
    woocommerce_sync_error = fields.Text(
        string='WooCommerce Sync Error',
        help='Error message from last WooCommerce synchronization attempt'
    ) 