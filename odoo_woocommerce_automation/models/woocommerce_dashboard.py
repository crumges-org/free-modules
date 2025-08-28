# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class WooCommerceDashboard(models.Model):
    """WooCommerce Dashboard Model"""
    _name = 'woocommerce.dashboard'
    _description = 'WooCommerce Dashboard'
    _rec_name = 'configuration_id'

    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='Configuration',
        required=False,
        default=lambda self: self.env['woocommerce.configuration'].get_active_configuration()
    )
    
    # Connection Status
    connection_status = fields.Selection([
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
    ], string='Connection Status', compute='_compute_connection_status', store=True)
    
    last_connection_test = fields.Datetime(
        string='Last Connection Test',
        compute='_compute_connection_status',
        store=True
    )
    
    connection_error_message = fields.Text(
        string='Connection Error Message',
        compute='_compute_connection_status',
        store=True
    )
    
    # Sync Statistics
    total_products_synced = fields.Integer(
        string='Total Products Synced',
        compute='_compute_sync_statistics',
        store=True
    )
    
    total_orders_synced = fields.Integer(
        string='Total Orders Synced',
        compute='_compute_sync_statistics',
        store=True
    )
    
    total_customers_synced = fields.Integer(
        string='Total Customers Synced',
        compute='_compute_sync_statistics',
        store=True
    )
    
    total_sync_errors = fields.Integer(
        string='Total Sync Errors',
        compute='_compute_sync_statistics',
        store=True
    )

    # Extended KPIs
    total_queues_pending = fields.Integer(
        string='Pending Queue Lines',
        compute='_compute_extended_kpis',
        store=True
    )
    total_queues_failed = fields.Integer(
        string='Failed Queue Lines',
        compute='_compute_extended_kpis',
        store=True
    )
    total_active_webhooks = fields.Integer(
        string='Active Webhooks',
        compute='_compute_extended_kpis',
        store=True
    )
    total_coupons = fields.Integer(
        string='Coupons',
        compute='_compute_extended_kpis',
        store=True
    )
    
    # Last Sync Times
    last_product_sync = fields.Datetime(
        string='Last Product Sync',
        compute='_compute_sync_statistics',
        store=True
    )
    
    last_order_sync = fields.Datetime(
        string='Last Order Sync',
        compute='_compute_sync_statistics',
        store=True
    )
    
    last_customer_sync = fields.Datetime(
        string='Last Customer Sync',
        compute='_compute_sync_statistics',
        store=True
    )
    
    # Configuration Details
    woocommerce_url = fields.Char(
        string='WooCommerce URL',
        compute='_compute_configuration_details',
        store=True
    )
    
    api_version = fields.Selection([
        ('wc/v3', 'WC v3'),
        ('wc/v2', 'WC v2'),
    ], string='API Version', compute='_compute_configuration_details', store=True)
    
    sync_frequency = fields.Selection([
        ('5min', 'Every 5 minutes'),
        ('15min', 'Every 15 minutes'),
        ('30min', 'Every 30 minutes'),
        ('1hour', 'Every hour'),
        ('6hours', 'Every 6 hours'),
        ('12hours', 'Every 12 hours'),
        ('daily', 'Daily'),
    ], string='Sync Frequency', compute='_compute_configuration_details', store=True)
    
    sync_products = fields.Boolean(
        string='Sync Products',
        compute='_compute_configuration_details',
        store=True
    )
    
    sync_orders = fields.Boolean(
        string='Sync Orders',
        compute='_compute_configuration_details',
        store=True
    )
    
    sync_customers = fields.Boolean(
        string='Sync Customers',
        compute='_compute_configuration_details',
        store=True
    )
    
    # Recent Sync Logs
    recent_sync_logs = fields.Text(
        string='Recent Sync Logs',
        compute='_compute_recent_sync_logs',
        store=True
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    @api.depends('configuration_id')
    def _compute_connection_status(self):
        """Compute connection status from configuration"""
        for record in self:
            if record.configuration_id:
                record.connection_status = record.configuration_id.connection_status
                record.last_connection_test = record.configuration_id.last_connection_test
                record.connection_error_message = record.configuration_id.connection_error_message
            else:
                record.connection_status = 'disconnected'
                record.last_connection_test = False
                record.connection_error_message = False

    @api.depends('configuration_id')
    def _compute_sync_statistics(self):
        """Compute sync statistics from configuration and logs"""
        for record in self:
            if record.configuration_id:
                # Get statistics from configuration
                record.total_products_synced = record.configuration_id.total_products_synced
                record.total_orders_synced = record.configuration_id.total_orders_synced
                record.total_customers_synced = record.configuration_id.total_customers_synced
                record.last_product_sync = record.configuration_id.last_product_sync
                record.last_order_sync = record.configuration_id.last_order_sync
                record.last_customer_sync = record.configuration_id.last_customer_sync
                
                # Calculate sync errors in last 24 hours
                yesterday = datetime.now() - timedelta(days=1)
                error_logs = self.env['woocommerce.sync.log'].search([
                    ('configuration_id', '=', record.configuration_id.id),
                    ('status', '=', 'error'),
                    ('start_time', '>=', yesterday)
                ])
                record.total_sync_errors = len(error_logs)
            else:
                record.total_products_synced = 0
                record.total_orders_synced = 0
                record.total_customers_synced = 0
                record.total_sync_errors = 0
                record.last_product_sync = False
                record.last_order_sync = False
                record.last_customer_sync = False

    @api.depends('configuration_id')
    def _compute_configuration_details(self):
        """Compute configuration details"""
        for record in self:
            if record.configuration_id:
                record.woocommerce_url = record.configuration_id.woocommerce_url
                record.api_version = record.configuration_id.api_version
                record.sync_frequency = record.configuration_id.sync_frequency
                record.sync_products = record.configuration_id.sync_products
                record.sync_orders = record.configuration_id.sync_orders
                record.sync_customers = record.configuration_id.sync_customers
            else:
                record.woocommerce_url = False
                record.api_version = False
                record.sync_frequency = False
                record.sync_products = False
                record.sync_orders = False
                record.sync_customers = False

    @api.depends('configuration_id')
    def _compute_recent_sync_logs(self):
        """Compute recent sync logs"""
        for record in self:
            if record.configuration_id:
                # Get last 10 sync logs
                recent_logs = self.env['woocommerce.sync.log'].search([
                    ('configuration_id', '=', record.configuration_id.id)
                ], limit=10, order='create_date desc')
                
                log_text = ""
                for log in recent_logs:
                    status_icon = "✅" if log.status == 'success' else "❌" if log.status == 'error' else "⚠️"
                    log_text += f"{status_icon} {log.sync_type.title()} {log.operation.title()} - {log.start_time.strftime('%Y-%m-%d %H:%M')}\n"
                
                record.recent_sync_logs = log_text
            else:
                record.recent_sync_logs = ""

    @api.depends('configuration_id')
    def _compute_extended_kpis(self):
        """Compute extended KPIs sourced from new models (queues, webhooks, coupons)."""
        for record in self:
            if record.configuration_id:
                # Queue KPIs
                queue_lines = self.env['woocommerce.queue.line'].search([
                    ('queue_id.configuration_id', '=', record.configuration_id.id)
                ], limit=0)
                record.total_queues_pending = len(queue_lines.filtered(lambda l: l.state in ['draft', 'in_progress']))
                record.total_queues_failed = len(queue_lines.filtered(lambda l: l.state == 'failed'))

                # Webhooks KPI
                record.total_active_webhooks = self.env['woocommerce.webhook'].search_count([
                    ('configuration_id', '=', record.configuration_id.id),
                    ('status', '=', 'active')
                ])

                # Coupons KPI
                record.total_coupons = self.env['woocommerce.coupon'].search_count([
                    ('configuration_id', '=', record.configuration_id.id)
                ])
            else:
                record.total_queues_pending = 0
                record.total_queues_failed = 0
                record.total_active_webhooks = 0
                record.total_coupons = 0

    def action_test_connection(self):
        """Test WooCommerce connection"""
        self.ensure_one()
        if self.configuration_id:
            return self.configuration_id.action_test_connection()
        else:
            raise UserError(_('No active configuration found'))

    def action_sync_products(self):
        """Sync products"""
        self.ensure_one()
        if self.configuration_id:
            return self.configuration_id.action_sync_products()
        else:
            raise UserError(_('No active configuration found'))

    def action_sync_orders(self):
        """Sync orders"""
        self.ensure_one()
        if self.configuration_id:
            return self.configuration_id.action_sync_orders()
        else:
            raise UserError(_('No active configuration found'))

    def action_sync_customers(self):
        """Sync customers"""
        self.ensure_one()
        if self.configuration_id:
            return self.configuration_id.action_sync_customers()
        else:
            raise UserError(_('No active configuration found'))

    def action_view_configuration(self):
        """View configuration"""
        self.ensure_one()
        if self.configuration_id:
            return {
                'name': _('WooCommerce Configuration'),
                'type': 'ir.actions.act_window',
                'res_model': 'woocommerce.configuration',
                'res_id': self.configuration_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError(_('No active configuration found'))

    def action_view_sync_logs(self):
        """View sync logs"""
        self.ensure_one()
        if self.configuration_id:
            return self.configuration_id.action_view_sync_logs()
        else:
            raise UserError(_('No active configuration found'))

    def action_open_import_wizard(self):
        """Open import wizard"""
        if not self.configuration_id:
            raise UserError(_('Please create a WooCommerce configuration first before using import features.'))
        return {
            'name': _('Import from WooCommerce'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_configuration_id': self.configuration_id.id,
            }
        }

    def action_open_export_wizard(self):
        """Open export wizard"""
        if not self.configuration_id:
            raise UserError(_('Please create a WooCommerce configuration first before using export features.'))
        return {
            'name': _('Export to WooCommerce'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_configuration_id': self.configuration_id.id,
            }
        }

    def action_open_mapping_wizard(self):
        """Open mapping wizard"""
        if not self.configuration_id:
            raise UserError(_('Please create a WooCommerce configuration first before using mapping features.'))
        return {
            'name': _('WooCommerce Mapping'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.mapping.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_configuration_id': self.configuration_id.id,
            }
        }

    def action_open_configuration(self):
        """Open configuration settings"""
        if self.configuration_id:
            return {
                'name': _('WooCommerce Configuration'),
                'type': 'ir.actions.act_window',
                'res_model': 'woocommerce.configuration',
                'res_id': self.configuration_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'name': _('WooCommerce Configurations'),
                'type': 'ir.actions.act_window',
                'res_model': 'woocommerce.configuration',
                'view_mode': 'list,form',
                'target': 'current',
            }

    def action_open_queues(self):
        """Open queues for the current configuration"""
        if not self.configuration_id:
            raise UserError(_('Please create a WooCommerce configuration first.'))
        return {
            'name': _('WooCommerce Queues'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.queue',
            'view_mode': 'list,form',
            'domain': [('configuration_id', '=', self.configuration_id.id)],
            'context': {'default_configuration_id': self.configuration_id.id},
            'target': 'current',
        }

    def action_open_webhooks(self):
        """Open webhooks for the current configuration"""
        if not self.configuration_id:
            raise UserError(_('Please create a WooCommerce configuration first.'))
        return {
            'name': _('WooCommerce Webhooks'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.webhook',
            'view_mode': 'list,form',
            'domain': [('configuration_id', '=', self.configuration_id.id)],
            'context': {'default_configuration_id': self.configuration_id.id},
            'target': 'current',
        }

    def action_open_coupons(self):
        """Open coupons for the current configuration"""
        if not self.configuration_id:
            raise UserError(_('Please create a WooCommerce configuration first.'))
        return {
            'name': _('WooCommerce Coupons'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.coupon',
            'view_mode': 'list,form',
            'domain': [('configuration_id', '=', self.configuration_id.id)],
            'context': {'default_configuration_id': self.configuration_id.id},
            'target': 'current',
        }

    def action_open_process_history(self):
        """Open process history records"""
        if not self.configuration_id:
            raise UserError(_('Please create a WooCommerce configuration first.'))
        return {
            'name': _('WooCommerce Process History'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.process.history',
            'view_mode': 'list,form',
            'domain': [('configuration_id', '=', self.configuration_id.id)],
            'context': {'default_configuration_id': self.configuration_id.id},
            'target': 'current',
        }

    @api.model
    def get_dashboard_data(self):
        """Get dashboard data for the current user"""
        config = self.env['woocommerce.configuration'].get_active_configuration()
        if config:
            dashboard = self.search([('configuration_id', '=', config.id)], limit=1)
            if not dashboard:
                dashboard = self.create({'configuration_id': config.id})
            return dashboard
        else:
            # Create a default dashboard without configuration
            dashboard = self.search([('configuration_id', '=', False)], limit=1)
            if not dashboard:
                dashboard = self.create({})
            return dashboard

    def refresh_dashboard(self):
        """Refresh dashboard data"""
        self.ensure_one()
        self._compute_connection_status()
        self._compute_sync_statistics()
        self._compute_configuration_details()
        self._compute_recent_sync_logs()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Dashboard refreshed successfully'),
                'type': 'success',
                'sticky': False,
            }
        } 