# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
import requests
import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import woocommerce
from woocommerce import API

_logger = logging.getLogger(__name__)


class WooCommerceTools:
    """Utility class for WooCommerce API operations"""
    
    def __init__(self, config=None, url=None, consumer_key=None, consumer_secret=None, version="wc/v3", timeout=30):
        """Initialize WooCommerce API client"""
        if config:
            self.config = config
            self.url = config.woocommerce_url
            self.consumer_key = config.consumer_key
            self.consumer_secret = config.consumer_secret
            self.version = config.api_version
            self.timeout = config.timeout
        else:
            self.config = None
            self.url = url
            self.consumer_key = consumer_key
            self.consumer_secret = consumer_secret
            self.version = version
            self.timeout = timeout
        
        self.wcapi = None
        self._init_api_client()
    
    def _init_api_client(self):
        """Initialize WooCommerce API client"""
        try:
            self.wcapi = API(
                url=self.url,
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                version=self.version,
                timeout=self.timeout
            )
        except Exception as e:
            _logger.error(f"Failed to initialize WooCommerce API: {e}")
            raise UserError(_("Failed to initialize WooCommerce API connection"))
    
    def test_connection(self):
        """Test WooCommerce API connection"""
        try:
            response = self.wcapi.get("")
            if response.status_code == 200:
                return True, "Connection successful"
            else:
                return False, f"Connection failed: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def get_store_info(self):
        """Get WooCommerce store information"""
        try:
            response = self.wcapi.get("")
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"Failed to get store info: {response.status_code}")
                return None
        except Exception as e:
            _logger.error(f"Error getting store info: {e}")
            return None
    
    def get_products(self, page=1, per_page=100):
        """Get products from WooCommerce"""
        try:
            response = self.wcapi.get("products", params={
                'page': page,
                'per_page': per_page
            })
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"Failed to get products: {response.status_code}")
                return []
        except Exception as e:
            _logger.error(f"Error getting products: {e}")
            return []
    
    def create_product(self, product_data):
        """Create product in WooCommerce"""
        try:
            response = self.wcapi.post("products", product_data)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                _logger.error(f"Failed to create product: {response.status_code}")
                return None
        except Exception as e:
            _logger.error(f"Error creating product: {e}")
            return None
    
    def update_product(self, product_id, product_data):
        """Update product in WooCommerce"""
        try:
            response = self.wcapi.put(f"products/{product_id}", product_data)
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"Failed to update product: {response.status_code}")
                return None
        except Exception as e:
            _logger.error(f"Error updating product: {e}")
            return None
    
    def get_orders(self, page=1, per_page=100, status=None):
        """Get orders from WooCommerce"""
        try:
            params = {
                'page': page,
                'per_page': per_page
            }
            if status:
                params['status'] = status
            
            response = self.wcapi.get("orders", params=params)
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"Failed to get orders: {response.status_code}")
                return []
        except Exception as e:
            _logger.error(f"Error getting orders: {e}")
            return []
    
    def update_order_status(self, order_id, status):
        """Update order status in WooCommerce"""
        try:
            response = self.wcapi.put(f"orders/{order_id}", {
                'status': status
            })
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"Failed to update order status: {response.status_code}")
                return None
        except Exception as e:
            _logger.error(f"Error updating order status: {e}")
            return None
    
    def get_customers(self, page=1, per_page=100):
        """Get customers from WooCommerce"""
        try:
            response = self.wcapi.get("customers", params={
                'page': page,
                'per_page': per_page
            })
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"Failed to get customers: {response.status_code}")
                return []
        except Exception as e:
            _logger.error(f"Error getting customers: {e}")
            return []
    
    def create_customer(self, customer_data):
        """Create customer in WooCommerce"""
        try:
            response = self.wcapi.post("customers", customer_data)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                _logger.error(f"Failed to create customer: {response.status_code}")
                return None
        except Exception as e:
            _logger.error(f"Error creating customer: {e}")
            return None


class WooCommerceDataMapper:
    """Map data between Odoo and WooCommerce formats"""
    
    @staticmethod
    def map_product_to_woocommerce(product):
        """Map Odoo product to WooCommerce format"""
        return {
            'name': product.name,
            'type': 'simple' if product.type == 'product' else 'variable',
            'regular_price': str(product.list_price),
            'description': product.description or '',
            'short_description': product.description_sale or '',
            'categories': [],  # TODO: Map categories
            'images': [],  # TODO: Map images
            'manage_stock': True,
            'stock_quantity': product.qty_available,
            'stock_status': 'instock' if product.qty_available > 0 else 'outofstock',
            'sku': product.default_code or '',
            'status': 'publish' if product.active else 'draft',
        }
    
    @staticmethod
    def map_woocommerce_product_to_odoo(wc_product):
        """Map WooCommerce product to Odoo format"""
        return {
            'name': wc_product.get('name', ''),
            'default_code': wc_product.get('sku', ''),
            'list_price': float(wc_product.get('regular_price', 0)),
            'description': wc_product.get('description', ''),
            'description_sale': wc_product.get('short_description', ''),
            'type': 'product' if wc_product.get('type') == 'simple' else 'consu',
            'active': wc_product.get('status') == 'publish',
        }
    
    @staticmethod
    def map_order_to_woocommerce(order):
        """Map Odoo sale order to WooCommerce format"""
        return {
            'status': 'processing',  # Default status
            'currency': order.currency_id.name,
            'customer_id': order.partner_id.woocommerce_customer_id or None,
            'billing': {
                'first_name': order.partner_id.name.split()[0] if order.partner_id.name else '',
                'last_name': ' '.join(order.partner_id.name.split()[1:]) if order.partner_id.name else '',
                'email': order.partner_id.email or '',
                'phone': order.partner_id.phone or '',
                'address_1': order.partner_id.street or '',
                'city': order.partner_id.city or '',
                'state': order.partner_id.state_id.name or '',
                'postcode': order.partner_id.zip or '',
                'country': order.partner_id.country_id.code or '',
            },
            'shipping': {
                'first_name': order.partner_shipping_id.name.split()[0] if order.partner_shipping_id.name else '',
                'last_name': ' '.join(order.partner_shipping_id.name.split()[1:]) if order.partner_shipping_id.name else '',
                'address_1': order.partner_shipping_id.street or '',
                'city': order.partner_shipping_id.city or '',
                'state': order.partner_shipping_id.state_id.name or '',
                'postcode': order.partner_shipping_id.zip or '',
                'country': order.partner_shipping_id.country_id.code or '',
            },
            'line_items': [
                {
                    'product_id': line.product_id.woocommerce_product_id,
                    'quantity': line.product_uom_qty,
                    'price': str(line.price_unit),
                }
                for line in order.order_line
                if line.product_id.woocommerce_product_id
            ],
        }
    
    @staticmethod
    def map_woocommerce_order_to_odoo(wc_order):
        """Map WooCommerce order to Odoo format"""
        return {
            'name': f"WC-{wc_order.get('id', '')}",
            'partner_id': None,  # Will be set during import
            'partner_shipping_id': None,  # Will be set during import
            'date_order': wc_order.get('date_created', fields.Datetime.now()),
            'state': 'draft',
            'woocommerce_order_id': wc_order.get('id'),
            'woocommerce_status': wc_order.get('status'),
        }
    
    @staticmethod
    def map_customer_to_woocommerce(partner):
        """Map Odoo partner to WooCommerce format"""
        return {
            'email': partner.email,
            'first_name': partner.name.split()[0] if partner.name else '',
            'last_name': ' '.join(partner.name.split()[1:]) if partner.name else '',
            'username': partner.email,
            'billing': {
                'first_name': partner.name.split()[0] if partner.name else '',
                'last_name': ' '.join(partner.name.split()[1:]) if partner.name else '',
                'email': partner.email or '',
                'phone': partner.phone or '',
                'address_1': partner.street or '',
                'city': partner.city or '',
                'state': partner.state_id.name or '',
                'postcode': partner.zip or '',
                'country': partner.country_id.code or '',
            },
        }
    
    @staticmethod
    def map_woocommerce_customer_to_odoo(wc_customer):
        """Map WooCommerce customer to Odoo format"""
        return {
            'name': f"{wc_customer.get('first_name', '')} {wc_customer.get('last_name', '')}".strip(),
            'email': wc_customer.get('email', ''),
            'phone': wc_customer.get('billing', {}).get('phone', ''),
            'street': wc_customer.get('billing', {}).get('address_1', ''),
            'city': wc_customer.get('billing', {}).get('city', ''),
            'zip': wc_customer.get('billing', {}).get('postcode', ''),
            'country_id': None,  # Will be set during import
            'state_id': None,  # Will be set during import
            'woocommerce_customer_id': wc_customer.get('id'),
        }


def post_init_hook(env):
    """Post-installation hook"""
    _logger.info("Initializing Odoo WooCommerce Automation module...")
    
    # Handle optional account_invoice_extract module (Enterprise Edition feature)
    try:
        invoice_extract_module = env['ir.module.module'].search([
            ('name', '=', 'account_invoice_extract')
        ])
        
        if invoice_extract_module:
            if invoice_extract_module.state != 'installed':
                _logger.info("Installing account_invoice_extract module (Enterprise Edition)...")
                invoice_extract_module.button_immediate_install()
                _logger.info("account_invoice_extract module installed successfully")
            else:
                _logger.info("account_invoice_extract module is already installed")
                
            # Update the module to ensure all fields are properly registered
            _logger.info("Updating account_invoice_extract module...")
            invoice_extract_module.button_immediate_upgrade()
            _logger.info("account_invoice_extract module updated successfully")
        else:
            _logger.info("account_invoice_extract module not available (Community Edition) - module will work without invoice digitization features")
            
    except Exception as e:
        _logger.info(f"account_invoice_extract module not available: {e} - module will work without invoice digitization features")
    
    # Ensure account module is up to date
    try:
        account_module = env['ir.module.module'].search([
            ('name', '=', 'account')
        ])
        
        if account_module:
            _logger.info("Updating account module...")
            account_module.button_immediate_upgrade()
            _logger.info("account module updated successfully")
            
    except Exception as e:
        _logger.error(f"Error updating account module: {e}")
    
    # Create default configuration
    config = env['woocommerce.configuration'].search([], limit=1)
    if not config:
        env['woocommerce.configuration'].create({
            'name': 'Default WooCommerce Configuration',
            'active': False,
        })
    
    _logger.info("Odoo WooCommerce Automation module initialized successfully")


def uninstall_hook(env):
    """Uninstallation hook"""
    _logger.info("Uninstalling Odoo WooCommerce Automation module...")
    
    # Clean up any module-specific data if needed
    _logger.info("Odoo WooCommerce Automation module uninstalled successfully") 