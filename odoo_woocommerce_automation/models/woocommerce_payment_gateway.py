# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCommercePaymentGateway(models.Model):
    """WooCommerce Payment Gateway Management"""
    _name = 'woocommerce.payment.gateway'
    _description = 'WooCommerce Payment Gateway'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(string='Gateway Name', required=True, tracking=True)
    title = fields.Char(string='Title', tracking=True, help="Display title for the gateway")
    description = fields.Text(string='Description', tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Configuration Reference
    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    # WooCommerce Integration
    woocommerce_gateway_id = fields.Char(string='WooCommerce Gateway ID', help="ID in WooCommerce")
    exported_in_woocommerce = fields.Boolean(string='Exported in WooCommerce', default=False, tracking=True)
    last_sync_date = fields.Datetime(string='Last Sync Date', tracking=True)
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('failed', 'Failed'),
        ('updated', 'Updated')
    ], string='Sync Status', default='pending', tracking=True)
    
    # Gateway Properties
    gateway_type = fields.Selection([
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('check', 'Check'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('square', 'Square'),
        ('other', 'Other')
    ], string='Gateway Type', default='other', tracking=True)
    
    # Settings
    enabled = fields.Boolean(string='Enabled', default=True, tracking=True)
    supports_refunds = fields.Boolean(string='Supports Refunds', default=False, tracking=True)
    supports_partial_refunds = fields.Boolean(string='Supports Partial Refunds', default=False, tracking=True)
    supports_capture = fields.Boolean(string='Supports Capture', default=False, tracking=True)
    
    # Configuration
    gateway_config = fields.Text(string='Gateway Configuration', help="JSON configuration for the gateway")
    
    # Statistics
    transaction_count = fields.Integer(string='Transaction Count', default=0, tracking=True)
    total_amount = fields.Float(string='Total Amount', default=0.0, tracking=True)
    success_rate = fields.Float(string='Success Rate (%)', default=0.0, tracking=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                default=lambda self: self.env.company, required=True)
    
    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name, configuration_id)', 'Gateway name must be unique per configuration!')
    ]

    def action_export_to_woocommerce(self):
        """Export payment gateway to WooCommerce"""
        self.ensure_one()
        try:
            # Prepare gateway data for WooCommerce
            gateway_data = {
                'name': self.name,
                'title': self.title or self.name,
                'description': self.description or '',
                'enabled': self.enabled,
                'gateway_type': self.gateway_type,
                'supports_refunds': self.supports_refunds,
                'supports_partial_refunds': self.supports_partial_refunds,
                'supports_capture': self.supports_capture,
                'gateway_config': self.gateway_config or '{}'
            }
            
            # Export via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.export_payment_gateway(self.configuration_id, gateway_data)
            
            if result:
                self.write({
                    'exported_in_woocommerce': True,
                    'last_sync_date': fields.Datetime.now(),
                    'sync_status': 'synced',
                    'woocommerce_gateway_id': result.get('id')
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Payment gateway exported to WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            self.write({'sync_status': 'failed'})
            raise UserError(_('Failed to export payment gateway: %s') % str(e))

    def action_import_from_woocommerce(self):
        """Import payment gateway from WooCommerce"""
        self.ensure_one()
        try:
            # Import via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.import_payment_gateway(self.configuration_id, self.woocommerce_gateway_id)
            
            if result:
                self._update_from_woocommerce_data(result)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Payment gateway imported from WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Failed to import payment gateway: %s') % str(e))

    def action_sync_all_gateways(self):
        """Sync all payment gateways for a configuration"""
        self.ensure_one()
        try:
            sync_service = self.env['woocommerce.sync.service']
            sync_service.sync_payment_gateways(self.configuration_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All payment gateways synchronized successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Failed to sync payment gateways: %s') % str(e))

    def _update_from_woocommerce_data(self, woo_data):
        """Update payment gateway from WooCommerce data"""
        self.write({
            'name': woo_data.get('name', self.name),
            'title': woo_data.get('title', ''),
            'description': woo_data.get('description', ''),
            'enabled': woo_data.get('enabled', True),
            'gateway_type': woo_data.get('gateway_type', 'other'),
            'supports_refunds': woo_data.get('supports_refunds', False),
            'supports_partial_refunds': woo_data.get('supports_partial_refunds', False),
            'supports_capture': woo_data.get('supports_capture', False),
            'gateway_config': woo_data.get('gateway_config', '{}'),
            'transaction_count': woo_data.get('transaction_count', 0),
            'total_amount': float(woo_data.get('total_amount', 0)),
            'success_rate': float(woo_data.get('success_rate', 0)),
            'last_sync_date': fields.Datetime.now(),
            'sync_status': 'synced'
        })

    def action_view_transactions(self):
        """View payment transactions for this gateway"""
        return {
            'name': _('Payment Transactions: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('payment_method_id.name', 'ilike', self.name)],
        }

    def action_test_gateway(self):
        """Test payment gateway connection"""
        self.ensure_one()
        try:
            # Test via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.test_payment_gateway(self.configuration_id, self.woocommerce_gateway_id)
            
            if result:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Payment gateway test successful'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Payment gateway test failed: %s') % str(e))

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.name
            if record.gateway_type != 'other':
                name += f" ({record.gateway_type})"
            if not record.enabled:
                name += " [Disabled]"
            if not record.active:
                name += " [Inactive]"
            result.append((record.id, name))
        return result
