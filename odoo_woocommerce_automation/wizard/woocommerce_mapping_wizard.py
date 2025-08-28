# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class WooCommerceMappingWizard(models.TransientModel):
    """WooCommerce Mapping Wizard"""
    _name = 'woocommerce.mapping.wizard'
    _description = 'WooCommerce Mapping Wizard'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        help='Select the WooCommerce configuration to use for mapping'
    )
    
    mapping_type = fields.Selection([
        ('product_categories', 'Product Categories'),
        ('order_statuses', 'Order Statuses'),
        ('payment_methods', 'Payment Methods'),
        ('shipping_methods', 'Shipping Methods'),
        ('customer_groups', 'Customer Groups'),
        ('product_attributes', 'Product Attributes'),
    ], string='Mapping Type', required=True, default='product_categories')
    
    # Product Category Mapping
    odoo_category_id = fields.Many2one(
        'product.category',
        string='Odoo Category',
        help='Select Odoo product category'
    )
    
    woocommerce_category_id = fields.Char(
        string='WooCommerce Category ID',
        help='Enter WooCommerce category ID'
    )
    
    woocommerce_category_name = fields.Char(
        string='WooCommerce Category Name',
        help='Enter WooCommerce category name'
    )
    
    # Order Status Mapping
    odoo_state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Odoo Order State')
    
    woocommerce_status = fields.Char(
        string='WooCommerce Status',
        help='Enter WooCommerce order status'
    )
    
    # Payment Method Mapping
    odoo_payment_method = fields.Char(
        string='Odoo Payment Method',
        help='Enter Odoo payment method name'
    )
    
    woocommerce_payment_method = fields.Char(
        string='WooCommerce Payment Method',
        help='Enter WooCommerce payment method name'
    )
    
    # Shipping Method Mapping
    odoo_shipping_method = fields.Char(
        string='Odoo Shipping Method',
        help='Enter Odoo shipping method name'
    )
    
    woocommerce_shipping_method = fields.Char(
        string='WooCommerce Shipping Method',
        help='Enter WooCommerce shipping method name'
    )
    
    # Customer Group Mapping
    odoo_partner_category_id = fields.Many2one(
        'res.partner.category',
        string='Odoo Partner Category',
        help='Select Odoo partner category'
    )
    
    woocommerce_customer_group = fields.Char(
        string='WooCommerce Customer Group',
        help='Enter WooCommerce customer group name'
    )
    
    # Product Attribute Mapping
    odoo_attribute_id = fields.Many2one(
        'product.attribute',
        string='Odoo Product Attribute',
        help='Select Odoo product attribute'
    )
    
    woocommerce_attribute_name = fields.Char(
        string='WooCommerce Attribute Name',
        help='Enter WooCommerce attribute name'
    )
    
    # Mapping Results
    mapping_results = fields.Text(
        string='Mapping Results',
        readonly=True
    )
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ], string='Status', default='draft', readonly=True)
    
    @api.model
    def default_get(self, fields_list):
        """Set default configuration"""
        res = super().default_get(fields_list)
        config = self.env['woocommerce.configuration'].search([('active', '=', True)], limit=1)
        if config:
            res['configuration_id'] = config.id
        return res
    
    @api.onchange('mapping_type')
    def _onchange_mapping_type(self):
        """Clear fields when mapping type changes"""
        self.odoo_category_id = False
        self.woocommerce_category_id = ''
        self.woocommerce_category_name = ''
        self.odoo_state = False
        self.woocommerce_status = ''
        self.odoo_payment_method = ''
        self.woocommerce_payment_method = ''
        self.odoo_shipping_method = ''
        self.woocommerce_shipping_method = ''
        self.odoo_partner_category_id = False
        self.woocommerce_customer_group = ''
        self.odoo_attribute_id = False
        self.woocommerce_attribute_name = ''
    
    def action_create_mapping(self):
        """Create mapping based on selected type"""
        self.ensure_one()
        
        if not self.configuration_id:
            raise UserError(_("Please select a WooCommerce configuration."))
        
        self.write({
            'status': 'running',
            'mapping_results': 'Creating mapping...'
        })
        
        try:
            if self.mapping_type == 'product_categories':
                self._create_product_category_mapping()
            elif self.mapping_type == 'order_statuses':
                self._create_order_status_mapping()
            elif self.mapping_type == 'payment_methods':
                self._create_payment_method_mapping()
            elif self.mapping_type == 'shipping_methods':
                self._create_shipping_method_mapping()
            elif self.mapping_type == 'customer_groups':
                self._create_customer_group_mapping()
            elif self.mapping_type == 'product_attributes':
                self._create_product_attribute_mapping()
            
            self.write({
                'status': 'completed',
                'mapping_results': 'Mapping created successfully!'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Mapping Created'),
                    'message': _('Mapping created successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            self.write({
                'status': 'error',
                'mapping_results': f'Mapping failed: {str(e)}'
            })
            raise UserError(_(f'Mapping failed: {str(e)}'))
    
    def _create_product_category_mapping(self):
        """Create product category mapping"""
        if not self.odoo_category_id or not self.woocommerce_category_name:
            raise UserError(_("Please provide both Odoo category and WooCommerce category name."))
        
        # Create or update mapping record
        mapping = self.env['woocommerce.product.category.mapping'].search([
            ('odoo_category_id', '=', self.odoo_category_id.id),
            ('configuration_id', '=', self.configuration_id.id)
        ], limit=1)
        
        if mapping:
            mapping.write({
                'woocommerce_category_id': self.woocommerce_category_id,
                'woocommerce_category_name': self.woocommerce_category_name,
            })
        else:
            self.env['woocommerce.product.category.mapping'].create({
                'configuration_id': self.configuration_id.id,
                'odoo_category_id': self.odoo_category_id.id,
                'woocommerce_category_id': self.woocommerce_category_id,
                'woocommerce_category_name': self.woocommerce_category_name,
            })
        
        _logger.info(f"Created product category mapping: {self.odoo_category_id.name} -> {self.woocommerce_category_name}")
    
    def _create_order_status_mapping(self):
        """Create order status mapping"""
        if not self.odoo_state or not self.woocommerce_status:
            raise UserError(_("Please provide both Odoo state and WooCommerce status."))
        
        # Create or update mapping record
        mapping = self.env['woocommerce.order.status.mapping'].search([
            ('odoo_state', '=', self.odoo_state),
            ('configuration_id', '=', self.configuration_id.id)
        ], limit=1)
        
        if mapping:
            mapping.write({
                'woocommerce_status': self.woocommerce_status,
            })
        else:
            self.env['woocommerce.order.status.mapping'].create({
                'configuration_id': self.configuration_id.id,
                'odoo_state': self.odoo_state,
                'woocommerce_status': self.woocommerce_status,
                'name': f"{self.odoo_state.title()} -> {self.woocommerce_status}",
                'description': f"Mapping from Odoo {self.odoo_state} to WooCommerce {self.woocommerce_status}",
            })
        
        _logger.info(f"Created order status mapping: {self.odoo_state} -> {self.woocommerce_status}")
    
    def _create_payment_method_mapping(self):
        """Create payment method mapping"""
        if not self.odoo_payment_method or not self.woocommerce_payment_method:
            raise UserError(_("Please provide both Odoo and WooCommerce payment method names."))
        
        # Create or update mapping record
        mapping = self.env['woocommerce.payment.method.mapping'].search([
            ('odoo_payment_method', '=', self.odoo_payment_method),
            ('configuration_id', '=', self.configuration_id.id)
        ], limit=1)
        
        if mapping:
            mapping.write({
                'woocommerce_payment_method': self.woocommerce_payment_method,
            })
        else:
            self.env['woocommerce.payment.method.mapping'].create({
                'configuration_id': self.configuration_id.id,
                'odoo_payment_method': self.odoo_payment_method,
                'woocommerce_payment_method': self.woocommerce_payment_method,
                'name': f"{self.odoo_payment_method} -> {self.woocommerce_payment_method}",
                'description': f"Payment method mapping",
            })
        
        _logger.info(f"Created payment method mapping: {self.odoo_payment_method} -> {self.woocommerce_payment_method}")
    
    def _create_shipping_method_mapping(self):
        """Create shipping method mapping"""
        if not self.odoo_shipping_method or not self.woocommerce_shipping_method:
            raise UserError(_("Please provide both Odoo and WooCommerce shipping method names."))
        
        # Create or update mapping record
        mapping = self.env['woocommerce.shipping.method.mapping'].search([
            ('odoo_shipping_method', '=', self.odoo_shipping_method),
            ('configuration_id', '=', self.configuration_id.id)
        ], limit=1)
        
        if mapping:
            mapping.write({
                'woocommerce_shipping_method': self.woocommerce_shipping_method,
            })
        else:
            self.env['woocommerce.shipping.method.mapping'].create({
                'configuration_id': self.configuration_id.id,
                'odoo_shipping_method': self.odoo_shipping_method,
                'woocommerce_shipping_method': self.woocommerce_shipping_method,
                'name': f"{self.odoo_shipping_method} -> {self.woocommerce_shipping_method}",
                'description': f"Shipping method mapping",
            })
        
        _logger.info(f"Created shipping method mapping: {self.odoo_shipping_method} -> {self.woocommerce_shipping_method}")
    
    def _create_customer_group_mapping(self):
        """Create customer group mapping"""
        if not self.odoo_partner_category_id or not self.woocommerce_customer_group:
            raise UserError(_("Please provide both Odoo partner category and WooCommerce customer group."))
        
        # Create or update mapping record
        mapping = self.env['woocommerce.customer.group.mapping'].search([
            ('odoo_partner_category_id', '=', self.odoo_partner_category_id.id),
            ('configuration_id', '=', self.configuration_id.id)
        ], limit=1)
        
        if mapping:
            mapping.write({
                'woocommerce_customer_group': self.woocommerce_customer_group,
            })
        else:
            self.env['woocommerce.customer.group.mapping'].create({
                'configuration_id': self.configuration_id.id,
                'odoo_partner_category_id': self.odoo_partner_category_id.id,
                'woocommerce_customer_group': self.woocommerce_customer_group,
                'name': f"{self.odoo_partner_category_id.name} -> {self.woocommerce_customer_group}",
                'description': f"Customer group mapping",
            })
        
        _logger.info(f"Created customer group mapping: {self.odoo_partner_category_id.name} -> {self.woocommerce_customer_group}")
    
    def _create_product_attribute_mapping(self):
        """Create product attribute mapping"""
        if not self.odoo_attribute_id or not self.woocommerce_attribute_name:
            raise UserError(_("Please provide both Odoo attribute and WooCommerce attribute name."))
        
        # Create or update mapping record
        mapping = self.env['woocommerce.product.attribute.mapping'].search([
            ('odoo_attribute_id', '=', self.odoo_attribute_id.id),
            ('configuration_id', '=', self.configuration_id.id)
        ], limit=1)
        
        if mapping:
            mapping.write({
                'woocommerce_attribute_name': self.woocommerce_attribute_name,
            })
        else:
            self.env['woocommerce.product.attribute.mapping'].create({
                'configuration_id': self.configuration_id.id,
                'odoo_attribute_id': self.odoo_attribute_id.id,
                'woocommerce_attribute_name': self.woocommerce_attribute_name,
                'name': f"{self.odoo_attribute_id.name} -> {self.woocommerce_attribute_name}",
                'description': f"Product attribute mapping",
            })
        
        _logger.info(f"Created product attribute mapping: {self.odoo_attribute_id.name} -> {self.woocommerce_attribute_name}") 