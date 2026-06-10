from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ConnectorLog(models.Model):
    """
    Connector Log - Comprehensive logging system for all connector operations
    This model tracks all operations, errors, and performance metrics
    """
    _name = 'connector.log'
    _description = 'Connector Log'
    _order = 'create_date desc'
    _rec_name = 'message'

    # Basic Information
    instance_id = fields.Many2one(
        'connector.instance',
        string='Connector Instance',
        required=True,
        ondelete='cascade',
        help='The connector instance this log belongs to'
    )
    
    platform_type = fields.Selection(
        related='instance_id.platform_type',
        string='Platform Type',
        store=True,
        readonly=True
    )
    
    level = fields.Selection([
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical')
    ], string='Log Level', required=True, default='info', index=True)
    
    operation = fields.Selection([
        ('connection_test', 'Connection Test'),
        ('sync_products', 'Sync Products'),
        ('sync_orders', 'Sync Orders'),
        ('sync_customers', 'Sync Customers'),
        ('sync_inventory', 'Sync Inventory'),
        ('sync_payments', 'Sync Payments'),
        ('webhook_received', 'Webhook Received'),
        ('api_call', 'API Call'),
        ('data_transformation', 'Data Transformation'),
        ('error_handling', 'Error Handling'),
        ('queue_processing', 'Queue Processing'),
        ('general', 'General'),
        ('maintenance', 'Maintenance'),
        ('cleanup', 'Cleanup')
    ], string='Operation', required=True, default='general', index=True)
    
    message = fields.Text(
        string='Message',
        required=True,
        help='Detailed log message'
    )
    
    # Performance Metrics
    execution_time = fields.Float(
        string='Execution Time (seconds)',
        help='Time taken to execute the operation'
    )
    
    memory_usage = fields.Float(
        string='Memory Usage (MB)',
        help='Memory used during operation'
    )
    
    records_processed = fields.Integer(
        string='Records Processed',
        default=0,
        help='Number of records processed in this operation'
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
    
    # Error Details
    error_code = fields.Char(
        string='Error Code',
        help='Specific error code if applicable'
    )
    
    error_type = fields.Char(
        string='Error Type',
        help='Type of error (e.g., APIError, ValidationError)'
    )
    
    stack_trace = fields.Text(
        string='Stack Trace',
        help='Full stack trace for errors'
    )
    
    # Additional Data
    data = fields.Text(
        string='Additional Data',
        help='JSON data related to this log entry'
    )
    
    request_data = fields.Text(
        string='Request Data',
        help='Request data sent to external API'
    )
    
    response_data = fields.Text(
        string='Response Data',
        help='Response data received from external API'
    )
    
    # User and Context
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        help='User who triggered this operation'
    )
    
    session_id = fields.Char(
        string='Session ID',
        help='Web session ID for web-based operations'
    )
    
    ip_address = fields.Char(
        string='IP Address',
        help='IP address of the request'
    )
    
    user_agent = fields.Char(
        string='User Agent',
        help='User agent string'
    )
    
    # Timestamps
    create_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True,
        index=True
    )
    
    start_time = fields.Datetime(
        string='Start Time',
        help='When the operation started'
    )
    
    end_time = fields.Datetime(
        string='End Time',
        help='When the operation ended'
    )
    
    # Computed Fields
    duration = fields.Float(
        string='Duration (seconds)',
        compute='_compute_duration',
        store=True,
        help='Duration of the operation'
    )
    
    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_success_rate',
        store=True,
        help='Success rate of the operation'
    )
    
    is_error = fields.Boolean(
        string='Is Error',
        compute='_compute_is_error',
        store=True,
        help='Whether this log represents an error'
    )
    
    # Related Records
    queue_id = fields.Many2one(
        'connector.queue',
        string='Queue Item',
        help='Related queue item if this log is from queue processing'
    )
    
    parent_log_id = fields.Many2one(
        'connector.log',
        string='Parent Log',
        help='Parent log entry for hierarchical logging'
    )
    
    child_log_ids = fields.One2many(
        'connector.log',
        'parent_log_id',
        string='Child Logs',
        help='Child log entries'
    )
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """Compute duration from start and end times"""
        for log in self:
            if log.start_time and log.end_time:
                duration = (log.end_time - log.start_time).total_seconds()
                log.duration = duration
            else:
                log.duration = 0.0
    
    @api.depends('records_processed', 'records_success')
    def _compute_success_rate(self):
        """Compute success rate percentage"""
        for log in self:
            if log.records_processed > 0:
                log.success_rate = (log.records_success / log.records_processed) * 100
            else:
                log.success_rate = 100.0 if log.level != 'error' else 0.0
    
    @api.depends('level')
    def _compute_is_error(self):
        """Compute whether this log represents an error"""
        for log in self:
            log.is_error = log.level in ['error', 'critical']
    
    # Actions
    def action_view_details(self):
        """Open detailed view of this log entry"""
        self.ensure_one()
        return {
            'name': _('Log Details'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.log',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_view_children(self):
        """View child log entries"""
        self.ensure_one()
        return {
            'name': _('Child Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.log',
            'view_mode': 'tree,form',
            'domain': [('parent_log_id', '=', self.id)],
            'context': {'default_parent_log_id': self.id},
        }
    
    def action_retry_operation(self):
        """Retry the operation that generated this log"""
        self.ensure_one()
        if self.operation and self.operation != 'general':
            # Create a new queue item to retry the operation
            self.env['connector.queue'].create({
                'instance_id': self.instance_id.id,
                'operation': self.operation,
                'priority': 'high',
                'data': self.data or '{}',
                'retry_count': 0,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Retry Queued'),
                    'message': _('Operation has been queued for retry.'),
                    'type': 'info',
                }
            }
    
    def action_export_logs(self):
        """Export logs to CSV/Excel"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/export/xlsx?model=connector.log&ids={self.id}',
            'target': 'self',
        }
    
    # Utility Methods
    def log_api_call(self, method, endpoint, request_data=None, response_data=None, 
                    execution_time=None, success=True, error_message=None):
        """Log an API call with detailed information"""
        log_data = {
            'instance_id': self.instance_id.id,
            'operation': 'api_call',
            'level': 'error' if not success else 'info',
            'message': f'API {method} {endpoint} - {"Success" if success else "Failed"}',
            'execution_time': execution_time,
            'request_data': json.dumps(request_data) if request_data else None,
            'response_data': json.dumps(response_data) if response_data else None,
        }
        
        if error_message:
            log_data['message'] += f': {error_message}'
        
        return self.env['connector.log'].create(log_data)
    
    def log_sync_operation(self, operation_type, records_processed, records_success, 
                          records_failed, execution_time=None, error_message=None):
        """Log a synchronization operation"""
        success_rate = (records_success / records_processed * 100) if records_processed > 0 else 100
        
        log_data = {
            'instance_id': self.instance_id.id,
            'operation': f'sync_{operation_type}',
            'level': 'error' if records_failed > 0 else 'info',
            'message': f'Sync {operation_type}: {records_success}/{records_processed} successful',
            'execution_time': execution_time,
            'records_processed': records_processed,
            'records_success': records_success,
            'records_failed': records_failed,
        }
        
        if error_message:
            log_data['message'] += f' - Error: {error_message}'
        
        return self.env['connector.log'].create(log_data)
    
    def log_error(self, error, operation='general', data=None):
        """Log an error with full details"""
        import traceback
        
        log_data = {
            'instance_id': self.instance_id.id,
            'operation': operation,
            'level': 'error',
            'message': str(error),
            'error_type': type(error).__name__,
            'stack_trace': traceback.format_exc(),
            'data': json.dumps(data) if data else None,
        }
        
        return self.env['connector.log'].create(log_data)
    
    def log_warning(self, message, operation='general', data=None):
        """Log a warning message"""
        log_data = {
            'instance_id': self.instance_id.id,
            'operation': operation,
            'level': 'warning',
            'message': message,
            'data': json.dumps(data) if data else None,
        }
        
        return self.env['connector.log'].create(log_data)
    
    def log_info(self, message, operation='general', data=None):
        """Log an info message"""
        log_data = {
            'instance_id': self.instance_id.id,
            'operation': operation,
            'level': 'info',
            'message': message,
            'data': json.dumps(data) if data else None,
        }
        
        return self.env['connector.log'].create(log_data)
    
    def log_debug(self, message, operation='general', data=None):
        """Log a debug message"""
        log_data = {
            'instance_id': self.instance_id.id,
            'operation': operation,
            'level': 'debug',
            'message': message,
            'data': json.dumps(data) if data else None,
        }
        
        return self.env['connector.log'].create(log_data)
    
    # Class Methods
    @api.model
    def cleanup_old_logs(self, days=30, keep_levels=None):
        """Clean up old log entries"""
        if keep_levels is None:
            keep_levels = ['error', 'critical']
        
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        
        # Keep important logs longer
        old_logs = self.search([
            ('create_date', '<', cutoff_date),
            ('level', 'not in', keep_levels)
        ])
        
        deleted_count = len(old_logs)
        old_logs.unlink()
        
        # Log the cleanup operation
        self.env['connector.log'].create({
            'instance_id': False,
            'operation': 'cleanup',
            'level': 'info',
            'message': f'Cleaned up {deleted_count} old log entries older than {days} days',
        })
        
        return deleted_count
    
    @api.model
    def get_error_summary(self, instance_id=None, days=7):
        """Get summary of errors for the specified period"""
        domain = [
            ('level', 'in', ['error', 'critical']),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=days))
        ]
        
        if instance_id:
            domain.append(('instance_id', '=', instance_id))
        
        errors = self.search(domain)
        
        summary = {
            'total_errors': len(errors),
            'by_operation': {},
            'by_level': {},
            'recent_errors': []
        }
        
        for error in errors:
            # Count by operation
            op = error.operation
            summary['by_operation'][op] = summary['by_operation'].get(op, 0) + 1
            
            # Count by level
            level = error.level
            summary['by_level'][level] = summary['by_level'].get(level, 0) + 1
            
            # Recent errors
            if len(summary['recent_errors']) < 10:
                summary['recent_errors'].append({
                    'id': error.id,
                    'message': error.message,
                    'operation': error.operation,
                    'create_date': error.create_date,
                    'instance': error.instance_id.name
                })
        
        return summary
    
    @api.model
    def get_performance_metrics(self, instance_id=None, days=7):
        """Get performance metrics for the specified period"""
        domain = [
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=days)),
            ('execution_time', '>', 0)
        ]
        
        if instance_id:
            domain.append(('instance_id', '=', instance_id))
        
        logs = self.search(domain)
        
        if not logs:
            return {}
        
        metrics = {
            'total_operations': len(logs),
            'avg_execution_time': sum(logs.mapped('execution_time')) / len(logs),
            'max_execution_time': max(logs.mapped('execution_time')),
            'min_execution_time': min(logs.mapped('execution_time')),
            'total_records_processed': sum(logs.mapped('records_processed')),
            'total_records_success': sum(logs.mapped('records_success')),
            'total_records_failed': sum(logs.mapped('records_failed')),
            'avg_success_rate': sum(logs.mapped('success_rate')) / len(logs),
        }
        
        return metrics
    
    # CRUD Overrides
    def create(self, vals):
        """Override create to add additional context"""
        # Add user context if not provided
        if 'user_id' not in vals:
            vals['user_id'] = self.env.user.id
        
        # Add start time if operation is starting
        if 'start_time' not in vals and vals.get('operation') != 'general':
            vals['start_time'] = fields.Datetime.now()
        
        return super().create(vals)
    
    def write(self, vals):
        """Override write to handle end time"""
        # Add end time if operation is completing
        if 'end_time' not in vals and self.filtered(lambda l: l.start_time and not l.end_time):
            vals['end_time'] = fields.Datetime.now()
        
        return super().write(vals) 