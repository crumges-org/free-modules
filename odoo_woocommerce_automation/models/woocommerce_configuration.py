# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from ..tools import WooCommerceTools

_logger = logging.getLogger(__name__)


class WooCommerceConfiguration(models.Model):
    """WooCommerce Configuration Model"""
    _name = 'woocommerce.configuration'
    _description = 'WooCommerce Configuration'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='Name for this WooCommerce configuration'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Enable or disable this configuration'
    )
    
    woocommerce_url = fields.Char(
        string='WooCommerce URL',
        required=True,
        help='Your WooCommerce store URL (e.g., https://yourstore.com)'
    )
    
    consumer_key = fields.Char(
        string='Consumer Key',
        required=True,
        help='WooCommerce REST API Consumer Key'
    )
    
    consumer_secret = fields.Char(
        string='Consumer Secret',
        required=True,
        help='WooCommerce REST API Consumer Secret'
    )
    
    api_version = fields.Selection([
        ('wc/v3', 'WC v3'),
        ('wc/v2', 'WC v2'),
    ], string='API Version', default='wc/v3', required=True)
    
    timeout = fields.Integer(
        string='Timeout (seconds)',
        default=30,
        help='API request timeout in seconds'
    )
    
    # Sync Settings
    sync_products = fields.Boolean(
        string='Sync Products',
        default=True,
        help='Enable product synchronization'
    )
    
    sync_orders = fields.Boolean(
        string='Sync Orders',
        default=True,
        help='Enable order synchronization'
    )
    
    sync_customers = fields.Boolean(
        string='Sync Customers',
        default=True,
        help='Enable customer synchronization'
    )
    
    sync_inventory = fields.Boolean(
        string='Sync Inventory',
        default=True,
        help='Enable inventory synchronization'
    )
    
    # Auto Sync Settings
    auto_sync_products = fields.Boolean(
        string='Auto Sync Products',
        default=False,
        help='Automatically sync products on changes'
    )
    
    auto_sync_orders = fields.Boolean(
        string='Auto Sync Orders',
        default=False,
        help='Automatically sync orders on changes'
    )
    
    auto_sync_customers = fields.Boolean(
        string='Auto Sync Customers',
        default=False,
        help='Automatically sync customers on changes'
    )
    
    sync_frequency = fields.Selection([
        ('15minutes', 'Every 15 minutes'),
        ('30minutes', 'Every 30 minutes'),
        ('1hour', 'Every hour'),
        ('6hours', 'Every 6 hours'),
        ('12hours', 'Every 12 hours'),
        ('1day', 'Daily'),
    ], string='Sync Frequency', default='1hour')
    
    # Connection Status
    connection_status = fields.Selection([
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
    ], string='Connection Status', default='disconnected', readonly=True)
    
    last_connection_test = fields.Datetime(
        string='Last Connection Test',
        readonly=True
    )
    
    connection_error_message = fields.Text(
        string='Connection Error Message',
        readonly=True
    )
    
    # Sync Statistics
    last_product_sync = fields.Datetime(
        string='Last Product Sync',
        readonly=True
    )
    
    last_order_sync = fields.Datetime(
        string='Last Order Sync',
        readonly=True
    )
    
    last_customer_sync = fields.Datetime(
        string='Last Customer Sync',
        readonly=True
    )
    
    last_inventory_sync = fields.Datetime(
        string='Last Inventory Sync',
        readonly=True
    )
    
    total_products_synced = fields.Integer(
        string='Total Products Synced',
        default=0,
        readonly=True
    )
    
    total_orders_synced = fields.Integer(
        string='Total Orders Synced',
        default=0,
        readonly=True
    )
    
    total_customers_synced = fields.Integer(
        string='Total Customers Synced',
        default=0,
        readonly=True
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this configuration'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    @api.constrains('woocommerce_url')
    def _check_woocommerce_url(self):
        """Validate WooCommerce URL format"""
        for record in self:
            if record.woocommerce_url:
                if not record.woocommerce_url.startswith(('http://', 'https://')):
                    raise ValidationError(_('WooCommerce URL must start with http:// or https://'))

    def action_test_connection(self):
        """Test WooCommerce connection"""
        self.ensure_one()
        
        try:
            # Initialize WooCommerce tools
            wc_tools = WooCommerceTools(
                url=self.woocommerce_url,
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                version=self.api_version,
                timeout=self.timeout
            )
            
            # Test connection by getting store information
            store_info = wc_tools.get_store_info()
            
            if store_info:
                self.write({
                    'connection_status': 'connected',
                    'last_connection_test': fields.Datetime.now(),
                    'connection_error_message': False,
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Successful'),
                        'message': _('Successfully connected to WooCommerce store'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise Exception('Failed to retrieve store information')
                
        except Exception as e:
            self.write({
                'connection_status': 'error',
                'last_connection_test': fields.Datetime.now(),
                'connection_error_message': str(e),
            })
            
            raise UserError(_(f'Connection failed: {str(e)}'))

    def action_sync_products(self):
        """Manual product synchronization"""
        self.ensure_one()
        if not self.sync_products:
            raise UserError(_('Product synchronization is disabled for this configuration'))
        
        # This will be implemented in the sync service
        self.env['woocommerce.sync.service'].sync_products(self)
        
        self.write({
            'last_product_sync': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Product synchronization completed'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_orders(self):
        """Manual order synchronization"""
        self.ensure_one()
        if not self.sync_orders:
            raise UserError(_('Order synchronization is disabled for this configuration'))
        
        # This will be implemented in the sync service
        self.env['woocommerce.sync.service'].sync_orders(self)
        
        self.write({
            'last_order_sync': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Order synchronization completed'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_customers(self):
        """Manual customer synchronization"""
        self.ensure_one()
        if not self.sync_customers:
            raise UserError(_('Customer synchronization is disabled for this configuration'))
        
        # This will be implemented in the sync service
        self.env['woocommerce.sync.service'].sync_customers(self)
        
        self.write({
            'last_customer_sync': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Customer synchronization completed'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_sync_logs(self):
        """View synchronization logs for this configuration"""
        self.ensure_one()
        return {
            'name': _('Sync Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.sync.log',
            'view_mode': 'list,form',
            'domain': [('configuration_id', '=', self.id)],
            'context': {'default_configuration_id': self.id},
        }

    def action_view_dashboard(self):
        """View WooCommerce dashboard"""
        self.ensure_one()
        return {
            'name': _('WooCommerce Dashboard'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.dashboard',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_configuration_id': self.id},
        }

    @api.model
    def get_active_configuration(self):
        """Get the active WooCommerce configuration"""
        return self.search([('active', '=', True)], limit=1)

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.name}"
            if record.connection_status == 'connected':
                name += f" ({_('Connected')})"
            elif record.connection_status == 'error':
                name += f" ({_('Error')})"
            result.append((record.id, name))
        return result

    # Cron Methods
    @api.model
    def _cron_sync_products(self):
        """Cron job to sync products"""
        _logger.info("Starting scheduled product sync")
        configurations = self.search([('active', '=', True), ('auto_sync_products', '=', True)])
        
        for config in configurations:
            try:
                config.action_sync_products()
                _logger.info(f"Product sync completed for configuration: {config.name}")
            except Exception as e:
                _logger.error(f"Product sync failed for configuration {config.name}: {str(e)}")

    @api.model
    def _cron_sync_orders(self):
        """Cron job to sync orders"""
        _logger.info("Starting scheduled order sync")
        configurations = self.search([('active', '=', True), ('auto_sync_orders', '=', True)])
        
        for config in configurations:
            try:
                config.action_sync_orders()
                _logger.info(f"Order sync completed for configuration: {config.name}")
            except Exception as e:
                _logger.error(f"Order sync failed for configuration {config.name}: {str(e)}")

    @api.model
    def _cron_sync_customers(self):
        """Cron job to sync customers"""
        _logger.info("Starting scheduled customer sync")
        configurations = self.search([('active', '=', True), ('auto_sync_customers', '=', True)])
        
        for config in configurations:
            try:
                config.action_sync_customers()
                _logger.info(f"Customer sync completed for configuration: {config.name}")
            except Exception as e:
                _logger.error(f"Customer sync failed for configuration {config.name}: {str(e)}")

    @api.model
    def _cron_sync_inventory(self):
        """Cron job to sync inventory"""
        _logger.info("Starting scheduled inventory sync")
        configurations = self.search([('active', '=', True), ('sync_inventory', '=', True)])
        
        for config in configurations:
            try:
                # This will be implemented in the sync service
                self.env['woocommerce.sync.service'].sync_inventory(config)
                config.write({'last_inventory_sync': fields.Datetime.now()})
                _logger.info(f"Inventory sync completed for configuration: {config.name}")
            except Exception as e:
                _logger.error(f"Inventory sync failed for configuration {config.name}: {str(e)}")

    @api.model
    def _cron_test_connection(self):
        """Cron job to test connections"""
        _logger.info("Starting scheduled connection tests")
        configurations = self.search([('active', '=', True)])
        
        for config in configurations:
            try:
                config.action_test_connection()
                _logger.info(f"Connection test completed for configuration: {config.name}")
            except Exception as e:
                _logger.error(f"Connection test failed for configuration {config.name}: {str(e)}") 