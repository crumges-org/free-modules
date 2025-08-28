# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WooCommerceProcessHistory(models.Model):
	"""WooCommerce Process History Tracking"""
	_name = 'woocommerce.process.history'
	_description = 'WooCommerce Process History'
	_rec_name = 'name'
	_order = 'create_date desc'
	_inherit = ['mail.thread', 'mail.activity.mixin']

	# Basic Information
	name = fields.Char(string='Process Name', required=True, copy=False, tracking=True)
	process_type = fields.Selection([
		('import', 'Import'),
		('export', 'Export'),
		('sync', 'Synchronization'),
		('webhook', 'Webhook'),
		('queue', 'Queue Processing'),
		('mapping', 'Mapping'),
		('test', 'Test'),
		('cleanup', 'Cleanup'),
		('other', 'Other')
	], string='Process Type', required=True, tracking=True)
	
	# Configuration Reference
	configuration_id = fields.Many2one(
		'woocommerce.configuration',
		string='WooCommerce Configuration',
		required=True,
		ondelete='cascade'
	)
	
	# Process Details
	description = fields.Text(string='Description', tracking=True)
	status = fields.Selection([
		('running', 'Running'),
		('completed', 'Completed'),
		('failed', 'Failed'),
		('cancelled', 'Cancelled'),
		('partial', 'Partially Completed')
	], string='Status', default='running', tracking=True)
	
	# Timing Information
	start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now, tracking=True)
	end_time = fields.Datetime(string='End Time', tracking=True)
	duration = fields.Float(string='Duration (seconds)', compute='_compute_duration', store=True)
	
	# Statistics
	total_items = fields.Integer(string='Total Items', default=0, tracking=True)
	processed_items = fields.Integer(string='Processed Items', default=0, tracking=True)
	failed_items = fields.Integer(string='Failed Items', default=0, tracking=True)
	skipped_items = fields.Integer(string='Skipped Items', default=0, tracking=True)
	
	# Progress Tracking
	progress_percentage = fields.Float(string='Progress (%)', compute='_compute_progress', store=True)
	
	# Error Handling
	error_message = fields.Text(string='Error Message')
	error_details = fields.Text(string='Error Details')
	
	# User Information
	user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, tracking=True)
	
	# Related Records
	related_model = fields.Char(string='Related Model')
	related_record_ids = fields.Text(string='Related Record IDs', help="Comma-separated list of related record IDs")
	
	# Process Lines
	process_line_ids = fields.One2many('woocommerce.process.history.line', 'process_id', string='Process Lines')
	
	# Company
	company_id = fields.Many2one('res.company', string='Company',
								default=lambda self: self.env.company, required=True)
	
	# Constraints
	_sql_constraints = [
		('name_unique', 'unique(name)', 'Process name must be unique!')
	]

	@api.depends('start_time', 'end_time')
	def _compute_duration(self):
		"""Compute process duration"""
		for record in self:
			if record.start_time and record.end_time:
				duration = (record.end_time - record.start_time).total_seconds()
				record.duration = duration
			else:
				record.duration = 0.0

	@api.depends('total_items', 'processed_items', 'failed_items', 'skipped_items')
	def _compute_progress(self):
		"""Compute progress percentage"""
		for record in self:
			if record.total_items > 0:
				completed = record.processed_items + record.failed_items + record.skipped_items
				record.progress_percentage = (completed / record.total_items) * 100
			else:
				record.progress_percentage = 0.0

	@api.model
	def create(self, vals):
		"""Override create to generate sequence"""
		if not vals.get('name'):
			sequence = self.env['ir.sequence'].next_by_code('woocommerce.process.history')
			vals['name'] = sequence or f"Process_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}"
		return super(WooCommerceProcessHistory, self).create(vals)

	def action_mark_completed(self):
		"""Mark process as completed"""
		self.ensure_one()
		self.write({
			'status': 'completed',
			'end_time': fields.Datetime.now()
		})
		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': _('Success'),
				'message': _('Process marked as completed'),
				'type': 'success',
				'sticky': False,
			}
		}

	def action_mark_failed(self, error_message=None):
		"""Mark process as failed"""
		self.ensure_one()
		vals = {
			'status': 'failed',
			'end_time': fields.Datetime.now()
		}
		if error_message:
			vals['error_message'] = error_message
		self.write(vals)
		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': _('Failed'),
				'message': _('Process marked as failed'),
				'type': 'danger',
				'sticky': False,
			}
		}

	def action_cancel_process(self):
		"""Cancel the process"""
		self.ensure_one()
		if self.status == 'running':
			self.write({
				'status': 'cancelled',
				'end_time': fields.Datetime.now()
			})
			return {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': _('Cancelled'),
					'message': _('Process cancelled successfully'),
					'type': 'warning',
					'sticky': False,
				}
			}
		else:
			raise UserError(_('Cannot cancel process in current status: %s') % self.status)

	def action_view_process_lines(self):
		"""View process lines"""
		return {
			'name': _('Process Lines'),
			'type': 'ir.actions.act_window',
			'res_model': 'woocommerce.process.history.line',
			'view_mode': 'list,form',
			'domain': [('process_id', '=', self.id)],
			'context': {'default_process_id': self.id},
		}

	def action_retry_failed_items(self):
		"""Retry failed items"""
		self.ensure_one()
		failed_lines = self.process_line_ids.filtered(lambda x: x.status == 'failed')
		if not failed_lines:
			raise UserError(_('No failed items to retry'))
		
		# Reset failed lines
		failed_lines.write({'status': 'pending'})
		
		# Create new process for retry
		new_process = self.create({
			'name': f"Retry_{self.name}",
			'process_type': self.process_type,
			'configuration_id': self.configuration_id.id,
			'description': f"Retry of failed items from {self.name}",
			'total_items': len(failed_lines),
			'user_id': self.env.user.id
		})
		
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'woocommerce.process.history',
			'res_id': new_process.id,
			'view_mode': 'form',
			'target': 'current',
		}

	@api.model
	def _cleanup_old_history(self, days=30):
		"""Clean up old process history"""
		cutoff_date = fields.Datetime.now() - timedelta(days=days)
		old_history = self.search([
			('create_date', '<', cutoff_date),
			('status', 'in', ['completed', 'failed', 'cancelled'])
		])
		
		if old_history:
			count = len(old_history)
			old_history.unlink()
			_logger.info(f"Cleaned up {count} old process history records")
			return count
		return 0

	def name_get(self):
		"""Custom name display"""
		result = []
		for record in self:
			name = f"{record.name} ({record.process_type})"
			if record.status != 'completed':
				name += f" [{record.status}]"
			result.append((record.id, name))
		return result


class WooCommerceProcessHistoryLine(models.Model):
	"""WooCommerce Process History Line"""
	_name = 'woocommerce.process.history.line'
	_description = 'WooCommerce Process History Line'
	_rec_name = 'name'
	_order = 'create_date desc'

	# Basic Information
	name = fields.Char(string='Line Name', required=True, copy=False)
	process_id = fields.Many2one('woocommerce.process.history', string='Process', required=True, ondelete='cascade')
	
	# Line Details
	line_type = fields.Selection([
		('product', 'Product'),
		('order', 'Order'),
		('customer', 'Customer'),
		('coupon', 'Coupon'),
		('category', 'Category'),
		('tag', 'Tag'),
		('attribute', 'Attribute'),
		('webhook', 'Webhook'),
		('other', 'Other')
	], string='Line Type', required=True)
	
	operation = fields.Selection([
		('import', 'Import'),
		('export', 'Export'),
		('update', 'Update'),
		('delete', 'Delete'),
		('sync', 'Synchronize'),
		('validate', 'Validate'),
		('other', 'Other')
	], string='Operation', required=True)
	
	# Status and Processing
	status = fields.Selection([
		('pending', 'Pending'),
		('running', 'Running'),
		('completed', 'Completed'),
		('failed', 'Failed'),
		('skipped', 'Skipped')
	], string='Status', default='pending', tracking=True)
	
	# Data Information
	woocommerce_id = fields.Char(string='WooCommerce ID')
	odoo_id = fields.Integer(string='Odoo ID')
	data_summary = fields.Text(string='Data Summary', help="Brief summary of the data being processed")
	
	# Error Handling
	error_message = fields.Text(string='Error Message')
	error_details = fields.Text(string='Error Details')
	
	# Timing Information
	start_time = fields.Datetime(string='Start Time')
	end_time = fields.Datetime(string='End Time')
	duration = fields.Float(string='Duration (seconds)', compute='_compute_duration')
	
	# Retry Information
	retry_count = fields.Integer(string='Retry Count', default=0)
	max_retries = fields.Integer(string='Max Retries', default=3)
	
	# Company
	company_id = fields.Many2one('res.company', string='Company',
								default=lambda self: self.env.company, required=True)

	@api.depends('start_time', 'end_time')
	def _compute_duration(self):
		"""Compute line duration"""
		for record in self:
			if record.start_time and record.end_time:
				duration = (record.end_time - record.start_time).total_seconds()
				record.duration = duration
			else:
				record.duration = 0.0

	@api.model
	def create(self, vals):
		"""Override create to generate sequence"""
		if not vals.get('name'):
			sequence = self.env['ir.sequence'].next_by_code('woocommerce.process.history.line')
			vals['name'] = sequence or f"Line_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}"
		return super(WooCommerceProcessHistoryLine, self).create(vals)

	def action_retry(self):
		"""Retry processing the line"""
		self.ensure_one()
		if self.status == 'failed' and self.retry_count < self.max_retries:
			self.write({
				'status': 'pending',
				'retry_count': self.retry_count + 1,
				'error_message': '',
				'error_details': ''
			})
			return {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': _('Success'),
					'message': _('Line queued for retry'),
					'type': 'success',
					'sticky': False,
				}
			}
		else:
			raise UserError(_('Cannot retry line in current status or max retries exceeded'))

	def name_get(self):
		"""Custom name display"""
		result = []
		for record in self:
			name = f"{record.name} ({record.operation} {record.line_type})"
			if record.status != 'completed':
				name += f" [{record.status}]"
			result.append((record.id, name))
		return result
