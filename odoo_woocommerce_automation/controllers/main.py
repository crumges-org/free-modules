# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
import json
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class WooCommerceController(http.Controller):
    """WooCommerce API Controller"""
    
    @http.route('/woocommerce/webhook', type='json', auth='public', csrf=False)
    def woocommerce_webhook(self, **kwargs):
        """Handle WooCommerce webhooks"""
        try:
            _logger.info(f"Received WooCommerce webhook: {kwargs}")
            
            # Validate webhook signature (implement security)
            # Process webhook data based on topic
            
            return {'status': 'success'}
        except Exception as e:
            _logger.error(f"Error processing WooCommerce webhook: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @http.route('/woocommerce/api/status', type='json', auth='user')
    def woocommerce_api_status(self, **kwargs):
        """Get WooCommerce API status"""
        try:
            config = request.env['woocommerce.configuration'].get_active_configuration()
            if config:
                return {
                    'status': 'success',
                    'connected': config.connection_status == 'connected',
                    'last_sync': {
                        'products': config.last_product_sync,
                        'orders': config.last_order_sync,
                        'customers': config.last_customer_sync,
                    }
                }
            else:
                return {
                    'status': 'error',
                    'message': 'No active configuration found'
                }
        except Exception as e:
            _logger.error(f"Error getting WooCommerce API status: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @http.route('/woocommerce/api/sync', type='json', auth='user')
    def woocommerce_api_sync(self, sync_type='all', **kwargs):
        """Trigger WooCommerce synchronization"""
        try:
            config = request.env['woocommerce.configuration'].get_active_configuration()
            if not config:
                return {'status': 'error', 'message': 'No active configuration found'}
            
            if sync_type == 'products' or sync_type == 'all':
                config.action_sync_products()
            
            if sync_type == 'orders' or sync_type == 'all':
                config.action_sync_orders()
            
            if sync_type == 'customers' or sync_type == 'all':
                config.action_sync_customers()
            
            return {'status': 'success', 'message': f'Sync {sync_type} completed'}
        except Exception as e:
            _logger.error(f"Error triggering WooCommerce sync: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @http.route('/woocommerce/dashboard/data', type='json', auth='user')
    def woocommerce_dashboard_data(self, **kwargs):
        """Get dashboard data for WooCommerce"""
        try:
            dashboard = request.env['woocommerce.dashboard'].get_dashboard_data()
            return {
                'status': 'success',
                'data': {
                    'connection_status': dashboard.connection_status,
                    'total_products_synced': dashboard.total_products_synced,
                    'total_orders_synced': dashboard.total_orders_synced,
                    'total_customers_synced': dashboard.total_customers_synced,
                    'total_sync_errors': dashboard.total_sync_errors,
                    'last_sync': {
                        'products': dashboard.last_product_sync,
                        'orders': dashboard.last_order_sync,
                        'customers': dashboard.last_customer_sync,
                    }
                }
            }
        except Exception as e:
            _logger.error(f"Error getting dashboard data: {e}")
            return {'status': 'error', 'message': str(e)} 