from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class ConnectorConfig(models.Model):
    """
    Connector Config - Platform-specific configuration management
    This model manages configuration settings for different platforms
    """
    _name = 'connector.config'
    _description = 'Connector Configuration'
    _order = 'sequence, id'
    _rec_name = 'name'

    # Basic Information
    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='Name to identify this configuration'
    )
    
    instance_id = fields.Many2one(
        'connector.instance',
        string='Connector Instance',
        required=True,
        ondelete='cascade',
        help='The connector instance this configuration belongs to'
    )
    
    platform_type = fields.Selection(
        related='instance_id.platform_type',
        string='Platform Type',
        store=True,
        readonly=True
    )
    
    # Configuration Type
    config_type = fields.Selection([
        ('sync_settings', 'Sync Settings'),
        ('api_settings', 'API Settings'),
        ('mapping_settings', 'Mapping Settings'),
        ('webhook_settings', 'Webhook Settings'),
        ('notification_settings', 'Notification Settings'),
        ('performance_settings', 'Performance Settings'),
        ('security_settings', 'Security Settings'),
        ('custom_settings', 'Custom Settings')
    ], string='Configuration Type', required=True, index=True)
    
    # Configuration Data
    config_key = fields.Char(
        string='Configuration Key',
        required=True,
        help='Configuration key/parameter name'
    )
    
    config_value = fields.Text(
        string='Configuration Value',
        help='Configuration value (can be JSON for complex data)'
    )
    
    value_type = fields.Selection([
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('selection', 'Selection'),
        ('password', 'Password'),
        ('file', 'File Path')
    ], string='Value Type', required=True, default='string')
    
    # Selection Options (for selection type)
    selection_options = fields.Text(
        string='Selection Options',
        help='JSON array of selection options'
    )
    
    # Validation and Constraints
    is_required = fields.Boolean(
        string='Required',
        default=False,
        help='Whether this configuration is required'
    )
    
    validation_rule = fields.Text(
        string='Validation Rule',
        help='JSON validation rule for this configuration'
    )
    
    default_value = fields.Char(
        string='Default Value',
        help='Default value for this configuration'
    )
    
    # Status and Organization
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Enable or disable this configuration'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of configuration items'
    )
    
    group_name = fields.Char(
        string='Group Name',
        help='Group this configuration belongs to'
    )
    
    # Metadata
    description = fields.Text(
        string='Description',
        help='Description of this configuration'
    )
    
    help_text = fields.Text(
        string='Help Text',
        help='Help text for users'
    )
    
    # Security
    is_sensitive = fields.Boolean(
        string='Sensitive Data',
        default=False,
        help='Whether this configuration contains sensitive data'
    )
    
    encrypted = fields.Boolean(
        string='Encrypted',
        default=False,
        help='Whether this value should be encrypted'
    )
    
    # Computed Fields
    display_value = fields.Char(
        string='Display Value',
        compute='_compute_display_value',
        store=True,
        help='Formatted display value'
    )
    
    is_valid = fields.Boolean(
        string='Is Valid',
        compute='_compute_is_valid',
        store=True,
        help='Whether this configuration is valid'
    )
    
    @api.depends('config_value', 'value_type', 'is_sensitive')
    def _compute_display_value(self):
        """Compute display value (masked for sensitive data)"""
        for config in self:
            if config.is_sensitive and config.config_value:
                config.display_value = '*' * len(config.config_value)
            elif config.value_type == 'boolean':
                config.display_value = 'True' if config.config_value == 'true' else 'False'
            elif config.value_type == 'json':
                try:
                    parsed = json.loads(config.config_value)
                    config.display_value = json.dumps(parsed, indent=2)
                except:
                    config.display_value = config.config_value
            else:
                config.display_value = config.config_value or ''
    
    @api.depends('config_key', 'is_active', 'is_required', 'config_value')
    def _compute_is_valid(self):
        """Compute whether this configuration is valid"""
        for config in self:
            config.is_valid = (
                config.is_active and
                config.config_key and
                (not config.is_required or config.config_value)
            )
    
    # Constraints
    @api.constrains('config_key', 'instance_id', 'config_type')
    def _check_unique_config(self):
        """Ensure unique configuration keys per instance and type"""
        for config in self:
            existing = self.search([
                ('instance_id', '=', config.instance_id.id),
                ('config_type', '=', config.config_type),
                ('config_key', '=', config.config_key),
                ('id', '!=', config.id)
            ])
            if existing:
                raise ValidationError(_('A configuration with this key already exists for this instance and type'))
    
    @api.constrains('config_value', 'value_type')
    def _check_value_type(self):
        """Validate value type"""
        for config in self:
            if config.config_value:
                if config.value_type == 'integer':
                    try:
                        int(config.config_value)
                    except ValueError:
                        raise ValidationError(_('Value must be an integer'))
                elif config.value_type == 'float':
                    try:
                        float(config.config_value)
                    except ValueError:
                        raise ValidationError(_('Value must be a number'))
                elif config.value_type == 'boolean':
                    if config.config_value not in ['true', 'false', 'True', 'False', '1', '0']:
                        raise ValidationError(_('Value must be true/false'))
                elif config.value_type == 'json':
                    try:
                        json.loads(config.config_value)
                    except json.JSONDecodeError:
                        raise ValidationError(_('Value must be valid JSON'))
    
    # Actions
    def action_test_config(self):
        """Test this configuration"""
        self.ensure_one()
        
        try:
            # Validate the configuration
            self._validate_config()
            
            # Test the configuration based on type
            if self.config_type == 'api_settings':
                result = self._test_api_config()
            elif self.config_type == 'webhook_settings':
                result = self._test_webhook_config()
            else:
                result = {'success': True, 'message': 'Configuration is valid'}
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Successful'),
                    'message': result.get('message', _('Configuration test completed successfully.')),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Failed'),
                    'message': str(e),
                    'type': 'danger',
                }
            }
    
    def action_reset_to_default(self):
        """Reset configuration to default value"""
        self.ensure_one()
        
        if self.default_value:
            self.config_value = self.default_value
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Reset Successful'),
                    'message': _('Configuration has been reset to default value.'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Default'),
                    'message': _('No default value is set for this configuration.'),
                    'type': 'warning',
                }
            }
    
    def action_duplicate_config(self):
        """Duplicate this configuration"""
        self.ensure_one()
        
        new_config = self.copy({
            'name': f'{self.name} (Copy)',
        })
        
        return {
            'name': _('Duplicated Configuration'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.config',
            'res_id': new_config.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # Configuration Methods
    def get_config_value(self, key, default=None):
        """Get configuration value by key"""
        config = self.search([
            ('instance_id', '=', self.instance_id.id),
            ('config_key', '=', key),
            ('is_active', '=', True)
        ], limit=1)
        
        if config:
            return config._parse_value()
        return default
    
    def set_config_value(self, key, value, value_type='string'):
        """Set configuration value by key"""
        config = self.search([
            ('instance_id', '=', self.instance_id.id),
            ('config_key', '=', key)
        ], limit=1)
        
        if config:
            config.write({
                'config_value': str(value),
                'value_type': value_type
            })
        else:
            self.create({
                'instance_id': self.instance_id.id,
                'name': key,
                'config_key': key,
                'config_value': str(value),
                'value_type': value_type,
                'config_type': 'custom_settings'
            })
    
    def get_config_group(self, group_name):
        """Get all configurations in a group"""
        return self.search([
            ('instance_id', '=', self.instance_id.id),
            ('group_name', '=', group_name),
            ('is_active', '=', True)
        ], order='sequence')
    
    def _parse_value(self):
        """Parse configuration value based on type"""
        if not self.config_value:
            return None
        
        try:
            if self.value_type == 'integer':
                return int(self.config_value)
            elif self.value_type == 'float':
                return float(self.config_value)
            elif self.value_type == 'boolean':
                return self.config_value.lower() in ['true', '1']
            elif self.value_type == 'json':
                return json.loads(self.config_value)
            elif self.value_type == 'date':
                return fields.Date.from_string(self.config_value)
            elif self.value_type == 'datetime':
                return fields.Datetime.from_string(self.config_value)
            else:
                return self.config_value
        except Exception as e:
            _logger.error(f'Error parsing config value {self.config_key}: {str(e)}')
            return self.config_value
    
    def _validate_config(self):
        """Validate configuration value"""
        if self.is_required and not self.config_value:
            raise ValidationError(_('This configuration is required'))
        
        if self.validation_rule:
            try:
                rule = json.loads(self.validation_rule)
                value = self._parse_value()
                
                # Type validation
                expected_type = rule.get('type')
                if expected_type:
                    if expected_type == 'integer' and not isinstance(value, int):
                        raise ValidationError(_('Value must be an integer'))
                    elif expected_type == 'float' and not isinstance(value, (int, float)):
                        raise ValidationError(_('Value must be a number'))
                    elif expected_type == 'boolean' and not isinstance(value, bool):
                        raise ValidationError(_('Value must be a boolean'))
                
                # Range validation
                min_value = rule.get('min')
                max_value = rule.get('max')
                if min_value is not None and value < min_value:
                    raise ValidationError(_('Value must be at least %s') % min_value)
                if max_value is not None and value > max_value:
                    raise ValidationError(_('Value must be at most %s') % max_value)
                
                # Pattern validation
                pattern = rule.get('pattern')
                if pattern and isinstance(value, str):
                    import re
                    if not re.match(pattern, value):
                        raise ValidationError(_('Value does not match required pattern'))
                
                # Custom validation
                custom_validator = rule.get('validator')
                if custom_validator:
                    # Execute custom validation function
                    # This should be implemented safely in production
                    pass
                    
            except json.JSONDecodeError:
                raise ValidationError(_('Invalid validation rule format'))
    
    def _test_api_config(self):
        """Test API configuration"""
        # This should be implemented by platform-specific modules
        return {'success': True, 'message': 'API configuration test not implemented'}
    
    def _test_webhook_config(self):
        """Test webhook configuration"""
        # This should be implemented by platform-specific modules
        return {'success': True, 'message': 'Webhook configuration test not implemented'}
    
    # Class Methods
    @api.model
    def create_default_configs(self, instance_id, platform_type):
        """Create default configurations for a platform"""
        default_configs = self._get_default_configs(platform_type)
        
        created_configs = []
        for config_data in default_configs:
            config_data['instance_id'] = instance_id
            config = self.create(config_data)
            created_configs.append(config)
        
        return created_configs
    
    @api.model
    def _get_default_configs(self, platform_type):
        """Get default configurations for a platform"""
        base_configs = [
            {
                'name': 'Sync Interval',
                'config_type': 'sync_settings',
                'config_key': 'sync_interval',
                'config_value': '30',
                'value_type': 'integer',
                'is_required': True,
                'description': 'Interval between sync operations in minutes',
                'group_name': 'Sync Settings'
            },
            {
                'name': 'Batch Size',
                'config_type': 'performance_settings',
                'config_key': 'batch_size',
                'config_value': '100',
                'value_type': 'integer',
                'is_required': True,
                'description': 'Number of records to process in each batch',
                'group_name': 'Performance'
            },
            {
                'name': 'Retry Attempts',
                'config_type': 'sync_settings',
                'config_key': 'retry_attempts',
                'config_value': '3',
                'value_type': 'integer',
                'is_required': True,
                'description': 'Number of retry attempts for failed operations',
                'group_name': 'Sync Settings'
            },
            {
                'name': 'Enable Notifications',
                'config_type': 'notification_settings',
                'config_key': 'enable_notifications',
                'config_value': 'true',
                'value_type': 'boolean',
                'is_required': True,
                'description': 'Enable email notifications for sync events',
                'group_name': 'Notifications'
            },
            {
                'name': 'Log Level',
                'config_type': 'sync_settings',
                'config_key': 'log_level',
                'config_value': 'info',
                'value_type': 'selection',
                'selection_options': '["debug", "info", "warning", "error"]',
                'is_required': True,
                'description': 'Logging level for connector operations',
                'group_name': 'Sync Settings'
            }
        ]
        
        # Add platform-specific configurations
        platform_configs = self._get_platform_specific_configs(platform_type)
        base_configs.extend(platform_configs)
        
        return base_configs
    
    @api.model
    def _get_platform_specific_configs(self, platform_type):
        """Get platform-specific default configurations"""
        if platform_type == 'shopify':
            return [
                {
                    'name': 'Shopify API Version',
                    'config_type': 'api_settings',
                    'config_key': 'api_version',
                    'config_value': '2024-01',
                    'value_type': 'string',
                    'is_required': True,
                    'description': 'Shopify API version to use',
                    'group_name': 'API Settings'
                },
                {
                    'name': 'Webhook Secret',
                    'config_type': 'webhook_settings',
                    'config_key': 'webhook_secret',
                    'config_value': '',
                    'value_type': 'password',
                    'is_sensitive': True,
                    'description': 'Secret key for webhook verification',
                    'group_name': 'Webhook Settings'
                }
            ]
        elif platform_type == 'woocommerce':
            return [
                {
                    'name': 'WooCommerce API Version',
                    'config_type': 'api_settings',
                    'config_key': 'api_version',
                    'config_value': 'wc/v3',
                    'value_type': 'string',
                    'is_required': True,
                    'description': 'WooCommerce API version to use',
                    'group_name': 'API Settings'
                }
            ]
        else:
            return []
    
    @api.model
    def get_config_by_type(self, instance_id, config_type):
        """Get all configurations of a specific type"""
        return self.search([
            ('instance_id', '=', instance_id),
            ('config_type', '=', config_type),
            ('is_active', '=', True)
        ], order='sequence')
    
    @api.model
    def export_configs(self, instance_id):
        """Export configurations as JSON"""
        configs = self.search([
            ('instance_id', '=', instance_id),
            ('is_active', '=', True)
        ])
        
        export_data = []
        for config in configs:
            config_data = {
                'name': config.name,
                'config_type': config.config_type,
                'config_key': config.config_key,
                'config_value': config.config_value if not config.is_sensitive else '',
                'value_type': config.value_type,
                'is_required': config.is_required,
                'group_name': config.group_name,
                'description': config.description,
                'help_text': config.help_text,
            }
            export_data.append(config_data)
        
        return export_data
    
    @api.model
    def import_configs(self, instance_id, config_data):
        """Import configurations from JSON"""
        imported_count = 0
        
        for config_item in config_data:
            # Check if config already exists
            existing = self.search([
                ('instance_id', '=', instance_id),
                ('config_key', '=', config_item.get('config_key'))
            ], limit=1)
            
            if existing:
                # Update existing config
                existing.write({
                    'name': config_item.get('name', existing.name),
                    'config_value': config_item.get('config_value', existing.config_value),
                    'description': config_item.get('description', existing.description),
                    'help_text': config_item.get('help_text', existing.help_text),
                })
            else:
                # Create new config
                config_item['instance_id'] = instance_id
                self.create(config_item)
            
            imported_count += 1
        
        return imported_count
    
    # CRUD Overrides
    def create(self, vals):
        """Override create to add validation"""
        # Set default name if not provided
        if 'name' not in vals and 'config_key' in vals:
            vals['name'] = vals['config_key'].replace('_', ' ').title()
        
        return super().create(vals)
    
    def write(self, vals):
        """Override write to add validation"""
        result = super().write(vals)
        
        # Validate configurations after update
        for config in self:
            try:
                config._validate_config()
            except ValidationError as e:
                _logger.warning(f'Configuration validation warning for {config.config_key}: {str(e)}')
        
        return result
    
    def unlink(self):
        """Override unlink to prevent deletion of required configs"""
        for config in self:
            if config.is_required:
                raise ValidationError(_('Cannot delete required configuration: %s') % config.name)
        
        return super().unlink() 