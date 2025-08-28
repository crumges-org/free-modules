# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCommerceProductCategoryMapping(models.Model):
    """WooCommerce Product Category Mapping"""
    _name = 'woocommerce.product.category.mapping'
    _description = 'WooCommerce Product Category Mapping'
    _rec_name = 'name'
    _order = 'name'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    odoo_category_id = fields.Many2one(
        'product.category',
        string='Odoo Category',
        required=True,
        ondelete='cascade'
    )
    
    woocommerce_category_id = fields.Char(
        string='WooCommerce Category ID',
        help='WooCommerce category ID'
    )
    
    woocommerce_category_name = fields.Char(
        string='WooCommerce Category Name',
        required=True,
        help='WooCommerce category name'
    )
    
    name = fields.Char(
        string='Mapping Name',
        compute='_compute_name',
        store=True
    )
    
    description = fields.Text(
        string='Description',
        help='Mapping description'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    @api.depends('odoo_category_id', 'woocommerce_category_name')
    def _compute_name(self):
        for record in self:
            if record.odoo_category_id and record.woocommerce_category_name:
                record.name = f"{record.odoo_category_id.name} → {record.woocommerce_category_name}"
            else:
                record.name = "Unnamed Mapping"


class WooCommerceOrderStatusMapping(models.Model):
    """WooCommerce Order Status Mapping"""
    _name = 'woocommerce.order.status.mapping'
    _description = 'WooCommerce Order Status Mapping'
    _rec_name = 'name'
    _order = 'name'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    odoo_state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Odoo Order State', required=True)
    
    woocommerce_status = fields.Char(
        string='WooCommerce Status',
        required=True,
        help='WooCommerce order status'
    )
    
    name = fields.Char(
        string='Mapping Name',
        required=True,
        help='Mapping name'
    )
    
    description = fields.Text(
        string='Description',
        help='Mapping description'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )


class WooCommercePaymentMethodMapping(models.Model):
    """WooCommerce Payment Method Mapping"""
    _name = 'woocommerce.payment.method.mapping'
    _description = 'WooCommerce Payment Method Mapping'
    _rec_name = 'name'
    _order = 'name'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    odoo_payment_method = fields.Char(
        string='Odoo Payment Method',
        required=True,
        help='Odoo payment method name'
    )
    
    woocommerce_payment_method = fields.Char(
        string='WooCommerce Payment Method',
        required=True,
        help='WooCommerce payment method name'
    )
    
    name = fields.Char(
        string='Mapping Name',
        required=True,
        help='Mapping name'
    )
    
    description = fields.Text(
        string='Description',
        help='Mapping description'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )


class WooCommerceShippingMethodMapping(models.Model):
    """WooCommerce Shipping Method Mapping"""
    _name = 'woocommerce.shipping.method.mapping'
    _description = 'WooCommerce Shipping Method Mapping'
    _rec_name = 'name'
    _order = 'name'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    odoo_shipping_method = fields.Char(
        string='Odoo Shipping Method',
        required=True,
        help='Odoo shipping method name'
    )
    
    woocommerce_shipping_method = fields.Char(
        string='WooCommerce Shipping Method',
        required=True,
        help='WooCommerce shipping method name'
    )
    
    name = fields.Char(
        string='Mapping Name',
        required=True,
        help='Mapping name'
    )
    
    description = fields.Text(
        string='Description',
        help='Mapping description'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )


class WooCommerceCustomerGroupMapping(models.Model):
    """WooCommerce Customer Group Mapping"""
    _name = 'woocommerce.customer.group.mapping'
    _description = 'WooCommerce Customer Group Mapping'
    _rec_name = 'name'
    _order = 'name'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    odoo_partner_category_id = fields.Many2one(
        'res.partner.category',
        string='Odoo Partner Category',
        required=True,
        ondelete='cascade'
    )
    
    woocommerce_customer_group = fields.Char(
        string='WooCommerce Customer Group',
        required=True,
        help='WooCommerce customer group name'
    )
    
    name = fields.Char(
        string='Mapping Name',
        compute='_compute_name',
        store=True
    )
    
    description = fields.Text(
        string='Description',
        help='Mapping description'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    @api.depends('odoo_partner_category_id', 'woocommerce_customer_group')
    def _compute_name(self):
        for record in self:
            if record.odoo_partner_category_id and record.woocommerce_customer_group:
                record.name = f"{record.odoo_partner_category_id.name} → {record.woocommerce_customer_group}"
            else:
                record.name = "Unnamed Mapping"


class WooCommerceProductAttributeMapping(models.Model):
    """WooCommerce Product Attribute Mapping"""
    _name = 'woocommerce.product.attribute.mapping'
    _description = 'WooCommerce Product Attribute Mapping'
    _rec_name = 'name'
    _order = 'name'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    odoo_attribute_id = fields.Many2one(
        'product.attribute',
        string='Odoo Product Attribute',
        required=True,
        ondelete='cascade'
    )
    
    woocommerce_attribute_name = fields.Char(
        string='WooCommerce Attribute Name',
        required=True,
        help='WooCommerce attribute name'
    )
    
    name = fields.Char(
        string='Mapping Name',
        compute='_compute_name',
        store=True
    )
    
    description = fields.Text(
        string='Description',
        help='Mapping description'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    @api.depends('odoo_attribute_id', 'woocommerce_attribute_name')
    def _compute_name(self):
        for record in self:
            if record.odoo_attribute_id and record.woocommerce_attribute_name:
                record.name = f"{record.odoo_attribute_id.name} → {record.woocommerce_attribute_name}"
            else:
                record.name = "Unnamed Mapping"
