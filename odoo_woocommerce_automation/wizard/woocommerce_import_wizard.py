# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class WooCommerceImportWizard(models.TransientModel):
    """WooCommerce Import Wizard"""
    _name = 'woocommerce.import.wizard'
    _description = 'WooCommerce Import Wizard'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        help='Select the WooCommerce configuration to use for import'
    )
    
    import_products = fields.Boolean(
        string='Import Products',
        default=True,
        help='Import products from WooCommerce'
    )
    
    import_orders = fields.Boolean(
        string='Import Orders',
        default=True,
        help='Import orders from WooCommerce'
    )
    
    import_customers = fields.Boolean(
        string='Import Customers',
        default=True,
        help='Import customers from WooCommerce'
    )
    
    import_inventory = fields.Boolean(
        string='Import Inventory',
        default=True,
        help='Import inventory levels from WooCommerce'
    )
    
    sync_frequency = fields.Selection([
        ('manual', 'Manual'),
        ('1hour', 'Every Hour'),
        ('6hours', 'Every 6 Hours'),
        ('daily', 'Daily'),
    ], string='Sync Frequency', default='manual', required=True)
    
    import_limit = fields.Integer(
        string='Import Limit',
        default=100,
        help='Maximum number of records to import per type'
    )
    
    create_missing_products = fields.Boolean(
        string='Create Missing Products',
        default=True,
        help='Create Odoo products for WooCommerce products that don\'t exist'
    )
    
    create_missing_customers = fields.Boolean(
        string='Create Missing Customers',
        default=True,
        help='Create Odoo customers for WooCommerce customers that don\'t exist'
    )
    
    update_existing = fields.Boolean(
        string='Update Existing Records',
        default=True,
        help='Update existing Odoo records with WooCommerce data'
    )
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ], string='Status', default='draft', readonly=True)
    
    progress = fields.Float(
        string='Progress (%)',
        default=0.0,
        readonly=True
    )
    
    result_message = fields.Text(
        string='Result Message',
        readonly=True
    )
    
    @api.model
    def default_get(self, fields_list):
        """Set default configuration"""
        res = super().default_get(fields_list)
        config = self.env['woocommerce.configuration'].search([('active', '=', True)], limit=1)
        if config:
            res['configuration_id'] = config.id
        return res
    
    def action_start_import(self):
        """Start the import process"""
        self.ensure_one()
        
        if not self.configuration_id:
            raise UserError(_("Please select a WooCommerce configuration."))
        
        self.write({
            'status': 'running',
            'progress': 0.0,
            'result_message': 'Starting import process...'
        })
        
        try:
            # Import products
            if self.import_products:
                self._import_products()
                self.progress = 25.0
            
            # Import customers
            if self.import_customers:
                self._import_customers()
                self.progress = 50.0
            
            # Import orders
            if self.import_orders:
                self._import_orders()
                self.progress = 75.0
            
            # Import inventory
            if self.import_inventory:
                self._import_inventory()
                self.progress = 100.0
            
            self.write({
                'status': 'completed',
                'result_message': 'Import completed successfully!'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Completed'),
                    'message': _('WooCommerce import completed successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            self.write({
                'status': 'error',
                'result_message': f'Import failed: {str(e)}'
            })
            raise UserError(_(f'Import failed: {str(e)}'))
    
    def _import_products(self):
        """Import products from WooCommerce"""
        try:
            # This would call the actual import logic from the configuration
            self.configuration_id.action_sync_products()
            _logger.info(f"Products imported successfully for configuration {self.configuration_id.name}")
        except Exception as e:
            _logger.error(f"Error importing products: {e}")
            raise
    
    def _import_customers(self):
        """Import customers from WooCommerce"""
        try:
            # This would call the actual import logic from the configuration
            self.configuration_id.action_sync_customers()
            _logger.info(f"Customers imported successfully for configuration {self.configuration_id.name}")
        except Exception as e:
            _logger.error(f"Error importing customers: {e}")
            raise
    
    def _import_orders(self):
        """Import orders from WooCommerce"""
        try:
            # This would call the actual import logic from the configuration
            self.configuration_id.action_sync_orders()
            _logger.info(f"Orders imported successfully for configuration {self.configuration_id.name}")
        except Exception as e:
            _logger.error(f"Error importing orders: {e}")
            raise
    
    def _import_inventory(self):
        """Import inventory from WooCommerce"""
        try:
            # This would call the actual import logic from the configuration
            self.configuration_id.action_sync_inventory()
            _logger.info(f"Inventory imported successfully for configuration {self.configuration_id.name}")
        except Exception as e:
            _logger.error(f"Error importing inventory: {e}")
            raise 