# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCommerceQueue(models.Model):
    """WooCommerce Data Queue Management"""
    _name = 'woocommerce.queue'
    _description = 'WooCommerce Data Queue'
    _rec_name = 'name'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(string='Queue Name', required=True, copy=False, tracking=True)
    queue_type = fields.Selection([
        ('product', 'Product'),
        ('order', 'Order'),
        ('customer', 'Customer'),
        ('coupon', 'Coupon'),
        ('category', 'Category'),
        ('tag', 'Tag'),
        ('inventory', 'Inventory'),
        ('webhook', 'Webhook')
    ], string='Queue Type', required=True, tracking=True)
    
    # Configuration Reference
    configuration_id = fields.Many2one(
        'woocommerce.configuration',
        string='WooCommerce Configuration',
        required=True,
        ondelete='cascade'
    )
    
    # Status and Processing
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('partial', 'Partially Done'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, compute='_compute_state', store=True)
    
    # Queue Lines
    queue_line_ids = fields.One2many('woocommerce.queue.line', 'queue_id', string='Queue Lines')
    
    # Statistics
    total_lines = fields.Integer(string='Total Lines', compute='_compute_statistics', store=True)
    processed_lines = fields.Integer(string='Processed Lines', compute='_compute_statistics', store=True)
    failed_lines = fields.Integer(string='Failed Lines', compute='_compute_statistics', store=True)
    pending_lines = fields.Integer(string='Pending Lines', compute='_compute_statistics', store=True)
    
    # Processing Information
    is_processing = fields.Boolean(string='Is Processing', default=False, tracking=True)
    processing_start_time = fields.Datetime(string='Processing Start Time', tracking=True)
    processing_end_time = fields.Datetime(string='Processing End Time', tracking=True)
    processing_duration = fields.Float(string='Processing Duration (seconds)', compute='_compute_duration')
    
    # Created By
    created_by = fields.Selection([
        ('import', 'Import Process'),
        ('export', 'Export Process'),
        ('webhook', 'Webhook'),
        ('manual', 'Manual'),
        ('cron', 'Scheduled Task')
    ], string='Created By', default='manual', tracking=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                default=lambda self: self.env.company, required=True)
    
    # Constraints
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Queue name must be unique!')
    ]

    @api.depends('queue_line_ids.state')
    def _compute_state(self):
        """Compute queue state based on line states"""
        for record in self:
            if not record.queue_line_ids:
                record.state = 'draft'
                continue
            
            total = len(record.queue_line_ids)
            done = len(record.queue_line_ids.filtered(lambda x: x.state == 'done'))
            failed = len(record.queue_line_ids.filtered(lambda x: x.state == 'failed'))
            cancelled = len(record.queue_line_ids.filtered(lambda x: x.state == 'cancelled'))
            pending = len(record.queue_line_ids.filtered(lambda x: x.state in ['draft', 'in_progress']))
            
            if done + cancelled == total:
                record.state = 'done'
            elif failed == total:
                record.state = 'failed'
            elif pending == total:
                record.state = 'draft'
            elif failed > 0 or pending > 0:
                record.state = 'partial'
            else:
                record.state = 'done'

    @api.depends('queue_line_ids.state')
    def _compute_statistics(self):
        """Compute queue statistics"""
        for record in self:
            lines = record.queue_line_ids
            record.total_lines = len(lines)
            record.processed_lines = len(lines.filtered(lambda x: x.state == 'done'))
            record.failed_lines = len(lines.filtered(lambda x: x.state == 'failed'))
            record.pending_lines = len(lines.filtered(lambda x: x.state in ['draft', 'in_progress']))

    @api.depends('processing_start_time', 'processing_end_time')
    def _compute_duration(self):
        """Compute processing duration"""
        for record in self:
            if record.processing_start_time and record.processing_end_time:
                duration = (record.processing_end_time - record.processing_start_time).total_seconds()
                record.processing_duration = duration
            else:
                record.processing_duration = 0.0

    @api.model
    def create(self, vals):
        """Override create to generate sequence"""
        if not vals.get('name'):
            sequence = self.env['ir.sequence'].next_by_code('woocommerce.queue')
            vals['name'] = sequence or f"Queue_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return super(WooCommerceQueue, self).create(vals)

    def action_process_queue(self):
        """Process the queue"""
        self.ensure_one()
        if self.state in ['done', 'failed', 'cancelled']:
            raise UserError(_('Cannot process queue in current state: %s') % self.state)
        
        if self.is_processing:
            raise UserError(_('Queue is already being processed'))
        
        try:
            self.write({
                'is_processing': True,
                'processing_start_time': fields.Datetime.now(),
                'state': 'in_progress'
            })
            
            # Process queue lines
            pending_lines = self.queue_line_ids.filtered(lambda x: x.state in ['draft', 'failed'])
            for line in pending_lines:
                try:
                    line.action_process()
                except Exception as e:
                    line.write({
                        'state': 'failed',
                        'error_message': str(e)
                    })
                    _logger.error(f"Failed to process queue line {line.id}: {str(e)}")
            
            self.write({
                'is_processing': False,
                'processing_end_time': fields.Datetime.now()
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Queue processed successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            self.write({
                'is_processing': False,
                'processing_end_time': fields.Datetime.now(),
                'state': 'failed'
            })
            raise UserError(_('Failed to process queue: %s') % str(e))

    def action_retry_failed_lines(self):
        """Retry failed queue lines"""
        self.ensure_one()
        failed_lines = self.queue_line_ids.filtered(lambda x: x.state == 'failed')
        if not failed_lines:
            raise UserError(_('No failed lines to retry'))
        
        failed_lines.write({'state': 'draft'})
        return self.action_process_queue()

    def action_cancel_queue(self):
        """Cancel the queue"""
        self.ensure_one()
        if self.is_processing:
            raise UserError(_('Cannot cancel queue while processing'))
        
        self.queue_line_ids.filtered(lambda x: x.state in ['draft', 'in_progress']).write({
            'state': 'cancelled'
        })
        self.write({'state': 'cancelled'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Queue cancelled successfully'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_queue_lines(self):
        """View queue lines"""
        return {
            'name': _('Queue Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.queue.line',
            'view_mode': 'list,form',
            'domain': [('queue_id', '=', self.id)],
            'context': {'default_queue_id': self.id},
        }

    def action_view_logs(self):
        """View related logs"""
        return {
            'name': _('Sync Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'woocommerce.sync.log',
            'view_mode': 'list,form',
            'domain': [('configuration_id', '=', self.configuration_id.id)],
            'context': {'default_configuration_id': self.configuration_id.id},
        }

    @api.model
    def _cleanup_old_queues(self, days=30):
        """Clean up old completed queues"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_queues = self.search([
            ('create_date', '<', cutoff_date),
            ('state', 'in', ['done', 'failed', 'cancelled'])
        ])
        
        if old_queues:
            count = len(old_queues)
            old_queues.unlink()
            _logger.info(f"Cleaned up {count} old queues")
            return count
        return 0

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.name} ({record.queue_type})"
            if record.state != 'done':
                name += f" [{record.state}]"
            result.append((record.id, name))
        return result


class WooCommerceQueueLine(models.Model):
    """WooCommerce Queue Line"""
    _name = 'woocommerce.queue.line'
    _description = 'WooCommerce Queue Line'
    _rec_name = 'name'
    _order = 'create_date desc'

    # Basic Information
    name = fields.Char(string='Line Name', required=True, copy=False)
    queue_id = fields.Many2one('woocommerce.queue', string='Queue', required=True, ondelete='cascade')
    
    # Data Information
    data_type = fields.Selection([
        ('product', 'Product'),
        ('order', 'Order'),
        ('customer', 'Customer'),
        ('coupon', 'Coupon'),
        ('category', 'Category'),
        ('tag', 'Tag'),
        ('inventory', 'Inventory'),
        ('webhook', 'Webhook')
    ], string='Data Type', required=True)
    
    operation = fields.Selection([
        ('import', 'Import'),
        ('export', 'Export'),
        ('update', 'Update'),
        ('delete', 'Delete')
    ], string='Operation', required=True)
    
    # WooCommerce Data
    woocommerce_id = fields.Char(string='WooCommerce ID')
    woocommerce_data = fields.Text(string='WooCommerce Data', help="JSON data from WooCommerce")
    
    # Odoo Data
    odoo_model = fields.Char(string='Odoo Model')
    odoo_record_id = fields.Integer(string='Odoo Record ID')
    
    # Status and Processing
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Error Handling
    error_message = fields.Text(string='Error Message')
    retry_count = fields.Integer(string='Retry Count', default=0)
    max_retries = fields.Integer(string='Max Retries', default=3)
    
    # Processing Information
    processing_start_time = fields.Datetime(string='Processing Start Time')
    processing_end_time = fields.Datetime(string='Processing End Time')
    processing_duration = fields.Float(string='Processing Duration (seconds)', compute='_compute_duration')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                default=lambda self: self.env.company, required=True)

    @api.depends('processing_start_time', 'processing_end_time')
    def _compute_duration(self):
        """Compute processing duration"""
        for record in self:
            if record.processing_start_time and record.processing_end_time:
                duration = (record.processing_end_time - record.processing_start_time).total_seconds()
                record.processing_duration = duration
            else:
                record.processing_duration = 0.0

    @api.model
    def create(self, vals):
        """Override create to generate sequence"""
        if not vals.get('name'):
            sequence = self.env['ir.sequence'].next_by_code('woocommerce.queue.line')
            vals['name'] = sequence or f"Line_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return super(WooCommerceQueueLine, self).create(vals)

    def action_process(self):
        """Process the queue line"""
        self.ensure_one()
        if self.state in ['done', 'cancelled']:
            return
        
        if self.retry_count >= self.max_retries:
            self.write({'state': 'failed', 'error_message': 'Max retries exceeded'})
            return
        
        try:
            self.write({
                'state': 'in_progress',
                'processing_start_time': fields.Datetime.now(),
                'retry_count': self.retry_count + 1
            })
            
            # Process based on operation and data type
            if self.operation == 'import':
                self._process_import()
            elif self.operation == 'export':
                self._process_export()
            elif self.operation == 'update':
                self._process_update()
            elif self.operation == 'delete':
                self._process_delete()
            
            self.write({
                'state': 'done',
                'processing_end_time': fields.Datetime.now()
            })
            
        except Exception as e:
            self.write({
                'state': 'failed',
                'error_message': str(e),
                'processing_end_time': fields.Datetime.now()
            })
            raise

    def _process_import(self):
        """Process import operation"""
        sync_service = self.env['woocommerce.sync.service']
        
        if self.data_type == 'product':
            sync_service.import_product(self.queue_id.configuration_id, self.woocommerce_id)
        elif self.data_type == 'order':
            sync_service.import_order(self.queue_id.configuration_id, self.woocommerce_id)
        elif self.data_type == 'customer':
            sync_service.import_customer(self.queue_id.configuration_id, self.woocommerce_id)
        elif self.data_type == 'coupon':
            sync_service.import_coupon(self.queue_id.configuration_id, self.woocommerce_id)

    def _process_export(self):
        """Process export operation"""
        sync_service = self.env['woocommerce.sync.service']
        
        if self.data_type == 'product':
            sync_service.export_product(self.queue_id.configuration_id, self.odoo_record_id)
        elif self.data_type == 'order':
            sync_service.export_order(self.queue_id.configuration_id, self.odoo_record_id)
        elif self.data_type == 'customer':
            sync_service.export_customer(self.queue_id.configuration_id, self.odoo_record_id)
        elif self.data_type == 'coupon':
            sync_service.export_coupon(self.queue_id.configuration_id, self.odoo_record_id)

    def _process_update(self):
        """Process update operation"""
        sync_service = self.env['woocommerce.sync.service']
        
        if self.data_type == 'product':
            sync_service.update_product(self.queue_id.configuration_id, self.woocommerce_id)
        elif self.data_type == 'order':
            sync_service.update_order(self.queue_id.configuration_id, self.woocommerce_id)
        elif self.data_type == 'customer':
            sync_service.update_customer(self.queue_id.configuration_id, self.woocommerce_id)
        elif self.data_type == 'coupon':
            sync_service.update_coupon(self.queue_id.configuration_id, self.woocommerce_id)

    def _process_delete(self):
        """Process delete operation"""
        sync_service = self.env['woocommerce.sync.service']
        
        if self.data_type == 'product':
            sync_service.delete_product(self.queue_id.configuration_id, self.woocommerce_id)
        elif self.data_type == 'order':
            sync_service.delete_order(self.queue_id.configuration_id, self.woocommerce_id)
        elif self.data_type == 'customer':
            sync_service.delete_customer(self.queue_id.configuration_id, self.woocommerce_id)
        elif self.data_type == 'coupon':
            sync_service.delete_coupon(self.queue_id.configuration_id, self.woocommerce_id)

    def action_retry(self):
        """Retry processing the line"""
        self.ensure_one()
        if self.state == 'failed':
            self.write({'state': 'draft'})
            return self.action_process()

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.name} ({record.operation} {record.data_type})"
            if record.state != 'done':
                name += f" [{record.state}]"
            result.append((record.id, name))
        return result
