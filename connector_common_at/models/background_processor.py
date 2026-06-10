"""
Independent Background Job Processor for Connector Common AT
Provides background job processing without external dependencies
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)


class BackgroundProcessor(models.Model):
    """
    Independent Background Job Processor
    Handles all background job processing without external dependencies
    """
    _name = 'connector.background.processor'
    _description = 'Background Job Processor'
    _rec_name = 'name'
    _order = 'priority desc, create_date'

    # Basic Information
    name = fields.Char(
        string='Job Name',
        required=True,
        help='Name of the background job'
    )
    
    job_type = fields.Selection([
        ('sync_products', 'Sync Products'),
        ('sync_orders', 'Sync Orders'),
        ('sync_customers', 'Sync Customers'),
        ('sync_inventory', 'Sync Inventory'),
        ('sync_payments', 'Sync Payments'),
        ('sync_all', 'Sync All'),
        ('webhook_process', 'Process Webhook'),
        ('data_cleanup', 'Data Cleanup'),
        ('connection_test', 'Test Connection'),
        ('bulk_operation', 'Bulk Operation'),
        ('custom_operation', 'Custom Operation')
    ], string='Job Type', required=True, index=True)
    
    # Job Data
    instance_id = fields.Many2one(
        'connector.instance',
        string='Connector Instance',
        required=True,
        ondelete='cascade',
        help='The connector instance this job belongs to'
    )
    
    platform_type = fields.Selection(
        related='instance_id.platform_type',
        string='Platform Type',
        store=True,
        readonly=True
    )
    
    # Job Parameters
    job_data = fields.Text(
        string='Job Data',
        help='JSON data for the job execution'
    )
    
    method_name = fields.Char(
        string='Method Name',
        required=True,
        help='Name of the method to execute'
    )
    
    args = fields.Text(
        string='Arguments',
        help='JSON arguments for the method'
    )
    
    kwargs = fields.Text(
        string='Keyword Arguments',
        help='JSON keyword arguments for the method'
    )
    
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
        help='Progress percentage of the job'
    )
    
    current_step = fields.Char(
        string='Current Step',
        help='Current step being executed'
    )
    
    total_steps = fields.Integer(
        string='Total Steps',
        default=1,
        help='Total number of steps in the job'
    )
    
    # Execution Details
    start_time = fields.Datetime(
        string='Start Time',
        help='When the job started executing'
    )
    
    end_time = fields.Datetime(
        string='End Time',
        help='When the job finished executing'
    )
    
    execution_time = fields.Float(
        string='Execution Time (seconds)',
        compute='_compute_execution_time',
        store=True,
        help='Total execution time in seconds'
    )
    
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        help='User who processed this job'
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
        help='Delay in minutes before retrying'
    )
    
    last_retry = fields.Datetime(
        string='Last Retry',
        help='When this job was last retried'
    )
    
    # Error Handling
    error_message = fields.Text(
        string='Error Message',
        help='Error message if the job failed'
    )
    
    error_traceback = fields.Text(
        string='Error Traceback',
        help='Full error traceback for debugging'
    )
    
    # Results
    result_data = fields.Text(
        string='Result Data',
        help='JSON result data from job execution'
    )
    
    records_processed = fields.Integer(
        string='Records Processed',
        default=0,
        help='Number of records processed'
    )
    
    records_success = fields.Integer(
        string='Records Success',
        default=0,
        help='Number of records processed successfully'
    )
    
    records_failed = fields.Integer(
        string='Records Failed',
        default=0,
        help='Number of records that failed processing'
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
        help='Success rate of the job'
    )
    
    # Constraints
    @api.constrains('max_retries', 'retry_delay')
    def _check_positive_values(self):
        """Ensure positive values for numeric fields"""
        for job in self:
            if job.max_retries < 0:
                raise ValidationError(_('Max retries cannot be negative'))
            if job.retry_delay < 0:
                raise ValidationError(_('Retry delay cannot be negative'))
    
    @api.constrains('progress')
    def _check_progress_range(self):
        """Ensure progress is between 0 and 100"""
        for job in self:
            if job.progress < 0 or job.progress > 100:
                raise ValidationError(_('Progress must be between 0 and 100'))
    
    # Computed Methods
    @api.depends('start_time', 'end_time')
    def _compute_execution_time(self):
        """Compute execution time from start and end times"""
        for job in self:
            if job.start_time and job.end_time:
                duration = (job.end_time - job.start_time).total_seconds()
                job.execution_time = duration
            else:
                job.execution_time = 0.0
    
    @api.depends('scheduled_date')
    def _compute_is_overdue(self):
        """Compute whether the job is overdue"""
        for job in self:
            if job.state == 'pending' and job.scheduled_date:
                job.is_overdue = fields.Datetime.now() > job.scheduled_date
            else:
                job.is_overdue = False
    
    @api.depends('state', 'retry_count', 'max_retries')
    def _compute_can_retry(self):
        """Compute whether the job can be retried"""
        for job in self:
            job.can_retry = (
                job.state in ['failed', 'retry'] and 
                job.retry_count < job.max_retries
            )
    
    @api.depends('records_processed', 'records_success')
    def _compute_success_rate(self):
        """Compute success rate percentage"""
        for job in self:
            if job.records_processed > 0:
                job.success_rate = (job.records_success / job.records_processed) * 100
            else:
                job.success_rate = 100.0 if job.state != 'failed' else 0.0
    
    # Actions
    def action_process(self):
        """Process this background job"""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending jobs can be processed'))

        error_to_raise = None
        try:
            self.state = 'running'
            self.start_time = fields.Datetime.now()
            self.processed_by = self.env.user
            self.env.cr.commit()  # Commit running state before execution

            # Log start
            self._log_job('info', f'Starting {self.job_type} job')

            # Execute the job
            result = self._execute_job()

            # Mark as done
            self.state = 'done'
            self.end_time = fields.Datetime.now()
            self.progress = 100.0
            self.result_data = str(result)

            # Log success
            self._log_job('info', f'Job completed successfully: {result}')
            self.env.cr.commit()

            return result

        except Exception as e:
            error_to_raise = e
            # Use savepoint so error state is committed even when we re-raise
            try:
                self.env.cr.rollback()
                self._handle_job_error(str(e))
                self.env.cr.commit()
            except Exception:
                pass  # Don't mask original error

        if error_to_raise:
            raise error_to_raise
    
    def action_retry(self):
        """Retry a failed job"""
        self.ensure_one()
        if not self.can_retry:
            raise UserError(_('This job cannot be retried'))
        
        # Calculate retry delay with exponential backoff
        delay_minutes = self.retry_delay * (2 ** self.retry_count)
        retry_time = fields.Datetime.now() + timedelta(minutes=delay_minutes)
        
        self.write({
            'state': 'retry',
            'retry_count': self.retry_count + 1,
            'last_retry': fields.Datetime.now(),
            'scheduled_date': retry_time,
            'error_message': False,
            'error_traceback': False,
        })
        
        self._log_job('info', f'Job scheduled for retry at {retry_time}')
        return True
    
    def action_cancel(self):
        """Cancel a pending job"""
        self.ensure_one()
        if self.state not in ['pending', 'retry']:
            raise UserError(_('Only pending or retry jobs can be cancelled'))
        
        self.state = 'cancelled'
        self._log_job('info', 'Job cancelled by user')
        return True
    
    # Job Execution
    def _execute_job(self):
        """Execute the background job"""
        self.ensure_one()
        
        try:
            # Get the method to execute
            method = getattr(self.instance_id, self.method_name, None)
            if not method:
                raise UserError(_('Method %s not found on instance') % self.method_name)
            
            # Parse arguments
            args = self._parse_json(self.args) or []
            kwargs = self._parse_json(self.kwargs) or {}
            
            # Execute method
            self.current_step = f'Executing {self.method_name}'
            self.progress = 50.0
            
            result = method(*args, **kwargs)
            
            self.progress = 100.0
            return result
            
        except Exception as e:
            self._handle_job_error(str(e))
            raise
    
    def _handle_job_error(self, error_message):
        """Handle job execution errors"""
        self.state = 'failed'
        self.end_time = fields.Datetime.now()
        self.error_message = error_message
        
        # Log error
        self._log_job('error', f'Job failed: {error_message}')
        
        # Check if should retry
        if self.retry_count < self.max_retries:
            self.state = 'retry'
            delay_minutes = self.retry_delay * (2 ** self.retry_count)
            self.scheduled_date = fields.Datetime.now() + timedelta(minutes=delay_minutes)
            self._log_job('info', f'Job scheduled for retry in {delay_minutes} minutes')
    
    # Utility Methods
    def _parse_json(self, json_string):
        """Parse JSON string safely"""
        if not json_string:
            return None
        
        try:
            import json
            return json.loads(json_string)
        except Exception:
            return None
    
    def _log_job(self, level, message, data=None):
        """Log job activity"""
        # Map job_type to connector.log operation field
        job_type_to_operation = {
            'sync_products': 'sync_products',
            'sync_orders': 'sync_orders',
            'sync_customers': 'sync_customers',
            'sync_inventory': 'sync_inventory',
            'sync_all': 'general',
            'connection_test': 'connection_test',
            'webhook': 'webhook_received',
            'api_call': 'api_call',
            'cleanup': 'cleanup',
        }
        operation = job_type_to_operation.get(self.job_type, 'general')
        log_data = {
            'instance_id': self.instance_id.id,
            'level': level,
            'message': message,
            'operation': operation,
        }

        if data:
            log_data['data'] = str(data)

        return self.env['connector.log'].create(log_data)
    
    def update_progress(self, progress, step=None):
        """Update progress and current step"""
        self.progress = progress
        if step:
            self.current_step = step
    
    # Class Methods
    @api.model
    def process_pending_jobs(self):
        """Process all pending background jobs"""
        pending_jobs = self.search([
            ('state', 'in', ['pending', 'retry']),
            ('scheduled_date', '<=', fields.Datetime.now())
        ], order='priority desc, create_date')
        
        processed_count = 0
        for job in pending_jobs:
            try:
                job.action_process()
                processed_count += 1
            except Exception as e:
                _logger.error(f'Error processing job {job.id}: {str(e)}')
                job._handle_job_error(str(e))
        
        return processed_count
    
    @api.model
    def cleanup_old_jobs(self, days=7):
        """Clean up old completed/failed jobs"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        
        old_jobs = self.search([
            ('state', 'in', ['done', 'failed', 'cancelled']),
            ('create_date', '<', cutoff_date)
        ])
        
        deleted_count = len(old_jobs)
        old_jobs.unlink()
        
        return deleted_count
    
    @api.model
    def get_job_statistics(self, instance_id=None):
        """Get job statistics"""
        domain = []
        if instance_id:
            domain.append(('instance_id', '=', instance_id))
        
        all_jobs = self.search(domain)
        
        stats = {
            'total': len(all_jobs),
            'pending': len(all_jobs.filtered(lambda j: j.state == 'pending')),
            'running': len(all_jobs.filtered(lambda j: j.state == 'running')),
            'done': len(all_jobs.filtered(lambda j: j.state == 'done')),
            'failed': len(all_jobs.filtered(lambda j: j.state == 'failed')),
            'retry': len(all_jobs.filtered(lambda j: j.state == 'retry')),
            'cancelled': len(all_jobs.filtered(lambda j: j.state == 'cancelled')),
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
        for job in self:
            # Clean up related logs
            job._log_job('info', 'Job deleted')
        
        return super().unlink()


class BackgroundJobScheduler(models.Model):
    """
    Background Job Scheduler
    Manages the scheduling and execution of background jobs
    """
    _name = 'connector.job.scheduler'
    _description = 'Background Job Scheduler'
    
    name = fields.Char(string='Scheduler Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    last_run = fields.Datetime(string='Last Run')
    next_run = fields.Datetime(string='Next Run')
    interval_minutes = fields.Integer(string='Interval (minutes)', default=5)
    
    @api.model
    def start_scheduler(self):
        """Start the background job scheduler"""
        if not config.get('workers'):
            # Single process mode - use cron
            return self._start_cron_scheduler()
        else:
            # Multi-process mode - start background thread
            return self._start_background_scheduler()
    
    def _start_cron_scheduler(self):
        """Start scheduler using Odoo cron system"""
        cron = self.env['ir.cron'].search([
            ('name', '=', 'Process Background Jobs'),
            ('model', '=', 'connector.background.processor')
        ])
        
        if not cron:
            cron = self.env['ir.cron'].create({
                'name': 'Process Background Jobs',
                'model_id': self.env['ir.model']._get('connector.background.processor').id,
                'state': 'code',
                'code': 'model.process_pending_jobs()',
                'interval_number': 1,
                'interval_type': 'minutes',
                'active': True,
            })
        
        return cron
    
    def _start_background_scheduler(self):
        """Start scheduler in background thread"""
        def scheduler_loop():
            while True:
                try:
                    # Process pending jobs
                    self.env['connector.background.processor'].process_pending_jobs()
                    
                    # Wait for next interval
                    time.sleep(self.interval_minutes * 60)
                    
                except Exception as e:
                    _logger.error(f'Scheduler error: {str(e)}')
                    time.sleep(60)  # Wait 1 minute on error
        
        # Start scheduler thread
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        
        return scheduler_thread
