from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import json
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ConnectorInstance(models.Model):
    """
    Generic Connector Instance - Base model for all platform connectors
    This model provides common functionality for managing connections to
    various eCommerce platforms (Shopify, WooCommerce, Magento, etc.)
    """
    _name = 'connector.instance'
    _description = 'Connector Instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # Basic Information
    name = fields.Char(
        string='Instance Name',
        required=True,
        tracking=True,
        help='Name to identify this connector instance'
    )
    
    platform_type = fields.Selection([
        ('shopify', 'Shopify'),
        ('woocommerce', 'WooCommerce'),
        ('magento', 'Magento'),
        ('prestashop', 'PrestaShop'),
        ('bigcommerce', 'BigCommerce'),
        ('custom', 'Custom Platform')
    ], string='Platform Type', required=True, tracking=True)
    
    description = fields.Text(
        string='Description',
        help='Additional description for this connector instance'
    )

    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
        help='User responsible for this connector instance (used for access rules)'
    )
    
    # Connection Settings
    api_url = fields.Char(
        string='API URL',
        required=True,
        tracking=True,
        help='Base URL for the platform API'
    )
    
    api_key = fields.Char(
        string='API Key',
        required=True,
        tracking=True,
        help='API key for authentication'
    )
    
    api_secret = fields.Char(
        string='API Secret',
        tracking=True,
        help='API secret for enhanced security'
    )
    
    access_token = fields.Char(
        string='Access Token',
        tracking=True,
        help='OAuth access token if required'
    )
    
    # Status and Configuration
    is_active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Enable or disable this connector instance'
    )
    
    is_test_mode = fields.Boolean(
        string='Test Mode',
        default=False,
        tracking=True,
        help='Run in test mode to avoid affecting production data'
    )
    
    sync_enabled = fields.Boolean(
        string='Enable Sync',
        default=True,
        tracking=True,
        help='Enable automatic synchronization'
    )
    
    # Performance Settings
    batch_size = fields.Integer(
        string='Batch Size',
        default=100,
        tracking=True,
        help='Number of records to process in each batch'
    )
    
    sync_interval = fields.Integer(
        string='Sync Interval (minutes)',
        default=30,
        tracking=True,
        help='Interval between automatic syncs in minutes'
    )
    
    retry_attempts = fields.Integer(
        string='Retry Attempts',
        default=3,
        tracking=True,
        help='Number of retry attempts for failed operations'
    )
    
    # Timestamps
    last_sync_date = fields.Datetime(
        string='Last Sync',
        tracking=True,
        help='Last successful synchronization date'
    )
    
    last_connection_test = fields.Datetime(
        string='Last Connection Test',
        tracking=True,
        help='Last successful connection test'
    )
    
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True
    )
    
    # Related Records
    log_ids = fields.One2many(
        'connector.log',
        'instance_id',
        string='Logs',
        help='Connection and sync logs'
    )
    
    queue_ids = fields.One2many(
        'connector.queue',
        'instance_id',
        string='Queue Items',
        help='Pending operations in queue'
    )
    
    mapping_ids = fields.One2many(
        'connector.mapping',
        'instance_id',
        string='Field Mappings',
        help='Field mappings for data transformation'
    )
    
    config_ids = fields.One2many(
        'connector.config',
        'instance_id',
        string='Configurations',
        help='Platform-specific configurations'
    )
    
    # Statistics
    total_products_synced = fields.Integer(
        string='Products Synced',
        default=0,
        help='Total number of products synchronized'
    )
    
    total_orders_synced = fields.Integer(
        string='Orders Synced',
        default=0,
        help='Total number of orders synchronized'
    )
    
    total_customers_synced = fields.Integer(
        string='Customers Synced',
        default=0,
        help='Total number of customers synchronized'
    )
    
    sync_success_rate = fields.Float(
        string='Success Rate (%)',
        default=100.0,
        help='Percentage of successful sync operations'
    )
    
    # Computed Fields
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
        ('syncing', 'Syncing'),
        ('maintenance', 'Maintenance')
    ], string='Status', compute='_compute_status', store=True)
    
    connection_status = fields.Selection([
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Connection Error'),
        ('testing', 'Testing')
    ], string='Connection Status', compute='_compute_connection_status', store=True)
    
    @api.depends('is_active', 'last_sync_date', 'log_ids')
    def _compute_status(self):
        """Compute the overall status of the connector instance"""
        for instance in self:
            if not instance.is_active:
                instance.status = 'inactive'
            elif instance.log_ids and instance.log_ids[0].level == 'error':
                instance.status = 'error'
            elif instance.log_ids and 'syncing' in instance.log_ids[0].message:
                instance.status = 'syncing'
            else:
                instance.status = 'active'
    
    @api.depends('last_connection_test', 'log_ids')
    def _compute_connection_status(self):
        """Compute the connection status"""
        for instance in self:
            if not instance.last_connection_test:
                instance.connection_status = 'disconnected'
            elif instance.log_ids and 'connection error' in instance.log_ids[0].message.lower():
                instance.connection_status = 'error'
            else:
                instance.connection_status = 'connected'
    
    # Constraints
    @api.constrains('api_url')
    def _check_api_url(self):
        """Validate API URL format"""
        for instance in self:
            if instance.api_url and not instance.api_url.startswith(('http://', 'https://')):
                raise ValidationError(_('API URL must start with http:// or https://'))
    
    @api.constrains('batch_size', 'sync_interval', 'retry_attempts')
    def _check_positive_values(self):
        """Ensure positive values for numeric fields"""
        for instance in self:
            if instance.batch_size <= 0:
                raise ValidationError(_('Batch size must be greater than 0'))
            if instance.sync_interval <= 0:
                raise ValidationError(_('Sync interval must be greater than 0'))
            if instance.retry_attempts < 0:
                raise ValidationError(_('Retry attempts cannot be negative'))
    
    # Actions
    def action_test_connection(self):
        """Test the connection to the platform"""
        self.ensure_one()
        try:
            # Update connection status
            self.connection_status = 'testing'
            
            # Get platform-specific client
            client = self.get_platform_client()
            
            # Test connection
            result = client.test_connection()
            
            if result.get('success'):
                self.last_connection_test = fields.Datetime.now()
                self.connection_status = 'connected'
                
                # Log success
                self.env['connector.log'].create({
                    'instance_id': self.id,
                    'level': 'info',
                    'message': f'Connection test successful: {result.get("message", "")}',
                    'operation': 'connection_test'
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Connection test successful!'),
                        'type': 'success',
                    }
                }
            else:
                raise Exception(result.get('message', 'Unknown error'))
                
        except Exception as e:
            self.connection_status = 'error'
            
            # Log error
            self.env['connector.log'].create({
                'instance_id': self.id,
                'level': 'error',
                'message': f'Connection test failed: {str(e)}',
                'operation': 'connection_test'
            })
            
            raise UserError(_('Connection test failed: %s') % str(e))
    
    def action_sync_now(self):
        """Trigger immediate synchronization"""
        self.ensure_one()
        if not self.is_active:
            raise UserError(_('Cannot sync inactive connector instance'))
        
        # Create sync job
        self.env['connector.queue'].create({
            'instance_id': self.id,
            'operation': 'sync_all',
            'priority': 'high',
            'data': json.dumps({
                'sync_type': 'manual',
                'user_id': self.env.user.id
            })
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Started'),
                'message': _('Synchronization has been queued for processing.'),
                'type': 'info',
            }
        }
    
    def action_view_logs(self):
        """Open logs view for this instance"""
        self.ensure_one()
        return {
            'name': _('Connector Logs'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.log',
            'view_mode': 'tree,form',
            'domain': [('instance_id', '=', self.id)],
            'context': {'default_instance_id': self.id},
        }
    
    def action_view_queue(self):
        """Open queue view for this instance"""
        self.ensure_one()
        return {
            'name': _('Connector Queue'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.queue',
            'view_mode': 'tree,form',
            'domain': [('instance_id', '=', self.id)],
            'context': {'default_instance_id': self.id},
        }
    
    def action_reset_statistics(self):
        """Reset sync statistics"""
        self.ensure_one()
        self.write({
            'total_products_synced': 0,
            'total_orders_synced': 0,
            'total_customers_synced': 0,
            'sync_success_rate': 100.0,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Statistics Reset'),
                'message': _('Sync statistics have been reset.'),
                'type': 'success',
            }
        }
    
    # Platform-specific methods (to be overridden by child classes)
    def get_platform_client(self):
        """Get platform-specific API client
        This method should be overridden by platform-specific modules
        """
        raise NotImplementedError(_('Platform client not implemented for %s') % self.platform_type)
    
    def get_supported_operations(self):
        """Get list of supported operations for this platform
        This method should be overridden by platform-specific modules
        """
        return ['test_connection']
    
    def validate_credentials(self):
        """Validate platform-specific credentials
        This method should be overridden by platform-specific modules
        """
        return True
    
    # Utility methods
    def log_operation(self, level, message, operation='general', data=None):
        """Log an operation for this instance"""
        log_data = {
            'instance_id': self.id,
            'level': level,
            'message': message,
            'operation': operation,
        }
        
        if data:
            log_data['data'] = json.dumps(data)
        
        return self.env['connector.log'].create(log_data)
    
    def update_sync_statistics(self, operation_type, count=1, success=True):
        """Update sync statistics"""
        if operation_type == 'product':
            self.total_products_synced += count
        elif operation_type == 'order':
            self.total_orders_synced += count
        elif operation_type == 'customer':
            self.total_customers_synced += count
        
        # Update success rate (simplified calculation)
        if not success:
            # Decrease success rate by 1% for each failure
            self.sync_success_rate = max(0.0, self.sync_success_rate - 1.0)
    
    @api.model
    def get_instances_by_platform(self, platform_type):
        """Get all active instances for a specific platform"""
        return self.search([
            ('platform_type', '=', platform_type),
            ('is_active', '=', True)
        ])
    
    @api.model
    def cleanup_old_logs(self, days=30):
        """Clean up old log entries"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_logs = self.env['connector.log'].search([
            ('create_date', '<', cutoff_date)
        ])
        return old_logs.unlink()
    
    @api.model
    def process_queue(self):
        """Process pending queue items"""
        queue_items = self.env['connector.queue'].search([
            ('state', '=', 'pending'),
            ('scheduled_date', '<=', fields.Datetime.now())
        ], order='priority desc, create_date')
        
        for item in queue_items:
            try:
                item.process()
            except Exception as e:
                item.log_error(str(e))
                _logger.error(f'Error processing queue item {item.id}: {str(e)}')
    
    # CRUD overrides
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to add validation (Odoo 19 batch-create style)."""
        instances = super().create(vals_list)

        for instance in instances:
            if instance.api_key and instance.api_url:
                try:
                    instance.validate_credentials()
                except Exception as e:
                    instance.log_operation(
                        'warning',
                        f'Credential validation failed: {str(e)}',
                    )

        return instances
    
    def write(self, vals):
        """Override write to add validation"""
        result = super().write(vals)
        
        # Re-validate credentials if API settings changed
        if any(field in vals for field in ['api_url', 'api_key', 'api_secret', 'access_token']):
            for instance in self:
                try:
                    instance.validate_credentials()
                except Exception as e:
                    instance.log_operation('warning', f'Credential validation failed: {str(e)}')
        
        return result
    
    def unlink(self):
        """Override unlink to clean up related data"""
        for instance in self:
            # Clean up related data
            instance.log_ids.unlink()
            instance.queue_ids.unlink()
            instance.mapping_ids.unlink()
            instance.config_ids.unlink()
        
        return super().unlink() 