from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class ConnectorMapping(models.Model):
    """
    Connector Mapping - Flexible field mapping system for data transformation
    This model manages field mappings between different platforms and Odoo
    """
    _name = 'connector.mapping'
    _description = 'Connector Field Mapping'
    _order = 'sequence, id'
    _rec_name = 'name'

    # Basic Information
    name = fields.Char(
        string='Mapping Name',
        required=True,
        help='Name to identify this field mapping'
    )
    
    instance_id = fields.Many2one(
        'connector.instance',
        string='Connector Instance',
        required=True,
        ondelete='cascade',
        help='The connector instance this mapping belongs to'
    )
    
    platform_type = fields.Selection(
        related='instance_id.platform_type',
        string='Platform Type',
        store=True,
        readonly=True
    )
    
    # Mapping Configuration
    model_name = fields.Selection([
        ('product.template', 'Product Template'),
        ('product.product', 'Product Variant'),
        ('sale.order', 'Sales Order'),
        ('sale.order.line', 'Order Line'),
        ('res.partner', 'Customer/Supplier'),
        ('stock.move', 'Stock Move'),
        ('account.move', 'Invoice'),
        ('account.payment', 'Payment'),
        ('custom', 'Custom Model')
    ], string='Odoo Model', required=True, index=True)
    
    custom_model_name = fields.Char(
        string='Custom Model Name',
        help='Custom model name if not in the predefined list'
    )
    
    direction = fields.Selection([
        ('import', 'Import (External → Odoo)'),
        ('export', 'Export (Odoo → External)'),
        ('bidirectional', 'Bidirectional')
    ], string='Direction', required=True, default='bidirectional', index=True)
    
    # Field Mapping
    external_field = fields.Char(
        string='External Field',
        required=True,
        help='Field name in the external platform'
    )
    
    odoo_field = fields.Char(
        string='Odoo Field',
        required=True,
        help='Field name in Odoo model'
    )
    
    field_type = fields.Selection([
        ('char', 'Text'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('many2one', 'Many2One'),
        ('many2many', 'Many2Many'),
        ('one2many', 'One2Many'),
        ('selection', 'Selection'),
        ('json', 'JSON'),
        ('binary', 'Binary'),
        ('html', 'HTML'),
        ('monetary', 'Monetary'),
        ('custom', 'Custom')
    ], string='Field Type', required=True, default='char')
    
    # Transformation Rules
    transformation_type = fields.Selection([
        ('direct', 'Direct Copy'),
        ('format', 'Format Conversion'),
        ('lookup', 'Lookup/Mapping'),
        ('calculation', 'Calculation'),
        ('conditional', 'Conditional'),
        ('custom', 'Custom Function')
    ], string='Transformation Type', default='direct', required=True)
    
    transformation_rule = fields.Text(
        string='Transformation Rule',
        help='JSON configuration for the transformation rule'
    )
    
    # Value Mapping
    value_mapping = fields.Text(
        string='Value Mapping',
        help='JSON mapping of values between platforms'
    )
    
    # Default Values
    default_value = fields.Char(
        string='Default Value',
        help='Default value if external field is empty'
    )
    
    default_value_type = fields.Selection([
        ('static', 'Static Value'),
        ('computed', 'Computed Value'),
        ('field', 'Field Reference')
    ], string='Default Value Type', default='static')
    
    # Validation Rules
    is_required = fields.Boolean(
        string='Required Field',
        default=False,
        help='Whether this field is required'
    )
    
    validation_rule = fields.Text(
        string='Validation Rule',
        help='JSON validation rule configuration'
    )
    
    error_message = fields.Char(
        string='Error Message',
        help='Custom error message for validation failures'
    )
    
    # Performance and Caching
    is_cached = fields.Boolean(
        string='Cache Field',
        default=False,
        help='Whether to cache this field value'
    )
    
    cache_duration = fields.Integer(
        string='Cache Duration (hours)',
        default=24,
        help='How long to cache this field value'
    )
    
    # Status and Configuration
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Enable or disable this mapping'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of processing for this mapping'
    )
    
    # Advanced Configuration
    conditional_expression = fields.Text(
        string='Conditional Expression',
        help='Python expression to determine if this mapping should be applied'
    )
    
    pre_processing = fields.Text(
        string='Pre-processing Code',
        help='Python code to execute before mapping'
    )
    
    post_processing = fields.Text(
        string='Post-processing Code',
        help='Python code to execute after mapping'
    )
    
    # Metadata
    description = fields.Text(
        string='Description',
        help='Additional description for this mapping'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Internal notes about this mapping'
    )
    
    # Statistics
    usage_count = fields.Integer(
        string='Usage Count',
        default=0,
        help='Number of times this mapping has been used'
    )
    
    last_used = fields.Datetime(
        string='Last Used',
        help='When this mapping was last used'
    )
    
    success_count = fields.Integer(
        string='Success Count',
        default=0,
        help='Number of successful mappings'
    )
    
    error_count = fields.Integer(
        string='Error Count',
        default=0,
        help='Number of mapping errors'
    )
    
    # Computed Fields
    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_success_rate',
        store=True,
        help='Success rate of this mapping'
    )
    
    is_valid = fields.Boolean(
        string='Is Valid',
        compute='_compute_is_valid',
        store=True,
        help='Whether this mapping is valid'
    )
    
    @api.depends('success_count', 'error_count')
    def _compute_success_rate(self):
        """Compute success rate percentage"""
        for mapping in self:
            total = mapping.success_count + mapping.error_count
            if total > 0:
                mapping.success_rate = (mapping.success_count / total) * 100
            else:
                mapping.success_rate = 100.0
    
    @api.depends('external_field', 'odoo_field', 'is_active')
    def _compute_is_valid(self):
        """Compute whether this mapping is valid"""
        for mapping in self:
            mapping.is_valid = (
                mapping.is_active and
                mapping.external_field and
                mapping.odoo_field and
                mapping.model_name
            )
    
    # Constraints
    @api.constrains('external_field', 'odoo_field', 'instance_id')
    def _check_unique_mapping(self):
        """Ensure unique field mappings per instance"""
        for mapping in self:
            existing = self.search([
                ('instance_id', '=', mapping.instance_id.id),
                ('external_field', '=', mapping.external_field),
                ('odoo_field', '=', mapping.odoo_field),
                ('model_name', '=', mapping.model_name),
                ('id', '!=', mapping.id)
            ])
            if existing:
                raise ValidationError(_('A mapping with these fields already exists for this instance'))
    
    @api.constrains('cache_duration')
    def _check_cache_duration(self):
        """Ensure positive cache duration"""
        for mapping in self:
            if mapping.cache_duration < 0:
                raise ValidationError(_('Cache duration cannot be negative'))
    
    # Actions
    def action_test_mapping(self):
        """Test this mapping with sample data"""
        self.ensure_one()
        
        # Create test data
        test_data = self._generate_test_data()
        
        try:
            # Test import mapping
            if self.direction in ['import', 'bidirectional']:
                result = self._apply_mapping(test_data, 'import')
                self._log_test_result('import', True, result)
            
            # Test export mapping
            if self.direction in ['export', 'bidirectional']:
                result = self._apply_mapping(test_data, 'export')
                self._log_test_result('export', True, result)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Successful'),
                    'message': _('Mapping test completed successfully.'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            self._log_test_result('test', False, str(e))
            raise ValidationError(_('Mapping test failed: %s') % str(e))
    
    def action_reset_statistics(self):
        """Reset usage statistics"""
        self.ensure_one()
        self.write({
            'usage_count': 0,
            'success_count': 0,
            'error_count': 0,
            'last_used': False,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Statistics Reset'),
                'message': _('Mapping statistics have been reset.'),
                'type': 'success',
            }
        }
    
    def action_duplicate_mapping(self):
        """Duplicate this mapping"""
        self.ensure_one()
        
        new_mapping = self.copy({
            'name': f'{self.name} (Copy)',
            'usage_count': 0,
            'success_count': 0,
            'error_count': 0,
            'last_used': False,
        })
        
        return {
            'name': _('Duplicated Mapping'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.mapping',
            'res_id': new_mapping.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # Mapping Methods
    def apply_mapping(self, data, direction='import'):
        """Apply this mapping to transform data"""
        self.ensure_one()
        
        try:
            result = self._apply_mapping(data, direction)
            
            # Update statistics
            self.usage_count += 1
            self.success_count += 1
            self.last_used = fields.Datetime.now()
            
            return result
            
        except Exception as e:
            # Update error statistics
            self.usage_count += 1
            self.error_count += 1
            self.last_used = fields.Datetime.now()
            
            # Log error
            self._log_mapping_error(str(e), data)
            raise
    
    def _apply_mapping(self, data, direction):
        """Internal method to apply the mapping transformation"""
        # Get source and target field names
        if direction == 'import':
            source_field = self.external_field
            target_field = self.odoo_field
        else:  # export
            source_field = self.odoo_field
            target_field = self.external_field
        
        # Get source value
        source_value = self._get_field_value(data, source_field)
        
        # Apply transformation
        transformed_value = self._transform_value(source_value, direction)
        
        # Apply validation
        self._validate_value(transformed_value)
        
        return {target_field: transformed_value}
    
    def _get_field_value(self, data, field_name):
        """Get field value from data dictionary"""
        # Handle nested field names (e.g., 'user.name')
        if '.' in field_name:
            parts = field_name.split('.')
            value = data
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            return value
        else:
            return data.get(field_name)
    
    def _transform_value(self, value, direction):
        """Transform value according to mapping rules"""
        # Handle None/empty values
        if value is None or value == '':
            return self._get_default_value()
        
        # Apply transformation based on type
        if self.transformation_type == 'direct':
            return self._direct_transform(value)
        elif self.transformation_type == 'format':
            return self._format_transform(value)
        elif self.transformation_type == 'lookup':
            return self._lookup_transform(value, direction)
        elif self.transformation_type == 'calculation':
            return self._calculation_transform(value)
        elif self.transformation_type == 'conditional':
            return self._conditional_transform(value)
        elif self.transformation_type == 'custom':
            return self._custom_transform(value, direction)
        else:
            return value
    
    def _direct_transform(self, value):
        """Direct value transformation"""
        return value
    
    def _format_transform(self, value):
        """Format-based transformation"""
        if not self.transformation_rule:
            return value
        
        try:
            rule = json.loads(self.transformation_rule)
            format_type = rule.get('format_type')
            
            if format_type == 'date':
                # Date format transformation
                from datetime import datetime
                input_format = rule.get('input_format', '%Y-%m-%d')
                output_format = rule.get('output_format', '%Y-%m-%d')
                
                if isinstance(value, str):
                    date_obj = datetime.strptime(value, input_format)
                    return date_obj.strftime(output_format)
            
            elif format_type == 'number':
                # Number format transformation
                precision = rule.get('precision', 2)
                return round(float(value), precision)
            
            elif format_type == 'text':
                # Text format transformation
                case = rule.get('case', 'lower')
                if case == 'upper':
                    return str(value).upper()
                elif case == 'lower':
                    return str(value).lower()
                elif case == 'title':
                    return str(value).title()
            
            return value
            
        except Exception as e:
            _logger.error(f'Format transformation error: {str(e)}')
            return value
    
    def _lookup_transform(self, value, direction):
        """Lookup-based transformation"""
        if not self.value_mapping:
            return value
        
        try:
            mapping = json.loads(self.value_mapping)
            
            if direction == 'import':
                # External → Odoo
                return mapping.get(str(value), value)
            else:
                # Odoo → External
                # Reverse lookup
                for ext_val, odoo_val in mapping.items():
                    if odoo_val == value:
                        return ext_val
                return value
                
        except Exception as e:
            _logger.error(f'Lookup transformation error: {str(e)}')
            return value
    
    def _calculation_transform(self, value):
        """Calculation-based transformation"""
        if not self.transformation_rule:
            return value
        
        try:
            rule = json.loads(self.transformation_rule)
            formula = rule.get('formula')
            
            if formula:
                # Safe evaluation of mathematical expressions
                import ast
                import operator
                
                # Define safe operators
                safe_operators = {
                    ast.Add: operator.add,
                    ast.Sub: operator.sub,
                    ast.Mult: operator.mul,
                    ast.Div: operator.truediv,
                    ast.Pow: operator.pow,
                }
                
                def safe_eval(node):
                    if isinstance(node, ast.Num):
                        return node.n
                    elif isinstance(node, ast.Name):
                        if node.id == 'value':
                            return float(value)
                        else:
                            raise ValueError(f'Unsafe variable: {node.id}')
                    elif isinstance(node, ast.BinOp):
                        return safe_operators[type(node.op)](safe_eval(node.left), safe_eval(node.right))
                    else:
                        raise ValueError('Unsafe expression')
                
                tree = ast.parse(formula, mode='eval')
                return safe_eval(tree.body)
            
            return value
            
        except Exception as e:
            _logger.error(f'Calculation transformation error: {str(e)}')
            return value
    
    def _conditional_transform(self, value):
        """Conditional transformation"""
        if not self.conditional_expression:
            return value
        
        try:
            # Safe evaluation of conditional expression
            # This is a simplified version - in production, use a proper expression evaluator
            condition = self.conditional_expression.replace('value', str(value))
            
            # Very basic condition evaluation (for demonstration)
            if '==' in condition:
                left, right = condition.split('==')
                if eval(left.strip()) == eval(right.strip()):
                    return self._get_default_value()
            
            return value
            
        except Exception as e:
            _logger.error(f'Conditional transformation error: {str(e)}')
            return value
    
    def _custom_transform(self, value, direction):
        """Custom transformation using Python code"""
        if not self.transformation_rule:
            return value
        
        try:
            rule = json.loads(self.transformation_rule)
            code = rule.get('code')
            
            if code:
                # Create a safe execution environment
                safe_globals = {
                    'value': value,
                    'direction': direction,
                    'mapping': self,
                    'json': json,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                }
                
                # Execute the custom code
                exec(code, safe_globals)
                return safe_globals.get('result', value)
            
            return value
            
        except Exception as e:
            _logger.error(f'Custom transformation error: {str(e)}')
            return value
    
    def _get_default_value(self):
        """Get default value for the field"""
        if not self.default_value:
            return None
        
        if self.default_value_type == 'static':
            return self.default_value
        elif self.default_value_type == 'computed':
            # Execute computed default value
            try:
                return eval(self.default_value)
            except:
                return None
        elif self.default_value_type == 'field':
            # Reference to another field
            return self.default_value
        
        return None
    
    def _validate_value(self, value):
        """Validate the transformed value"""
        if not self.validation_rule:
            return True
        
        try:
            rule = json.loads(self.validation_rule)
            
            # Required field validation
            if self.is_required and (value is None or value == ''):
                raise ValidationError(self.error_message or _('Field is required'))
            
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
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            _logger.error(f'Validation error: {str(e)}')
            return True
    
    def _generate_test_data(self):
        """Generate test data for mapping validation"""
        # Generate sample data based on field type
        test_data = {}
        
        if self.field_type == 'char':
            test_data[self.external_field] = 'Test String'
        elif self.field_type == 'integer':
            test_data[self.external_field] = 123
        elif self.field_type == 'float':
            test_data[self.external_field] = 123.45
        elif self.field_type == 'boolean':
            test_data[self.external_field] = True
        elif self.field_type == 'date':
            test_data[self.external_field] = '2024-01-01'
        elif self.field_type == 'datetime':
            test_data[self.external_field] = '2024-01-01T10:00:00'
        else:
            test_data[self.external_field] = 'Test Value'
        
        return test_data
    
    def _log_test_result(self, direction, success, result):
        """Log test result"""
        self.env['connector.log'].create({
            'instance_id': self.instance_id.id,
            'level': 'info' if success else 'error',
            'message': f'Mapping test {direction}: {"Success" if success else "Failed"}',
            'operation': 'data_transformation',
            'data': json.dumps({
                'mapping_id': self.id,
                'direction': direction,
                'result': result
            })
        })
    
    def _log_mapping_error(self, error, data):
        """Log mapping error"""
        self.env['connector.log'].create({
            'instance_id': self.instance_id.id,
            'level': 'error',
            'message': f'Mapping error: {error}',
            'operation': 'data_transformation',
            'data': json.dumps({
                'mapping_id': self.id,
                'error': error,
                'data': data
            })
        })
    
    # Class Methods
    @api.model
    def get_mappings_for_model(self, instance_id, model_name, direction='import'):
        """Get all active mappings for a specific model and direction"""
        return self.search([
            ('instance_id', '=', instance_id),
            ('model_name', '=', model_name),
            ('direction', 'in', [direction, 'bidirectional']),
            ('is_active', '=', True)
        ], order='sequence')
    
    @api.model
    def apply_mappings(self, data, instance_id, model_name, direction='import'):
        """Apply all mappings for a model to transform data"""
        mappings = self.get_mappings_for_model(instance_id, model_name, direction)
        
        result = {}
        for mapping in mappings:
            try:
                mapping_result = mapping.apply_mapping(data, direction)
                result.update(mapping_result)
            except Exception as e:
                _logger.error(f'Error applying mapping {mapping.name}: {str(e)}')
                # Continue with other mappings
        
        return result
    
    # CRUD Overrides
    def create(self, vals):
        """Override create to add validation"""
        # Validate model name
        if vals.get('model_name') == 'custom' and not vals.get('custom_model_name'):
            raise ValidationError(_('Custom model name is required when model type is custom'))
        
        return super().create(vals)
    
    def write(self, vals):
        """Override write to add validation"""
        # Validate model name
        if vals.get('model_name') == 'custom' and not vals.get('custom_model_name'):
            raise ValidationError(_('Custom model name is required when model type is custom'))
        
        return super().write(vals) 