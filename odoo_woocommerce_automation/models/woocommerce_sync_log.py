# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta

_logger = logging.getLogger(__name__)


class WooCommerceSyncLog(models.Model):
    """WooCommerce Synchronization Log Model"""
    _name = 'woocommerce.sync.log'
    _description = 'WooCommerce Synchronization Log'
    _order = 'create_date desc'
    _rec_name = 'sync_type'

    name = fields.Char(
        string='Log Name',
        compute='_compute_name',
        store=True
    )
    
    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='Configuration',
        required=True,
        ondelete='cascade'
    )
    
    sync_type = fields.Selection([
        ('product', 'Product'),
        ('order', 'Order'),
        ('customer', 'Customer'),
        ('inventory', 'Inventory'),
        ('category', 'Category'),
        ('test_connection', 'Test Connection'),
    ], string='Sync Type', required=True)
    
    operation = fields.Selection([
        ('import', 'Import'),
        ('export', 'Export'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('test', 'Test'),
    ], string='Operation', required=True)
    
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('in_progress', 'In Progress'),
    ], string='Status', default='in_progress')
    
    # Details
    records_processed = fields.Integer(
        string='Records Processed',
        default=0
    )
    
    records_created = fields.Integer(
        string='Records Created',
        default=0
    )
    
    records_updated = fields.Integer(
        string='Records Updated',
        default=0
    )
    
    records_failed = fields.Integer(
        string='Records Failed',
        default=0
    )
    
    # Timing
    start_time = fields.Datetime(
        string='Start Time',
        default=fields.Datetime.now
    )
    
    end_time = fields.Datetime(
        string='End Time'
    )
    
    duration = fields.Float(
        string='Duration (seconds)',
        compute='_compute_duration',
        store=True
    )
    
    # Error Information
    error_message = fields.Text(
        string='Error Message'
    )
    
    error_details = fields.Text(
        string='Error Details'
    )
    
    # Related Records
    product_ids = fields.Many2many(
        'product.template',
        string='Related Products'
    )
    
    order_ids = fields.Many2many(
        'sale.order',
        string='Related Orders'
    )
    
    customer_ids = fields.Many2many(
        'res.partner',
        string='Related Customers'
    )
    
    # User Information
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    @api.depends('sync_type', 'operation', 'start_time')
    def _compute_name(self):
        """Compute log name"""
        for record in self:
            if record.sync_type and record.operation:
                record.name = f"{record.sync_type.title()} {record.operation.title()} - {record.start_time}"
            else:
                record.name = f"Sync Log - {record.start_time}"

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """Compute sync duration"""
        for record in self:
            if record.start_time and record.end_time:
                duration = (record.end_time - record.start_time).total_seconds()
                record.duration = duration
            else:
                record.duration = 0.0

    def action_view_details(self):
        """View sync log details"""
        self.ensure_one()
        return {
            'name': _('Sync Log Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.sync.log',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_retry_sync(self):
        """Retry failed synchronization"""
        self.ensure_one()
        if self.status != 'error':
            raise UserError(_('Only failed synchronizations can be retried'))
        
        # Create a new sync log for retry
        new_log = self.create({
            'configuration_id': self.configuration_id.id,
            'sync_type': self.sync_type,
            'operation': self.operation,
            'status': 'in_progress',
            'user_id': self.env.user.id,
        })
        
        # Execute the sync based on type
        if self.sync_type == 'product':
            self.configuration_id.action_sync_products()
        elif self.sync_type == 'order':
            self.configuration_id.action_sync_orders()
        elif self.sync_type == 'customer':
            self.configuration_id.action_sync_customers()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Synchronization retry initiated'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_clear_logs(self):
        """Clear old sync logs"""
        # Clear logs older than 30 days
        cutoff_date = fields.Datetime.now() - timedelta(days=30)
        old_logs = self.search([
            ('create_date', '<', cutoff_date),
            ('status', 'in', ['success', 'error', 'warning'])
        ])
        
        if old_logs:
            old_logs.unlink()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('%d old sync logs cleared') % len(old_logs),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Info'),
                    'message': _('No old logs to clear'),
                    'type': 'info',
                    'sticky': False,
                }
            }

    @api.model
    def create_sync_log(self, configuration, sync_type, operation, **kwargs):
        """Create a sync log entry"""
        return self.create({
            'configuration_id': configuration.id,
            'sync_type': sync_type,
            'operation': operation,
            'user_id': self.env.user.id,
            **kwargs
        })

    def mark_success(self, **kwargs):
        """Mark sync log as successful"""
        self.write({
            'status': 'success',
            'end_time': fields.Datetime.now(),
            **kwargs
        })

    def mark_error(self, error_message, error_details=None, **kwargs):
        """Mark sync log as failed"""
        self.write({
            'status': 'error',
            'end_time': fields.Datetime.now(),
            'error_message': error_message,
            'error_details': error_details,
            **kwargs
        })

    def mark_warning(self, **kwargs):
        """Mark sync log as warning"""
        self.write({
            'status': 'warning',
            'end_time': fields.Datetime.now(),
            **kwargs
        })

    def update_progress(self, **kwargs):
        """Update sync log progress"""
        self.write(kwargs)

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.sync_type.title()} {record.operation.title()}"
            if record.status == 'error':
                name += f" ({_('Error')})"
            elif record.status == 'success':
                name += f" ({_('Success')})"
            result.append((record.id, name))
        return result

    @api.model
    def _cron_cleanup_old_logs(self):
        """Cron job to cleanup old sync logs"""
        _logger.info("Starting scheduled cleanup of old sync logs")
        
        # Keep logs for 30 days
        cutoff_date = fields.Datetime.now() - timedelta(days=30)
        old_logs = self.search([
            ('create_date', '<', cutoff_date),
            ('status', 'in', ['success', 'error', 'warning'])
        ])
        
        if old_logs:
            count = len(old_logs)
            old_logs.unlink()
            _logger.info(f"Cleaned up {count} old sync logs")
        else:
            _logger.info("No old sync logs to clean up") 