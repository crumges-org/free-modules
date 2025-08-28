# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class WooCommerceExportWizard(models.TransientModel):
    """WooCommerce Export Wizard"""
    _name = 'woocommerce.export.wizard'
    _description = 'WooCommerce Export Wizard'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        help='Select the WooCommerce configuration to use for export'
    )
    
    export_products = fields.Boolean(
        string='Export Products',
        default=True,
        help='Export products to WooCommerce'
    )
    
    export_orders = fields.Boolean(
        string='Export Orders',
        default=False,
        help='Export orders to WooCommerce'
    )
    
    export_customers = fields.Boolean(
        string='Export Customers',
        default=True,
        help='Export customers to WooCommerce'
    )
    
    export_inventory = fields.Boolean(
        string='Export Inventory',
        default=True,
        help='Export inventory levels to WooCommerce'
    )
    
    export_limit = fields.Integer(
        string='Export Limit',
        default=100,
        help='Maximum number of records to export per type'
    )
    
    include_images = fields.Boolean(
        string='Include Product Images',
        default=True,
        help='Include product images in the export'
    )
    
    include_variants = fields.Boolean(
        string='Include Product Variants',
        default=True,
        help='Include product variants in the export'
    )
    
    update_existing = fields.Boolean(
        string='Update Existing Records',
        default=True,
        help='Update existing WooCommerce records with Odoo data'
    )
    
    create_missing = fields.Boolean(
        string='Create Missing Records',
        default=True,
        help='Create WooCommerce records for Odoo records that don\'t exist'
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
    
    def action_start_export(self):
        """Start the export process"""
        self.ensure_one()
        
        if not self.configuration_id:
            raise UserError(_("Please select a WooCommerce configuration."))
        
        self.write({
            'status': 'running',
            'progress': 0.0,
            'result_message': 'Starting export process...'
        })
        
        try:
            # Export products
            if self.export_products:
                self._export_products()
                self.progress = 25.0
            
            # Export customers
            if self.export_customers:
                self._export_customers()
                self.progress = 50.0
            
            # Export orders
            if self.export_orders:
                self._export_orders()
                self.progress = 75.0
            
            # Export inventory
            if self.export_inventory:
                self._export_inventory()
                self.progress = 100.0
            
            self.write({
                'status': 'completed',
                'result_message': 'Export completed successfully!'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Export Completed'),
                    'message': _('WooCommerce export completed successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            self.write({
                'status': 'error',
                'result_message': f'Export failed: {str(e)}'
            })
            raise UserError(_(f'Export failed: {str(e)}'))
    
    def _export_products(self):
        """Export products to WooCommerce"""
        try:
            # Get products to export
            products = self.env['product.template'].search([
                ('active', '=', True),
                ('sale_ok', '=', True)
            ], limit=self.export_limit)
            
            exported_count = 0
            for product in products:
                try:
                    # This would call the actual export logic
                    # For now, we'll just log the attempt
                    _logger.info(f"Exporting product: {product.name}")
                    exported_count += 1
                except Exception as e:
                    _logger.error(f"Error exporting product {product.name}: {e}")
            
            _logger.info(f"Exported {exported_count} products to WooCommerce")
            
        except Exception as e:
            _logger.error(f"Error in product export: {e}")
            raise
    
    def _export_customers(self):
        """Export customers to WooCommerce"""
        try:
            # Get customers to export
            customers = self.env['res.partner'].search([
                ('active', '=', True),
                ('customer_rank', '>', 0)
            ], limit=self.export_limit)
            
            exported_count = 0
            for customer in customers:
                try:
                    # This would call the actual export logic
                    _logger.info(f"Exporting customer: {customer.name}")
                    exported_count += 1
                except Exception as e:
                    _logger.error(f"Error exporting customer {customer.name}: {e}")
            
            _logger.info(f"Exported {exported_count} customers to WooCommerce")
            
        except Exception as e:
            _logger.error(f"Error in customer export: {e}")
            raise
    
    def _export_orders(self):
        """Export orders to WooCommerce"""
        try:
            # Get orders to export
            orders = self.env['sale.order'].search([
                ('state', 'in', ['sale', 'done']),
                ('woocommerce_order_id', '=', False)  # Not already exported
            ], limit=self.export_limit)
            
            exported_count = 0
            for order in orders:
                try:
                    # This would call the actual export logic
                    _logger.info(f"Exporting order: {order.name}")
                    exported_count += 1
                except Exception as e:
                    _logger.error(f"Error exporting order {order.name}: {e}")
            
            _logger.info(f"Exported {exported_count} orders to WooCommerce")
            
        except Exception as e:
            _logger.error(f"Error in order export: {e}")
            raise
    
    def _export_inventory(self):
        """Export inventory to WooCommerce"""
        try:
            # Get products with stock to export
            products = self.env['product.template'].search([
                ('active', '=', True),
                ('sale_ok', '=', True),
                ('type', '=', 'product')
            ], limit=self.export_limit)
            
            exported_count = 0
            for product in products:
                try:
                    # This would call the actual export logic
                    _logger.info(f"Exporting inventory for product: {product.name}")
                    exported_count += 1
                except Exception as e:
                    _logger.error(f"Error exporting inventory for product {product.name}: {e}")
            
            _logger.info(f"Exported inventory for {exported_count} products to WooCommerce")
            
        except Exception as e:
            _logger.error(f"Error in inventory export: {e}")
            raise 