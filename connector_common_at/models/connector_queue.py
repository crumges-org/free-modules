from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ConnectorQueue(models.Model):
    """
    Connector Queue - Background job management for connector operations
    This model manages queued operations, retries, and job processing
    """
    _name = 'connector.queue'
    _description = 'Connector Queue'
    _order = 'priority desc, create_date'
    _rec_name = 'operation'

    # Basic Information
    instance_id = fields.Many2one(
        'connector.instance',
        string='Connector Instance',
        required=True,
        ondelete='cascade',
        help='The connector instance this queue item belongs to'
    )
    
    platform_type = fields.Selection(
        related='instance_id.platform_type',
        string='Platform Type',
        store=True,
        readonly=True
    )
    
    operation = fields.Selection([
        ('sync_products', 'Sync Products'),
        ('sync_orders', 'Sync Orders'),
        ('sync_customers', 'Sync Customers'),
        ('sync_inventory', 'Sync Inventory'),
        ('sync_payments', 'Sync Payments'),
        ('sync_all', 'Sync All'),
        ('import_products', 'Import Products'),
        ('export_products', 'Export Products'),
        ('import_orders', 'Import Orders'),
        ('export_orders', 'Export Orders'),
        ('webhook_process', 'Process Webhook'),
        ('data_cleanup', 'Data Cleanup'),
        ('connection_test', 'Test Connection'),
        ('bulk_operation', 'Bulk Operation'),
        ('custom_operation', 'Custom Operation')
    ], string='Operation', required=True, index=True)
    
    # Priority and Scheduling
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], string='Priority', default='normal', required=True, index=True)
    
    scheduled_date = fields.Datetime(
        string='Scheduled Date',
        default=fields.Datetime.now,
        required=True,
        index=True,
        help='When this job should be executed'
    )
    
    # State Management
    state = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('retry', 'Retry')
    ], string='State', default='pending', required=True, index=True)
    
    # Progress Tracking
    progress = fields.Float(
        string='Progress (%)',
        default=0.0,
        help='Progress percentage of the operation'
    )
    
    current_step = fields.Char(
        string='Current Step',
        help='Current step being executed'
    )
    
    total_steps = fields.Integer(
        string='Total Steps',
        default=1,
        help='Total number of steps in the operation'
    )
    
    # Retry Management
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        help='Number of times this job has been retried'
    )
    
    max_retries = fields.Integer(
        string='Max Retries',
        default=3,
        help='Maximum number of retry attempts'
    )
    
    retry_delay = fields.Integer(
        string='Retry Delay (minutes)',
        default=5,
        help='Delay between retry attempts in minutes'
    )
    
    last_retry_date = fields.Datetime(
        string='Last Retry Date',
        help='When this job was last retried'
    )
    
    # Data and Parameters
    data = fields.Text(
        string='Operation Data',
        help='JSON data for the operation parameters'
    )
    
    result_data = fields.Text(
        string='Result Data',
        help='JSON data with operation results'
    )
    
    error_message = fields.Text(
        string='Error Message',
        help='Error message if the operation failed'
    )
    
    # Performance Metrics
    start_time = fields.Datetime(
        string='Start Time',
        help='When the operation started'
    )
    
    end_time = fields.Datetime(
        string='End Time',
        help='When the operation ended'
    )
    
    execution_time = fields.Float(
        string='Execution Time (seconds)',
        compute='_compute_execution_time',
        store=True,
        help='Total execution time'
    )
    
    # Records Processed
    records_processed = fields.Integer(
        string='Records Processed',
        default=0,
        help='Number of records processed'
    )
    
    records_success = fields.Integer(
        string='Records Success',
        default=0,
        help='Number of records successfully processed'
    )
    
    records_failed = fields.Integer(
        string='Records Failed',
        default=0,
        help='Number of records that failed processing'
    )
    
    # User and Context
    user_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        help='User who created this queue item'
    )
    
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        help='User or system that processed this item'
    )
    
    # Related Records
    log_ids = fields.One2many(
        'connector.log',
        'queue_id',
        string='Logs',
        help='Log entries related to this queue item'
    )
    
    parent_queue_id = fields.Many2one(
        'connector.queue',
        string='Parent Queue Item',
        help='Parent queue item for hierarchical operations'
    )
    
    child_queue_ids = fields.One2many(
        'connector.queue',
        'parent_queue_id',
        string='Child Queue Items',
        help='Child queue items'
    )
    
    # Computed Fields
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        store=True,
        help='Whether this job is overdue for execution'
    )
    
    can_retry = fields.Boolean(
        string='Can Retry',
        compute='_compute_can_retry',
        store=True,
        help='Whether this job can be retried'
    )
    
    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_success_rate',
        store=True,
        help='Success rate of the operation'
    )
    
    @api.depends('start_time', 'end_time')
    def _compute_execution_time(self):
        """Compute execution time from start and end times"""
        for item in self:
            if item.start_time and item.end_time:
                duration = (item.end_time - item.start_time).total_seconds()
                item.execution_time = duration
            else:
                item.execution_time = 0.0
    
    @api.depends('scheduled_date')
    def _compute_is_overdue(self):
        """Compute whether the job is overdue"""
        for item in self:
            if item.state == 'pending' and item.scheduled_date:
                item.is_overdue = fields.Datetime.now() > item.scheduled_date
            else:
                item.is_overdue = False
    
    @api.depends('state', 'retry_count', 'max_retries')
    def _compute_can_retry(self):
        """Compute whether the job can be retried"""
        for item in self:
            item.can_retry = (
                item.state in ['failed', 'retry'] and 
                item.retry_count < item.max_retries
            )
    
    @api.depends('records_processed', 'records_success')
    def _compute_success_rate(self):
        """Compute success rate percentage"""
        for item in self:
            if item.records_processed > 0:
                item.success_rate = (item.records_success / item.records_processed) * 100
            else:
                item.success_rate = 100.0 if item.state != 'failed' else 0.0
    
    # Constraints
    @api.constrains('max_retries', 'retry_delay')
    def _check_positive_values(self):
        """Ensure positive values for numeric fields"""
        for item in self:
            if item.max_retries < 0:
                raise ValidationError(_('Max retries cannot be negative'))
            if item.retry_delay < 0:
                raise ValidationError(_('Retry delay cannot be negative'))
    
    @api.constrains('progress')
    def _check_progress_range(self):
        """Ensure progress is between 0 and 100"""
        for item in self:
            if item.progress < 0 or item.progress > 100:
                raise ValidationError(_('Progress must be between 0 and 100'))
    
    # Actions
    def action_process(self):
        """Process this queue item"""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending items can be processed'))
        
        try:
            self.state = 'running'
            self.start_time = fields.Datetime.now()
            self.processed_by = self.env.user
            
            # Log start
            self.log_operation('info', f'Starting {self.operation} operation')
            
            # Process the operation
            result = self._process_operation()
            
            # Mark as done
            self.state = 'done'
            self.end_time = fields.Datetime.now()
            self.progress = 100.0
            self.result_data = json.dumps(result)
            
            # Log success
            self.log_operation('info', f'Completed {self.operation} operation successfully')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Operation completed successfully.'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            self._handle_error(str(e))
            raise UserError(_('Operation failed: %s') % str(e))
    
    def action_retry(self):
        """Retry this queue item"""
        self.ensure_one()
        if not self.can_retry:
            raise UserError(_('This item cannot be retried'))
        
        self.retry_count += 1
        self.last_retry_date = fields.Datetime.now()
        self.state = 'pending'
        self.scheduled_date = fields.Datetime.now() + timedelta(minutes=self.retry_delay)
        self.error_message = None
        self.progress = 0.0
        self.current_step = None
        
        # Log retry
        self.log_operation('info', f'Retrying {self.operation} operation (attempt {self.retry_count})')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Retry Scheduled'),
                'message': _('Operation has been scheduled for retry.'),
                'type': 'info',
            }
        }
    
    def action_cancel(self):
        """Cancel this queue item"""
        self.ensure_one()
        if self.state not in ['pending', 'retry']:
            raise UserError(_('Only pending or retry items can be cancelled'))
        
        self.state = 'cancelled'
        self.end_time = fields.Datetime.now()
        
        # Log cancellation
        self.log_operation('warning', f'Cancelled {self.operation} operation')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cancelled'),
                'message': _('Operation has been cancelled.'),
                'type': 'warning',
            }
        }
    
    def action_view_logs(self):
        """View logs for this queue item"""
        self.ensure_one()
        return {
            'name': _('Queue Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.log',
            'view_mode': 'tree,form',
            'domain': [('queue_id', '=', self.id)],
            'context': {'default_queue_id': self.id},
        }
    
    def action_view_children(self):
        """View child queue items"""
        self.ensure_one()
        return {
            'name': _('Child Queue Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.queue',
            'view_mode': 'tree,form',
            'domain': [('parent_queue_id', '=', self.id)],
            'context': {'default_parent_queue_id': self.id},
        }
    
    # Processing Methods
    def _process_operation(self):
        """Process the specific operation
        This method should be overridden by platform-specific modules
        """
        operation_map = {
            'sync_products': self._sync_products,
            'sync_orders': self._sync_orders,
            'sync_customers': self._sync_customers,
            'sync_inventory': self._sync_inventory,
            'sync_payments': self._sync_payments,
            'sync_all': self._sync_all,
            'connection_test': self._test_connection,
            'webhook_process': self._process_webhook,
            'data_cleanup': self._cleanup_data,
        }
        
        operation_method = operation_map.get(self.operation)
        if operation_method:
            return operation_method()
        else:
            raise NotImplementedError(_('Operation %s not implemented') % self.operation)
    
    def _sync_products(self):
        """Sync products operation"""
        self.current_step = 'Starting product sync'
        self.progress = 10.0
        
        # This should be implemented by platform-specific modules
        raise NotImplementedError(_('Product sync not implemented for this platform'))
    
    def _sync_orders(self):
        """Sync orders operation"""
        self.current_step = 'Starting order sync'
        self.progress = 10.0
        
        # This should be implemented by platform-specific modules
        raise NotImplementedError(_('Order sync not implemented for this platform'))
    
    def _sync_customers(self):
        """Sync customers operation"""
        self.current_step = 'Starting customer sync'
        self.progress = 10.0
        
        # This should be implemented by platform-specific modules
        raise NotImplementedError(_('Customer sync not implemented for this platform'))
    
    def _sync_inventory(self):
        """Sync inventory operation"""
        self.current_step = 'Starting inventory sync'
        self.progress = 10.0
        
        # This should be implemented by platform-specific modules
        raise NotImplementedError(_('Inventory sync not implemented for this platform'))
    
    def _sync_payments(self):
        """Sync payments operation"""
        self.current_step = 'Starting payment sync'
        self.progress = 10.0
        
        # This should be implemented by platform-specific modules
        raise NotImplementedError(_('Payment sync not implemented for this platform'))
    
    def _sync_all(self):
        """Sync all data operation"""
        self.current_step = 'Starting full sync'
        self.progress = 5.0
        
        # Create child queue items for each sync operation
        operations = ['sync_products', 'sync_orders', 'sync_customers', 'sync_inventory']
        
        for i, operation in enumerate(operations):
            self.env['connector.queue'].create({
                'instance_id': self.instance_id.id,
                'operation': operation,
                'priority': self.priority,
                'parent_queue_id': self.id,
                'data': self.data,
            })
            self.progress = 5.0 + (i + 1) * 20.0
        
        return {'message': 'Full sync queued successfully'}
    
    def _test_connection(self):
        """Test connection operation"""
        self.current_step = 'Testing connection'
        self.progress = 50.0
        
        # Test connection using instance method
        result = self.instance_id.action_test_connection()
        
        self.progress = 100.0
        return {'message': 'Connection test completed'}
    
    def _process_webhook(self):
        """Process webhook operation"""
        self.current_step = 'Processing webhook'
        self.progress = 50.0
        
        # Parse webhook data
        webhook_data = json.loads(self.data) if self.data else {}
        
        # This should be implemented by platform-specific modules
        raise NotImplementedError(_('Webhook processing not implemented for this platform'))
    
    def _cleanup_data(self):
        """Cleanup data operation"""
        self.current_step = 'Cleaning up data'
        self.progress = 50.0
        
        # Clean up old logs
        deleted_count = self.env['connector.log'].cleanup_old_logs()
        
        self.progress = 100.0
        return {'message': f'Cleaned up {deleted_count} old log entries'}
    
    def _handle_error(self, error_message):
        """Handle operation errors"""
        self.state = 'failed'
        self.end_time = fields.Datetime.now()
        self.error_message = error_message
        
        # Log error
        self.log_operation('error', f'Operation failed: {error_message}')
        
        # Check if should retry
        if self.retry_count < self.max_retries:
            self.state = 'retry'
            self.scheduled_date = fields.Datetime.now() + timedelta(minutes=self.retry_delay)
    
    def log_operation(self, level, message, data=None):
        """Log an operation for this queue item"""
        log_data = {
            'instance_id': self.instance_id.id,
            'queue_id': self.id,
            'level': level,
            'message': message,
            'operation': self.operation,
        }
        
        if data:
            log_data['data'] = json.dumps(data)
        
        return self.env['connector.log'].create(log_data)
    
    def update_progress(self, progress, step=None):
        """Update progress and current step"""
        self.progress = progress
        if step:
            self.current_step = step
    
    # Class Methods
    @api.model
    def process_pending_queue(self):
        """Process all pending queue items"""
        pending_items = self.search([
            ('state', 'in', ['pending', 'retry']),
            ('scheduled_date', '<=', fields.Datetime.now())
        ], order='priority desc, create_date')
        
        processed_count = 0
        for item in pending_items:
            try:
                item.action_process()
                processed_count += 1
            except Exception as e:
                _logger.error(f'Error processing queue item {item.id}: {str(e)}')
                item._handle_error(str(e))
        
        return processed_count
    
    @api.model
    def cleanup_failed_queue(self, days=7):
        """Clean up old failed queue items"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        
        failed_items = self.search([
            ('state', 'in', ['failed', 'cancelled']),
            ('create_date', '<', cutoff_date)
        ])
        
        deleted_count = len(failed_items)
        failed_items.unlink()
        
        return deleted_count
    
    @api.model
    def get_queue_statistics(self, instance_id=None):
        """Get queue statistics"""
        domain = []
        if instance_id:
            domain.append(('instance_id', '=', instance_id))
        
        all_items = self.search(domain)
        
        stats = {
            'total': len(all_items),
            'pending': len(all_items.filtered(lambda i: i.state == 'pending')),
            'running': len(all_items.filtered(lambda i: i.state == 'running')),
            'done': len(all_items.filtered(lambda i: i.state == 'done')),
            'failed': len(all_items.filtered(lambda i: i.state == 'failed')),
            'retry': len(all_items.filtered(lambda i: i.state == 'retry')),
            'cancelled': len(all_items.filtered(lambda i: i.state == 'cancelled')),
        }
        
        return stats
    
    # CRUD Overrides
    def create(self, vals):
        """Override create to add validation"""
        # Set default scheduled date if not provided
        if 'scheduled_date' not in vals:
            vals['scheduled_date'] = fields.Datetime.now()
        
        return super().create(vals)
    
    def unlink(self):
        """Override unlink to clean up related data"""
        for item in self:
            # Clean up related logs
            item.log_ids.unlink()
            # Clean up child items
            item.child_queue_ids.unlink()
        
        return super().unlink() 

    def _schedule_background_job(self, operation, priority='normal', scheduled_date=None, **kwargs):
        """Schedule a background job using the independent processor"""
        if not scheduled_date:
            scheduled_date = fields.Datetime.now()
        
        # Create background job
        job_data = {
            'name': f'{operation} for {self.instance_id.name}',
            'job_type': operation,
            'instance_id': self.instance_id.id,
            'priority': priority,
            'scheduled_date': scheduled_date,
            'method_name': f'_execute_{operation}',
            'args': json.dumps(kwargs.get('args', [])),
            'kwargs': json.dumps(kwargs.get('kwargs', {})),
        }
        
        background_job = self.env['connector.background.processor'].create(job_data)
        
        # Log job creation
        self.log_operation('info', f'Background job scheduled: {operation}', {
            'job_id': background_job.id,
            'scheduled_date': scheduled_date,
            'priority': priority
        })
        
        return background_job 