from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class ConnectorPlatform(models.Model):
    """
    Connector Platform - Platform-specific information and capabilities
    This model manages platform metadata, API specifications, and supported features
    """
    _name = 'connector.platform'
    _description = 'Connector Platform'
    _order = 'name'
    _rec_name = 'name'

    @api.model
    def _valid_field_parameter(self, field, name):
        if name == 'unique':
            return True
        return super()._valid_field_parameter(field, name)

    # Basic Information
    name = fields.Char(
        string='Platform Name',
        required=True,
        help='Name of the eCommerce platform'
    )
    
    code = fields.Char(
        string='Platform Code',
        required=True,
        unique=True,
        help='Unique code for the platform (e.g., shopify, woocommerce)'
    )
    
    version = fields.Char(
        string='Platform Version',
        help='Current version of the platform'
    )
    
    description = fields.Text(
        string='Description',
        help='Description of the platform'
    )
    
    # Platform Information
    website = fields.Char(
        string='Website',
        help='Official website of the platform'
    )
    
    api_documentation = fields.Char(
        string='API Documentation',
        help='Link to API documentation'
    )
    
    developer_portal = fields.Char(
        string='Developer Portal',
        help='Link to developer portal'
    )
    
    # Platform Status
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this platform is active and supported'
    )
    
    is_beta = fields.Boolean(
        string='Beta Version',
        default=False,
        help='Whether this platform support is in beta'
    )
    
    is_deprecated = fields.Boolean(
        string='Deprecated',
        default=False,
        help='Whether this platform is deprecated'
    )
    
    # API Information
    api_type = fields.Selection([
        ('rest', 'REST API'),
        ('graphql', 'GraphQL API'),
        ('soap', 'SOAP API'),
        ('custom', 'Custom API'),
        ('mixed', 'Mixed API')
    ], string='API Type', default='rest', required=True)
    
    api_version = fields.Char(
        string='API Version',
        help='Supported API version'
    )
    
    api_base_url = fields.Char(
        string='API Base URL',
        help='Base URL for the API'
    )
    
    api_rate_limit = fields.Integer(
        string='API Rate Limit',
        help='API rate limit (requests per minute)'
    )
    
    api_timeout = fields.Integer(
        string='API Timeout (seconds)',
        default=30,
        help='Default API timeout in seconds'
    )
    
    # Authentication Methods
    auth_methods = fields.Selection([
        ('api_key', 'API Key'),
        ('oauth', 'OAuth'),
        ('basic', 'Basic Auth'),
        ('token', 'Token'),
        ('custom', 'Custom'),
        ('multiple', 'Multiple Methods')
    ], string='Authentication Methods', default='api_key', required=True)
    
    auth_required_fields = fields.Text(
        string='Required Auth Fields',
        help='JSON array of required authentication fields'
    )
    
    # Supported Features
    supported_features = fields.Text(
        string='Supported Features',
        help='JSON object of supported features and their status'
    )
    
    supported_operations = fields.Text(
        string='Supported Operations',
        help='JSON array of supported operations'
    )
    
    # Data Models
    supported_models = fields.Text(
        string='Supported Models',
        help='JSON object of supported data models'
    )
    
    model_mappings = fields.Text(
        string='Model Mappings',
        help='JSON object mapping platform models to Odoo models'
    )
    
    # Field Mappings
    default_field_mappings = fields.Text(
        string='Default Field Mappings',
        help='JSON object of default field mappings'
    )
    
    # Webhook Support
    webhook_support = fields.Boolean(
        string='Webhook Support',
        default=True,
        help='Whether this platform supports webhooks'
    )
    
    webhook_events = fields.Text(
        string='Webhook Events',
        help='JSON array of supported webhook events'
    )
    
    webhook_authentication = fields.Selection([
        ('none', 'None'),
        ('signature', 'Signature'),
        ('token', 'Token'),
        ('custom', 'Custom')
    ], string='Webhook Authentication', default='signature')
    
    # Performance and Limits
    max_batch_size = fields.Integer(
        string='Max Batch Size',
        default=100,
        help='Maximum batch size for bulk operations'
    )
    
    max_file_size = fields.Integer(
        string='Max File Size (MB)',
        help='Maximum file size for uploads in MB'
    )
    
    concurrent_requests = fields.Integer(
        string='Concurrent Requests',
        default=5,
        help='Maximum number of concurrent API requests'
    )
    
    # Error Handling
    error_codes = fields.Text(
        string='Error Codes',
        help='JSON object of error codes and their descriptions'
    )
    
    retry_strategies = fields.Text(
        string='Retry Strategies',
        help='JSON object of retry strategies for different error types'
    )
    
    # Platform-specific Settings
    platform_settings = fields.Text(
        string='Platform Settings',
        help='JSON object of platform-specific settings'
    )
    
    # Metadata
    last_updated = fields.Datetime(
        string='Last Updated',
        default=fields.Datetime.now,
        help='When this platform information was last updated'
    )
    
    update_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('manual', 'Manual')
    ], string='Update Frequency', default='monthly')
    
    # Statistics
    total_instances = fields.Integer(
        string='Total Instances',
        compute='_compute_total_instances',
        store=True,
        help='Total number of connector instances for this platform'
    )
    
    active_instances = fields.Integer(
        string='Active Instances',
        compute='_compute_active_instances',
        store=True,
        help='Number of active connector instances'
    )
    
    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_success_rate',
        store=True,
        help='Average success rate across all instances'
    )
    
    # Computed Fields
    status = fields.Selection([
        ('active', 'Active'),
        ('beta', 'Beta'),
        ('deprecated', 'Deprecated'),
        ('inactive', 'Inactive')
    ], string='Status', compute='_compute_status', store=True)
    
    @api.depends('is_active', 'is_beta', 'is_deprecated')
    def _compute_status(self):
        """Compute platform status"""
        for platform in self:
            if platform.is_deprecated:
                platform.status = 'deprecated'
            elif platform.is_beta:
                platform.status = 'beta'
            elif platform.is_active:
                platform.status = 'active'
            else:
                platform.status = 'inactive'
    
    @api.depends('instance_ids')
    def _compute_total_instances(self):
        """Compute total number of instances"""
        for platform in self:
            platform.total_instances = len(platform.instance_ids)
    
    @api.depends('instance_ids')
    def _compute_active_instances(self):
        """Compute number of active instances"""
        for platform in self:
            platform.active_instances = len(platform.instance_ids.filtered(lambda i: i.is_active))
    
    @api.depends('instance_ids')
    def _compute_success_rate(self):
        """Compute average success rate"""
        for platform in self:
            instances = platform.instance_ids.filtered(lambda i: i.is_active)
            if instances:
                total_rate = sum(instances.mapped('sync_success_rate'))
                platform.success_rate = total_rate / len(instances)
            else:
                platform.success_rate = 0.0
    
    # Related Records
    instance_ids = fields.One2many(
        'connector.instance',
        'platform_type',
        string='Instances',
        help='Connector instances for this platform'
    )
    
    # Constraints
    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure unique platform code"""
        for platform in self:
            existing = self.search([
                ('code', '=', platform.code),
                ('id', '!=', platform.id)
            ])
            if existing:
                raise ValidationError(_('Platform code must be unique'))
    
    @api.constrains('api_rate_limit', 'api_timeout', 'max_batch_size', 'concurrent_requests')
    def _check_positive_values(self):
        """Ensure positive values for numeric fields"""
        for platform in self:
            if platform.api_rate_limit and platform.api_rate_limit <= 0:
                raise ValidationError(_('API rate limit must be positive'))
            if platform.api_timeout <= 0:
                raise ValidationError(_('API timeout must be positive'))
            if platform.max_batch_size <= 0:
                raise ValidationError(_('Max batch size must be positive'))
            if platform.concurrent_requests <= 0:
                raise ValidationError(_('Concurrent requests must be positive'))
    
    # Actions
    def action_view_instances(self):
        """View instances for this platform"""
        self.ensure_one()
        return {
            'name': _('Platform Instances'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.instance',
            'view_mode': 'tree,form',
            'domain': [('platform_type', '=', self.code)],
            'context': {'default_platform_type': self.code},
        }
    
    def action_test_platform(self):
        """Test platform connectivity and features"""
        self.ensure_one()
        
        try:
            # Test platform features
            test_results = self._test_platform_features()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Platform Test'),
                    'message': f'Platform test completed. {test_results.get("message", "")}',
                    'type': 'success' if test_results.get('success') else 'warning',
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Platform Test Failed'),
                    'message': str(e),
                    'type': 'danger',
                }
            }
    
    def action_update_platform_info(self):
        """Update platform information"""
        self.ensure_one()
        
        try:
            # Update platform information
            self._update_platform_info()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Update Successful'),
                    'message': _('Platform information has been updated.'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Update Failed'),
                    'message': str(e),
                    'type': 'danger',
                }
            }
    
    def action_export_platform_config(self):
        """Export platform configuration"""
        self.ensure_one()
        
        config_data = self._export_platform_config()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/export/json?model=connector.platform&ids={self.id}',
            'target': 'self',
        }
    
    # Platform Methods
    def get_supported_features(self):
        """Get supported features as dictionary"""
        if self.supported_features:
            try:
                return json.loads(self.supported_features)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def is_feature_supported(self, feature_name):
        """Check if a specific feature is supported"""
        features = self.get_supported_features()
        return features.get(feature_name, {}).get('supported', False)
    
    def get_supported_operations(self):
        """Get supported operations as list"""
        if self.supported_operations:
            try:
                return json.loads(self.supported_operations)
            except json.JSONDecodeError:
                return []
        return []
    
    def is_operation_supported(self, operation_name):
        """Check if a specific operation is supported"""
        operations = self.get_supported_operations()
        return operation_name in operations
    
    def get_supported_models(self):
        """Get supported models as dictionary"""
        if self.supported_models:
            try:
                return json.loads(self.supported_models)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_model_mapping(self, platform_model):
        """Get Odoo model mapping for platform model"""
        if self.model_mappings:
            try:
                mappings = json.loads(self.model_mappings)
                return mappings.get(platform_model)
            except json.JSONDecodeError:
                return None
        return None
    
    def get_default_field_mappings(self, model_name):
        """Get default field mappings for a model"""
        if self.default_field_mappings:
            try:
                mappings = json.loads(self.default_field_mappings)
                return mappings.get(model_name, {})
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_webhook_events(self):
        """Get supported webhook events as list"""
        if self.webhook_events:
            try:
                return json.loads(self.webhook_events)
            except json.JSONDecodeError:
                return []
        return []
    
    def get_error_codes(self):
        """Get error codes as dictionary"""
        if self.error_codes:
            try:
                return json.loads(self.error_codes)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_retry_strategies(self):
        """Get retry strategies as dictionary"""
        if self.retry_strategies:
            try:
                return json.loads(self.retry_strategies)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_platform_settings(self):
        """Get platform-specific settings as dictionary"""
        if self.platform_settings:
            try:
                return json.loads(self.platform_settings)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def _test_platform_features(self):
        """Test platform features and connectivity"""
        # This should be implemented by platform-specific modules
        return {
            'success': True,
            'message': 'Platform features test not implemented',
            'features_tested': []
        }
    
    def _update_platform_info(self):
        """Update platform information from external sources"""
        # This should be implemented by platform-specific modules
        self.last_updated = fields.Datetime.now()
        return True
    
    def _export_platform_config(self):
        """Export platform configuration"""
        return {
            'name': self.name,
            'code': self.code,
            'version': self.version,
            'api_type': self.api_type,
            'api_version': self.api_version,
            'supported_features': self.supported_features,
            'supported_operations': self.supported_operations,
            'supported_models': self.supported_models,
            'model_mappings': self.model_mappings,
            'default_field_mappings': self.default_field_mappings,
            'webhook_events': self.webhook_events,
            'error_codes': self.error_codes,
            'retry_strategies': self.retry_strategies,
            'platform_settings': self.platform_settings,
        }
    
    # Class Methods
    @api.model
    def create_default_platforms(self):
        """Create default platform definitions"""
        default_platforms = [
            {
                'name': 'Shopify',
                'code': 'shopify',
                'version': '2024-01',
                'description': 'Shopify is a leading eCommerce platform',
                'website': 'https://www.shopify.com',
                'api_documentation': 'https://shopify.dev/api',
                'api_type': 'rest',
                'api_version': '2024-01',
                'api_base_url': 'https://{shop}.myshopify.com/admin/api/{version}',
                'api_rate_limit': 40,
                'auth_methods': 'oauth',
                'webhook_support': True,
                'supported_features': json.dumps({
                    'products': {'supported': True, 'version': '2024-01'},
                    'orders': {'supported': True, 'version': '2024-01'},
                    'customers': {'supported': True, 'version': '2024-01'},
                    'inventory': {'supported': True, 'version': '2024-01'},
                    'payments': {'supported': True, 'version': '2024-01'},
                }),
                'supported_operations': json.dumps([
                    'sync_products', 'sync_orders', 'sync_customers',
                    'sync_inventory', 'sync_payments', 'webhook_process'
                ]),
                'supported_models': json.dumps({
                    'product': 'product.template',
                    'variant': 'product.product',
                    'order': 'sale.order',
                    'customer': 'res.partner',
                    'inventory': 'stock.move',
                    'payment': 'account.payment',
                }),
                'webhook_events': json.dumps([
                    'products/create', 'products/update', 'products/delete',
                    'orders/create', 'orders/updated', 'orders/paid',
                    'customers/create', 'customers/update',
                    'inventory_levels/update'
                ]),
            },
            {
                'name': 'WooCommerce',
                'code': 'woocommerce',
                'version': '8.0',
                'description': 'WooCommerce is a WordPress eCommerce plugin',
                'website': 'https://woocommerce.com',
                'api_documentation': 'https://woocommerce.github.io/woocommerce-rest-api-docs/',
                'api_type': 'rest',
                'api_version': 'wc/v3',
                'api_base_url': 'https://{domain}/wp-json/wc/v3',
                'api_rate_limit': 100,
                'auth_methods': 'api_key',
                'webhook_support': True,
                'supported_features': json.dumps({
                    'products': {'supported': True, 'version': 'v3'},
                    'orders': {'supported': True, 'version': 'v3'},
                    'customers': {'supported': True, 'version': 'v3'},
                    'inventory': {'supported': True, 'version': 'v3'},
                    'payments': {'supported': True, 'version': 'v3'},
                }),
                'supported_operations': json.dumps([
                    'sync_products', 'sync_orders', 'sync_customers',
                    'sync_inventory', 'sync_payments', 'webhook_process'
                ]),
                'supported_models': json.dumps({
                    'product': 'product.template',
                    'variation': 'product.product',
                    'order': 'sale.order',
                    'customer': 'res.partner',
                    'inventory': 'stock.move',
                    'payment': 'account.payment',
                }),
                'webhook_events': json.dumps([
                    'product.created', 'product.updated', 'product.deleted',
                    'order.created', 'order.updated', 'order.completed',
                    'customer.created', 'customer.updated',
                    'product.low_stock'
                ]),
            },
            {
                'name': 'Magento',
                'code': 'magento',
                'version': '2.4',
                'description': 'Magento is an Adobe eCommerce platform',
                'website': 'https://business.adobe.com/products/magento/magento-commerce.html',
                'api_documentation': 'https://developer.adobe.com/commerce/webapi/',
                'api_type': 'rest',
                'api_version': 'V1',
                'api_base_url': 'https://{domain}/rest/V1',
                'api_rate_limit': 50,
                'auth_methods': 'token',
                'webhook_support': True,
                'supported_features': json.dumps({
                    'products': {'supported': True, 'version': 'V1'},
                    'orders': {'supported': True, 'version': 'V1'},
                    'customers': {'supported': True, 'version': 'V1'},
                    'inventory': {'supported': True, 'version': 'V1'},
                    'payments': {'supported': True, 'version': 'V1'},
                }),
                'supported_operations': json.dumps([
                    'sync_products', 'sync_orders', 'sync_customers',
                    'sync_inventory', 'sync_payments', 'webhook_process'
                ]),
                'supported_models': json.dumps({
                    'product': 'product.template',
                    'product_variant': 'product.product',
                    'order': 'sale.order',
                    'customer': 'res.partner',
                    'inventory': 'stock.move',
                    'payment': 'account.payment',
                }),
                'webhook_events': json.dumps([
                    'catalog_product_save_after',
                    'sales_order_save_after',
                    'customer_save_after',
                    'inventory_source_items_save_after'
                ]),
            }
        ]
        
        created_platforms = []
        for platform_data in default_platforms:
            # Check if platform already exists
            existing = self.search([('code', '=', platform_data['code'])], limit=1)
            if not existing:
                platform = self.create(platform_data)
                created_platforms.append(platform)
        
        return created_platforms
    
    @api.model
    def get_platform_by_code(self, code):
        """Get platform by code"""
        return self.search([('code', '=', code)], limit=1)
    
    @api.model
    def get_active_platforms(self):
        """Get all active platforms"""
        return self.search([('is_active', '=', True)])
    
    @api.model
    def update_all_platforms(self):
        """Update information for all platforms"""
        platforms = self.search([('is_active', '=', True)])
        
        updated_count = 0
        for platform in platforms:
            try:
                platform._update_platform_info()
                updated_count += 1
            except Exception as e:
                _logger.error(f'Error updating platform {platform.name}: {str(e)}')
        
        return updated_count
    
    # CRUD Overrides
    def create(self, vals):
        """Override create to add validation"""
        # Validate JSON fields
        json_fields = ['supported_features', 'supported_operations', 'supported_models',
                      'model_mappings', 'default_field_mappings', 'webhook_events',
                      'error_codes', 'retry_strategies', 'platform_settings']
        
        for field in json_fields:
            if field in vals and vals[field]:
                try:
                    json.loads(vals[field])
                except json.JSONDecodeError:
                    raise ValidationError(_('Invalid JSON format for field: %s') % field)
        
        return super().create(vals)
    
    def write(self, vals):
        """Override write to add validation"""
        # Validate JSON fields
        json_fields = ['supported_features', 'supported_operations', 'supported_models',
                      'model_mappings', 'default_field_mappings', 'webhook_events',
                      'error_codes', 'retry_strategies', 'platform_settings']
        
        for field in json_fields:
            if field in vals and vals[field]:
                try:
                    json.loads(vals[field])
                except json.JSONDecodeError:
                    raise ValidationError(_('Invalid JSON format for field: %s') % field)
        
        return super().write(vals) 