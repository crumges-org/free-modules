# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..tools import WooCommerceTools

_logger = logging.getLogger(__name__)


class WooCommerceTestConnectionWizard(models.TransientModel):
    """WooCommerce Test Connection Wizard"""
    _name = 'woocommerce.test.connection.wizard'
    _description = 'WooCommerce Test Connection Wizard'

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
    
    test_result = fields.Text(
        string='Test Result',
        readonly=True
    )
    
    test_success = fields.Boolean(
        string='Test Successful',
        readonly=True
    )

    def action_test_connection(self):
        """Test WooCommerce API connection"""
        self.ensure_one()
        
        try:
            # Create a temporary configuration for testing
            test_config = self.env['woocommerce.configuration'].create({
                'name': 'Test Configuration',
                'woocommerce_url': self.woocommerce_url,
                'consumer_key': self.consumer_key,
                'consumer_secret': self.consumer_secret,
                'api_version': self.api_version,
                'timeout': self.timeout,
            })
            
            # Test the connection
            tools = WooCommerceTools(test_config)
            success, message = tools.test_connection()
            
            if success:
                # Try to get some basic information
                products = tools.get_products(per_page=1)
                orders = tools.get_orders(per_page=1)
                customers = tools.get_customers(per_page=1)
                
                result_text = f"✅ Connection successful!\n\n"
                result_text += f"Store URL: {self.woocommerce_url}\n"
                result_text += f"API Version: {self.api_version}\n"
                result_text += f"Timeout: {self.timeout} seconds\n\n"
                result_text += f"Store Information:\n"
                result_text += f"- Products available: {'Yes' if products else 'No'}\n"
                result_text += f"- Orders available: {'Yes' if orders else 'No'}\n"
                result_text += f"- Customers available: {'Yes' if customers else 'No'}\n"
                
                self.write({
                    'test_result': result_text,
                    'test_success': True,
                })
                
                # Clean up test configuration
                test_config.unlink()
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Connection test successful!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                result_text = f"❌ Connection failed!\n\n"
                result_text += f"Error: {message}\n\n"
                result_text += f"Please check:\n"
                result_text += f"- Store URL is correct and accessible\n"
                result_text += f"- Consumer Key and Secret are valid\n"
                result_text += f"- API version is supported\n"
                result_text += f"- WooCommerce REST API is enabled\n"
                
                self.write({
                    'test_result': result_text,
                    'test_success': False,
                })
                
                # Clean up test configuration
                test_config.unlink()
                
                raise UserError(_('Connection test failed: %s') % message)
                
        except Exception as e:
            result_text = f"❌ Connection test failed!\n\n"
            result_text += f"Error: {str(e)}\n\n"
            result_text += f"Please check your configuration and try again."
            
            self.write({
                'test_result': result_text,
                'test_success': False,
            })
            
            raise UserError(_('Connection test failed: %s') % str(e))

    def action_save_configuration(self):
        """Save the tested configuration"""
        self.ensure_one()
        
        if not self.test_success:
            raise UserError(_('Cannot save configuration: Connection test was not successful'))
        
        # Create or update configuration
        config = self.env['woocommerce.configuration'].search([
            ('woocommerce_url', '=', self.woocommerce_url)
        ], limit=1)
        
        if config:
            config.write({
                'consumer_key': self.consumer_key,
                'consumer_secret': self.consumer_secret,
                'api_version': self.api_version,
                'timeout': self.timeout,
                'connection_status': 'connected',
                'last_connection_test': fields.Datetime.now(),
                'connection_error_message': False,
            })
        else:
            config = self.env['woocommerce.configuration'].create({
                'name': f'WooCommerce Store - {self.woocommerce_url}',
                'woocommerce_url': self.woocommerce_url,
                'consumer_key': self.consumer_key,
                'consumer_secret': self.consumer_secret,
                'api_version': self.api_version,
                'timeout': self.timeout,
                'connection_status': 'connected',
                'last_connection_test': fields.Datetime.now(),
                'active': True,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.configuration',
            'res_id': config.id,
            'view_mode': 'form',
            'target': 'current',
        } 