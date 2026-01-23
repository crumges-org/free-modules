from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import time


class DynamicFormFieldCondition(models.Model):
    """Model to store multiple conditions for a field"""
    _name = 'dynamic.form.field.condition'
    _description = 'Dynamic Form Field Condition'
    _order = 'sequence, id'
    
    name = fields.Char('Condition Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    field_id = fields.Many2one('dynamic.form.field', 'Field', required=True, ondelete='cascade')
    condition_field_id = fields.Many2one('dynamic.form.field', 'Condition Field', required=True,
                                        domain="[('form_id', '=', parent.form_id), ('id', '!=', parent.id)]")
    operator = fields.Selection([
        ('equals', 'Equals'),
        ('not_equals', 'Not Equals'),
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('is_empty', 'Is Empty'),
        ('is_not_empty', 'Is Not Empty'),
    ], default='equals', required=True)
    value = fields.Char('Value')
    active = fields.Boolean('Active', default=True)
    
    # Computed fields for better display
    condition_field_name = fields.Char('Condition Field Name', compute='_compute_condition_field_name', store=True)
    condition_field_type = fields.Char('Condition Field Type', compute='_compute_condition_field_type', store=True)
    
    @api.depends('condition_field_id')
    def _compute_condition_field_name(self):
        for condition in self:
            if condition.condition_field_id:
                condition.condition_field_name = condition.condition_field_id.label or condition.condition_field_id.name
            else:
                condition.condition_field_name = ""
    
    @api.depends('condition_field_id')
    def _compute_condition_field_type(self):
        for condition in self:
            if condition.condition_field_id:
                field_type = condition.condition_field_id.field_type
                field_type_label = dict(condition._fields['operator'].selection).get(field_type, field_type)
                condition.condition_field_type = f"{field_type_label} ({field_type})"
            else:
                condition.condition_field_type = ""
    
    @api.constrains('field_id', 'condition_field_id', 'name')
    def _check_condition_field(self):
        for condition in self:
            if not condition.name:
                raise ValidationError(_('Condition name is required.'))
            
            if condition.field_id and condition.condition_field_id:
                if condition.field_id.id == condition.condition_field_id.id:
                    raise ValidationError(_('A field cannot be used as its own condition field.'))
                if condition.field_id.form_id != condition.condition_field_id.form_id:
                    raise ValidationError(_('Condition field must belong to the same form.'))


class DynamicFormField(models.Model):
    _name = 'dynamic.form.field'
    _description = 'Dynamic Form Field'
    _order = 'sequence, id'
    _rec_name = 'display_name'

    name = fields.Char('Field Name', required=True)
    label = fields.Char('Field Label', required=True)
    field_type = fields.Selection([
        ('text', 'Text'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('number', 'Number'),
        ('textarea', 'Text Area'),
        ('select', 'Dropdown'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkbox'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
        ('file', 'File Upload'),
        ('url', 'URL'),
        ('password', 'Password'),
        ('hidden', 'Hidden Field'),
    ], required=True, default='text')
    
    # Field Properties
    required = fields.Boolean('Required', default=False)
    readonly = fields.Boolean('Read Only', default=False)
    placeholder = fields.Char('Placeholder Text')
    help_text = fields.Text('Help Text')
    default_value = fields.Char('Default Value')
    
    # Validation
    min_length = fields.Integer('Minimum Length')
    max_length = fields.Integer('Maximum Length')
    min_value = fields.Float('Minimum Value')
    max_value = fields.Float('Maximum Value')
    pattern = fields.Char('Validation Pattern (Regex)')
    
    # Options for select/radio fields
    options = fields.Text('Options (one per line)',
                         help='For dropdown and radio fields, enter options one per line')
    
    # File upload settings
    allowed_file_types = fields.Char('Allowed File Types', 
                                   help='Comma-separated list of file extensions (e.g., .pdf,.doc,.jpg)')
    max_file_size = fields.Integer('Max File Size (MB)', default=5)
    
    # Conditional Logic
    conditional_logic = fields.Boolean('Enable Conditional Logic', default=False)
    
    # Single Condition (for backward compatibility)
    condition_field_id = fields.Many2one('dynamic.form.field', 'Condition Field',
                                        domain="[('form_id', '=', form_id), ('id', '!=', id)]")
    condition_operator = fields.Selection([
        ('equals', 'Equals'),
        ('not_equals', 'Not Equals'),
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('is_empty', 'Is Empty'),
        ('is_not_empty', 'Is Not Empty'),
    ], default='equals')
    condition_value = fields.Char('Condition Value')
    
    # Multi-Condition System
    use_multi_condition = fields.Boolean('Use Multi-Condition Logic', default=False,
                                        help="Enable to use multiple conditions with AND/OR logic")
    condition_logic_type = fields.Selection([
        ('and', 'AND (All conditions must be true)'),
        ('or', 'OR (Any condition can be true)'),
    ], default='and', string='Logic Type')
    condition_ids = fields.One2many('dynamic.form.field.condition', 'field_id', 'Conditions')
    
    # Styling
    css_class = fields.Char('CSS Class')
    width = fields.Selection([
        ('25', '25%'),
        ('50', '50%'),
        ('75', '75%'),
        ('100', '100%'),
    ], default='100')
    
    # Technical Fields
    form_id = fields.Many2one('dynamic.form', 'Form', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Computed Fields
    field_options = fields.Text('Field Options JSON', compute='_compute_field_options', store=True)
    options_count = fields.Integer('Options Count', compute='_compute_options_count', store=True)
    options_preview = fields.Text('Options Preview', compute='_compute_options_preview', store=True)
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    condition_field_type = fields.Char('Condition Field Type', compute='_compute_condition_field_type', store=True)
    
    @api.depends('label', 'field_type', 'required')
    def _compute_display_name(self):
        """Compute display name showing label, type, and required status"""
        for field in self:
            display_parts = [field.label or field.name]
            
            # Add field type
            field_type_label = dict(field._fields['field_type'].selection).get(field.field_type, field.field_type)
            display_parts.append(f"({field_type_label})")
            
            # Add required indicator
            if field.required:
                display_parts.append("(Required)")
            
            field.display_name = " ".join(display_parts)
    
    @api.depends('options')
    def _compute_field_options(self):
        for field in self:
            if field.options:
                options_list = [opt.strip() for opt in field.options.split('\n') if opt.strip()]
                field.field_options = json.dumps(options_list)
            else:
                field.field_options = '[]'
    
    @api.depends('options')
    def _compute_options_count(self):
        for field in self:
            if field.options:
                options_list = [opt.strip() for opt in field.options.split('\n') if opt.strip()]
                field.options_count = len(options_list)
            else:
                field.options_count = 0
    
    @api.depends('options')
    def _compute_options_preview(self):
        for field in self:
            if field.options:
                options_list = [opt.strip() for opt in field.options.split('\n') if opt.strip()]
                if options_list:
                    preview = ', '.join(options_list[:3])  # Show first 3 options
                    if len(options_list) > 3:
                        preview += f' (+{len(options_list) - 3} more)'
                    field.options_preview = preview
                else:
                    field.options_preview = ''
            else:
                field.options_preview = ''
    
    @api.depends('condition_field_id')
    def _compute_condition_field_type(self):
        """Compute the type of the condition field for better user guidance"""
        for field in self:
            if field.condition_field_id:
                field_type = field.condition_field_id.field_type
                field_type_label = dict(field._fields['field_type'].selection).get(field_type, field_type)
                field.condition_field_type = f"{field_type_label} ({field_type})"
            else:
                field.condition_field_type = ""
    
    @api.constrains('min_length', 'max_length')
    def _check_length_constraints(self):
        for field in self:
            if field.min_length and field.max_length and field.min_length > field.max_length:
                raise ValidationError(_('Minimum length cannot be greater than maximum length.'))
    
    @api.constrains('field_type', 'options')
    def _check_options_for_field_type(self):
        for field in self:
            if field.field_type in ['select', 'radio', 'checkbox']:
                if not field.options or not field.options.strip():
                    raise ValidationError(_('Options are required for %s fields. Please enter at least one option.') % field.field_type)
                
                options_list = [opt.strip() for opt in field.options.split('\n') if opt.strip()]
                if not options_list:
                    raise ValidationError(_('At least one option is required for %s fields.') % field.field_type)
    
    def action_configure_options(self):
        """Open options configuration for this field"""
        self.ensure_one()
        
        return {
            'name': f'Configure Options for {self.label}',
            'type': 'ir.actions.act_window',
            'res_model': 'dynamic.form.field',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_id': self.id,
                'form_view_ref': 'dynamic_custom_odoo_form_builde.view_dynamic_form_field_form',
            }
        }
    
    @api.constrains('min_value', 'max_value')
    def _check_value_constraints(self):
        for field in self:
            if field.min_value and field.max_value and field.min_value > field.max_value:
                raise ValidationError(_('Minimum value cannot be greater than maximum value.'))
    
    @api.model_create_multi
    def create(self, vals_list):
        """Ensure name is set when creating fields"""
        for vals in vals_list:
            if not vals.get('name'):
                # Generate a unique name based on form and sequence
                form_id = vals.get('form_id')
                if form_id:
                    # Count existing fields for this form
                    existing_count = self.search_count([('form_id', '=', form_id)])
                    vals['name'] = f"field_{existing_count + 1}"
                else:
                    # Fallback to timestamp
                    vals['name'] = f"field_{int(time.time())}"
        return super().create(vals_list)

    @api.constrains('conditional_logic', 'condition_field_id', 'use_multi_condition', 'condition_ids')
    def _check_conditional_logic(self):
        for field in self:
            if field.conditional_logic:
                # Check multi-condition logic
                if field.use_multi_condition:
                    if not field.condition_ids:
                        raise ValidationError(_('At least one condition is required when multi-condition logic is enabled.'))
                    
                    # Check if any condition uses the field itself
                    for condition in field.condition_ids:
                        if condition.condition_field_id and condition.condition_field_id.id == field.id:
                            raise ValidationError(_('A field cannot be used as its own condition field.'))
                
                # Check single condition logic
                else:
                    if not field.condition_field_id:
                        raise ValidationError(_('Condition field is required when conditional logic is enabled.'))
                    if field.condition_field_id and field.condition_field_id.id == field.id:
                        raise ValidationError(_('A field cannot be used as its own condition field.'))
    
    @api.onchange('field_type')
    def _onchange_field_type(self):
        """Reset field-specific properties when field type changes"""
        if self.field_type not in ['select', 'radio']:
            self.options = False
        if self.field_type != 'file':
            self.allowed_file_types = False
            self.max_file_size = False
        if self.field_type not in ['number']:
            self.min_value = False
            self.max_value = False
    
    @api.onchange('conditional_logic')
    def _onchange_conditional_logic(self):
        """Update condition field domain when conditional logic is enabled/disabled"""
        if self.conditional_logic:
            # Return domain to exclude current field
            return {
                'domain': {
                    'condition_field_id': [('form_id', '=', self.form_id.id), ('id', '!=', self.id)]
                }
            }
        else:
            # Clear condition field when conditional logic is disabled
            self.condition_field_id = False
            self.use_multi_condition = False
            self.condition_ids = [(5, 0, 0)]  # Clear all conditions
            self.condition_operator = False
            self.condition_value = False
    
    @api.onchange('use_multi_condition')
    def _onchange_use_multi_condition(self):
        """Handle multi-condition toggle"""
        if self.use_multi_condition:
            # Clear single condition fields when switching to multi-condition
            self.condition_field_id = False
            self.condition_operator = False
            self.condition_value = False
        else:
            # Clear multi-conditions when switching to single condition
            self.condition_ids = [(5, 0, 0)]
            self.condition_logic_type = 'and'
    
    def get_validation_rules(self):
        """Get validation rules for the field"""
        rules = {
            'required': self.required,
            'field_type': self.field_type,
        }
        
        if self.min_length:
            rules['min_length'] = self.min_length
        if self.max_length:
            rules['max_length'] = self.max_length
        if self.min_value is not False:
            rules['min_value'] = self.min_value
        if self.max_value is not False:
            rules['max_value'] = self.max_value
        if self.pattern:
            rules['pattern'] = self.pattern
        if self.field_type == 'file':
            if self.allowed_file_types:
                rules['allowed_types'] = [t.strip() for t in self.allowed_file_types.split(',')]
            if self.max_file_size:
                rules['max_size'] = self.max_file_size * 1024 * 1024  # Convert to bytes
        
        return rules
    
    def get_conditional_logic(self):
        """Get conditional logic for the field"""
        if not self.conditional_logic:
            return None
        
        # Use multi-condition system if enabled
        if self.use_multi_condition and self.condition_ids:
            conditions = []
            for condition in self.condition_ids.filtered(lambda c: c.active):
                conditions.append({
                    'name': condition.name,
                    'condition_field_id': condition.condition_field_id.id,
                    'condition_field_name': condition.condition_field_id.name,
                    'operator': condition.operator,
                    'value': condition.value,
                })
            
            return {
                'logic_type': self.condition_logic_type,
                'conditions': conditions,
            }
        
        # Fallback to single condition
        elif self.condition_field_id:
            return {
                'field_id': self.condition_field_id.id,
                'operator': self.condition_operator,
                'value': self.condition_value,
            }
        
        return None
    
    def get_field_config(self):
        """Get complete field configuration for frontend rendering"""
        config = {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'type': self.field_type,
            'required': self.required,
            'readonly': self.readonly,
            'placeholder': self.placeholder,
            'help_text': self.help_text,
            'default_value': self.default_value,
            'css_class': self.css_class,
            'width': self.width,
            'validation_rules': self.get_validation_rules(),
            'conditional_logic': self.get_conditional_logic(),
        }
        
        if self.field_type in ['select', 'radio']:
            config['options'] = json.loads(self.field_options)
        
        return config
    
    def copy(self, default=None):
        """Override copy to ensure unique field names"""
        default = default or {}
        if 'name' not in default:
            default['name'] = f"{self.name}_copy"
        return super().copy(default)
