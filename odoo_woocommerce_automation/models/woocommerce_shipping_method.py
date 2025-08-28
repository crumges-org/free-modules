# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCommerceShippingMethod(models.Model):
    """WooCommerce Shipping Method Management"""
    _name = 'woocommerce.shipping.method'
    _description = 'WooCommerce Shipping Method'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(string='Method Name', required=True, tracking=True)
    title = fields.Char(string='Title', tracking=True, help="Display title for the shipping method")
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
    woocommerce_method_id = fields.Char(string='WooCommerce Method ID', help="ID in WooCommerce")
    exported_in_woocommerce = fields.Boolean(string='Exported in WooCommerce', default=False, tracking=True)
    last_sync_date = fields.Datetime(string='Last Sync Date', tracking=True)
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('failed', 'Failed'),
        ('updated', 'Updated')
    ], string='Sync Status', default='pending', tracking=True)
    
    # Method Properties
    method_type = fields.Selection([
        ('flat_rate', 'Flat Rate'),
        ('free_shipping', 'Free Shipping'),
        ('local_pickup', 'Local Pickup'),
        ('table_rate', 'Table Rate'),
        ('weight_based', 'Weight Based'),
        ('distance_based', 'Distance Based'),
        ('other', 'Other')
    ], string='Method Type', default='other', tracking=True)
    
    # Settings
    enabled = fields.Boolean(string='Enabled', default=True, tracking=True)
    cost = fields.Float(string='Cost', default=0.0, tracking=True, help="Shipping cost")
    min_amount = fields.Float(string='Minimum Amount', default=0.0, tracking=True,
                             help="Minimum order amount for this method")
    max_amount = fields.Float(string='Maximum Amount', default=0.0, tracking=True,
                             help="Maximum order amount for this method")
    
    # Zones and Locations
    shipping_zones = fields.Text(string='Shipping Zones', help="Comma-separated list of shipping zones")
    excluded_zones = fields.Text(string='Excluded Zones', help="Comma-separated list of excluded zones")
    
    # Delivery Settings
    delivery_time = fields.Char(string='Delivery Time', help="Estimated delivery time")
    tracking_support = fields.Boolean(string='Tracking Support', default=False, tracking=True)
    
    # Statistics
    usage_count = fields.Integer(string='Usage Count', default=0, tracking=True)
    total_revenue = fields.Float(string='Total Revenue', default=0.0, tracking=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                default=lambda self: self.env.company, required=True)
    
    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name, configuration_id)', 'Shipping method name must be unique per configuration!')
    ]

    def action_export_to_woocommerce(self):
        """Export shipping method to WooCommerce"""
        self.ensure_one()
        try:
            # Prepare shipping method data for WooCommerce
            method_data = {
                'name': self.name,
                'title': self.title or self.name,
                'description': self.description or '',
                'enabled': self.enabled,
                'method_type': self.method_type,
                'cost': self.cost,
                'min_amount': self.min_amount,
                'max_amount': self.max_amount,
                'shipping_zones': self.shipping_zones or '',
                'excluded_zones': self.excluded_zones or '',
                'delivery_time': self.delivery_time or '',
                'tracking_support': self.tracking_support
            }
            
            # Export via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.export_shipping_method(self.configuration_id, method_data)
            
            if result:
                self.write({
                    'exported_in_woocommerce': True,
                    'last_sync_date': fields.Datetime.now(),
                    'sync_status': 'synced',
                    'woocommerce_method_id': result.get('id')
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Shipping method exported to WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            self.write({'sync_status': 'failed'})
            raise UserError(_('Failed to export shipping method: %s') % str(e))

    def action_import_from_woocommerce(self):
        """Import shipping method from WooCommerce"""
        self.ensure_one()
        try:
            # Import via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.import_shipping_method(self.configuration_id, self.woocommerce_method_id)
            
            if result:
                self._update_from_woocommerce_data(result)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Shipping method imported from WooCommerce successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Failed to import shipping method: %s') % str(e))

    def action_sync_all_methods(self):
        """Sync all shipping methods for a configuration"""
        self.ensure_one()
        try:
            sync_service = self.env['woocommerce.sync.service']
            sync_service.sync_shipping_methods(self.configuration_id)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All shipping methods synchronized successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Failed to sync shipping methods: %s') % str(e))

    def _update_from_woocommerce_data(self, woo_data):
        """Update shipping method from WooCommerce data"""
        self.write({
            'name': woo_data.get('name', self.name),
            'title': woo_data.get('title', ''),
            'description': woo_data.get('description', ''),
            'enabled': woo_data.get('enabled', True),
            'method_type': woo_data.get('method_type', 'other'),
            'cost': float(woo_data.get('cost', 0)),
            'min_amount': float(woo_data.get('min_amount', 0)),
            'max_amount': float(woo_data.get('max_amount', 0)),
            'shipping_zones': woo_data.get('shipping_zones', ''),
            'excluded_zones': woo_data.get('excluded_zones', ''),
            'delivery_time': woo_data.get('delivery_time', ''),
            'tracking_support': woo_data.get('tracking_support', False),
            'usage_count': woo_data.get('usage_count', 0),
            'total_revenue': float(woo_data.get('total_revenue', 0)),
            'last_sync_date': fields.Datetime.now(),
            'sync_status': 'synced'
        })

    def action_view_orders(self):
        """View orders using this shipping method"""
        return {
            'name': _('Orders with Shipping: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('carrier_id.name', 'ilike', self.name)],
        }

    def action_test_method(self):
        """Test shipping method calculation"""
        self.ensure_one()
        try:
            # Test via sync service
            sync_service = self.env['woocommerce.sync.service']
            result = sync_service.test_shipping_method(self.configuration_id, self.woocommerce_method_id)
            
            if result:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Shipping method test successful'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(_('Shipping method test failed: %s') % str(e))

    def action_calculate_shipping(self):
        """Calculate shipping cost for a test order"""
        self.ensure_one()
        return {
            'name': _('Calculate Shipping Cost'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.shipping.calculator',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shipping_method_id': self.id,
                'default_configuration_id': self.configuration_id.id,
            }
        }

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.name
            if record.method_type != 'other':
                name += f" ({record.method_type})"
            if record.cost > 0:
                name += f" - ${record.cost}"
            if not record.enabled:
                name += " [Disabled]"
            if not record.active:
                name += " [Inactive]"
            result.append((record.id, name))
        return result
