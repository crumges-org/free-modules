from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class DynamicFormFieldMapping(models.Model):
    _name = 'dynamic.form.field.mapping'
    _description = 'Dynamic Form Field Mapping'
    _order = 'sequence, id'

    form_id = fields.Many2one('dynamic.form', 'Form', required=True, ondelete='cascade', 
                               default=lambda self: self.env.context.get('default_form_id'))
    form_field_id = fields.Many2one('dynamic.form.field', 'Form Field', required=True, ondelete='cascade')
    form_field_label = fields.Char('Form Field Label', compute='_compute_form_field_label', store=True)
    model_field = fields.Selection(selection='_get_model_field_selection', string='Model Field', required=True)
    model_field_label = fields.Char('Model Field Label', compute='_compute_model_field_label', store=True)
    field_type_compatibility = fields.Char('Field Type Compatibility', compute='_compute_field_type_compatibility', store=True)
    label_field = fields.Boolean('Use as Label Field', default=False, 
                                help='Use this field value as the label for the created record')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)

    @api.depends('form_field_id')
    def _compute_form_field_label(self):
        """Compute form field label for display"""
        for mapping in self:
            if mapping.form_field_id:
                mapping.form_field_label = mapping.form_field_id.label or mapping.form_field_id.name
            else:
                mapping.form_field_label = ""
    
    @api.depends('model_field', 'form_id.target_model_id')
    def _compute_model_field_label(self):
        for mapping in self:
            if mapping.model_field and mapping.form_id.target_model_id:
                try:
                    target_model = self.env[mapping.form_id.target_model_id.model]
                    field = target_model._fields.get(mapping.model_field)
                    if field:
                        mapping.model_field_label = field.string or mapping.model_field
                    else:
                        mapping.model_field_label = mapping.model_field
                except Exception:
                    mapping.model_field_label = mapping.model_field
            else:
                mapping.model_field_label = mapping.model_field
    
    @api.depends('form_field_id', 'model_field', 'form_id.target_model_id')
    def _compute_field_type_compatibility(self):
        for mapping in self:
            if mapping.form_field_id and mapping.model_field and mapping.form_id.target_model_id:
                try:
                    target_model = self.env[mapping.form_id.target_model_id.model]
                    model_field = target_model._fields.get(mapping.model_field)
                    
                    if model_field:
                        form_field_type = mapping.form_field_id.field_type
                        model_field_type = model_field.type
                        
                        if self._are_field_types_compatible(form_field_type, model_field_type):
                            mapping.field_type_compatibility = f"✓ {form_field_type} → {model_field_type}"
                        else:
                            mapping.field_type_compatibility = f"✗ {form_field_type} → {model_field_type} (Incompatible)"
                    else:
                        mapping.field_type_compatibility = "Unknown model field"
                except Exception:
                    mapping.field_type_compatibility = "Error checking compatibility"
            else:
                mapping.field_type_compatibility = ""

    @api.constrains('form_field_id', 'model_field')
    def _check_unique_mapping(self):
        for mapping in self:
            # Check for duplicate mappings
            duplicate = self.search([
                ('form_id', '=', mapping.form_id.id),
                ('form_field_id', '=', mapping.form_field_id.id),
                ('id', '!=', mapping.id)
            ])
            if duplicate:
                raise ValidationError(_('Duplicate mapping for field "%s"') % mapping.form_field_id.label)
    
    @api.constrains('label_field', 'form_id')
    def _check_label_field_unique(self):
        for mapping in self:
            if mapping.label_field:
                # Check if another mapping in the same form is already set as label field
                other_label_mappings = self.search([
                    ('form_id', '=', mapping.form_id.id),
                    ('label_field', '=', True),
                    ('id', '!=', mapping.id)
                ])
                if other_label_mappings:
                    raise ValidationError(_('Only one field can be used as label field per form. Field "%s" is already set as label field.') % other_label_mappings[0].form_field_id.label)
    
    @api.constrains('form_field_id', 'model_field')
    def _check_field_type_compatibility(self):
        """Check if form field type is compatible with model field type"""
        for mapping in self:
            if mapping.form_field_id and mapping.model_field and mapping.form_id.target_model_id:
                try:
                    target_model = self.env[mapping.form_id.target_model_id.model]
                    model_field = target_model._fields.get(mapping.model_field)
                    
                    if not model_field:
                        continue
                    
                    form_field_type = mapping.form_field_id.field_type
                    model_field_type = model_field.type
                    
                    # Check compatibility
                    if not self._are_field_types_compatible(form_field_type, model_field_type):
                        raise ValidationError(_(
                            'Field type mismatch: Form field "%s" (type: %s) cannot be mapped to model field "%s" (type: %s). '
                            'Please select a compatible field type.'
                        ) % (mapping.form_field_id.label, form_field_type, mapping.model_field, model_field_type))
                        
                except Exception as e:
                    _logger.warning("Error checking field type compatibility: %s", str(e))
    
    def _are_field_types_compatible(self, form_field_type, model_field_type):
        """Check if form field type is compatible with model field type"""
        compatibility_map = {
            # Text fields
            'text': ['char', 'text', 'html'],
            'textarea': ['char', 'text', 'html'],
            'email': ['char', 'text'],
            'phone': ['char', 'text'],
            
            # Number fields
            'number': ['integer', 'float', 'monetary'],
            'integer': ['integer', 'float', 'monetary'],
            'float': ['integer', 'float', 'monetary'],
            
            # Date fields
            'date': ['date', 'datetime'],
            'datetime': ['date', 'datetime'],
            
            # Boolean fields
            'checkbox': ['boolean'],
            'radio': ['char', 'text', 'selection'],
            'select': ['char', 'text', 'selection'],
            
            # File fields
            'file': ['binary'],  # many2one for ir.attachment
            
            # Special cases
            'url': ['char', 'text'],
            'password': ['char', 'text'],
        }
        
        # Get compatible model field types for this form field type
        compatible_types = compatibility_map.get(form_field_type, [])
        
        # Check if model field type is compatible
        return model_field_type in compatible_types


    
    @api.model
    def _get_model_field_selection(self):
        """Get selection options for model field based on form's target model"""
        # This method is called by Odoo's Selection field mechanism
        # Try to get form_id from context (set when creating/editing a mapping)
        form_id = (
            self.env.context.get('default_form_id') or 
            self.env.context.get('form_id') or 
            self.env.context.get('active_id')
        )
        
        # If we have an active_id, check if it's a form_id
        if not form_id and self.env.context.get('active_model') == 'dynamic.form':
            form_id = self.env.context.get('active_id')
        
        # If still no form_id, try to get from parent form_id in context
        if not form_id:
            # Check if we're in a form view with a parent form_id
            parent_form_id = self.env.context.get('parent_form_id')
            if parent_form_id:
                form_id = parent_form_id
        
        # Try to get form_id from the record if we're in a record context
        # This happens when the field is rendered in a form view
        if not form_id and hasattr(self, '_ids') and self._ids:
            try:
                record = self.browse(self._ids[0])
                if record.form_id:
                    form_id = record.form_id.id
            except Exception:
                pass
        
        # Try to get form_id from the current record being created/edited
        # This is important for one2many tree views where record might not be saved yet
        if not form_id:
            try:
                # Check if we're in a recordset context (when creating new records)
                if hasattr(self, 'form_id') and self.form_id:
                    form_id = self.form_id.id
            except Exception:
                pass
        
        # Try to get from active record if we're in a one2many context
        if not form_id:
            try:
                # When in one2many tree view, parent record ID might be in context
                if self.env.context.get('default_form_id'):
                    form_id = self.env.context.get('default_form_id')
            except Exception:
                pass
        
        if not form_id:
            # Return placeholder if no form_id available
            # The selection will be populated when form_id is set via onchange
            return [('', 'Please select a Form first')]
        
        try:
            form = self.env['dynamic.form'].browse(form_id)
            if not form.exists() or not form.target_model_id:
                return [('', 'Please set Target Model for the form')]
            
            target_model = self.env[form.target_model_id.model]
            selection_options = []
            
            for field_name, field in target_model._fields.items():
                # Skip technical fields
                if field_name in ['id', 'create_date', 'write_date', 'create_uid', 'write_uid', '__last_update']:
                    continue
                
                # Skip relational fields (they require special handling)
                if field.type in ['many2one', 'many2many', 'one2many', 'one2one']:
                    continue
                
                field_label = f"{field.string or field_name} ({field_name})"
                if field.required:
                    field_label += " *"
                field_label += f" - {field.type}"
                
                selection_options.append((field_name, field_label))
            
            # Sort by field name for better UX
            selection_options.sort(key=lambda x: x[0])
            
            if not selection_options:
                return [('', 'No compatible fields found in target model')]
            
            return selection_options
        except Exception as e:
            _logger.warning("Error getting model field selection: %s", str(e))
            return [('', f'Error loading fields: {str(e)}')]
    
    def get_available_model_fields(self, form_field_type=None):
        """Get available fields for the target model, optionally filtered by form field type"""
        if not self.form_id.target_model_id:
            return []
        
        try:
            target_model = self.env[self.form_id.target_model_id.model]
            available_fields = []
            
            for field_name, field in target_model._fields.items():
                # Skip technical fields
                if field_name in ['id', 'create_date', 'write_date', 'create_uid', 'write_uid', '__last_update']:
                    continue
                
                # Skip relational fields
                if field.type in ['many2one', 'many2many', 'one2many', 'one2one']:
                    continue
                
                # If form field type is specified, check compatibility
                if form_field_type and not self._are_field_types_compatible(form_field_type, field.type):
                    continue
                
                available_fields.append({
                    'name': field_name,
                    'string': field.string or field_name,
                    'type': field.type,
                    'required': field.required,
                })
            
            return available_fields
        except Exception:
            return []
    
    @api.onchange('form_id')
    def _onchange_form_id(self):
        """Update form field and model field selection when form changes"""
        if self.form_id:
            # Clear current selections
            self.form_field_id = False
            self.model_field = False
            
            # Set domain for form field selection
            domain = {
                'form_field_id': [('form_id', '=', self.form_id.id), ('active', '=', True)]
            }
            
            # Update context to include form_id so selection field can access it
            # This helps the Selection field method get the form_id
            return {
                'domain': domain,
                'context': {
                    **self.env.context,
                    'default_form_id': self.form_id.id,
                    'form_id': self.form_id.id,
                }
            }
    
    @api.onchange('form_field_id')
    def _onchange_form_field_id(self):
        """Update model field selection when form field changes"""
        if self.form_field_id and self.form_id.target_model_id:
            # Clear current model field selection
            self.model_field = False
            
            # Get available model fields filtered by form field type
            form_field_type = self.form_field_id.field_type
            available_fields = self.get_available_model_fields(form_field_type)
            
            if not available_fields:
                return {
                    'warning': {
                        'title': _('No Compatible Fields'),
                        'message': _('No compatible model fields found for form field "%s" (type: %s). Please check the target model.') % (
                            self.form_field_id.label, form_field_type
                        )
                    }
                }
            
            return {
                'warning': {
                    'title': _('Field Type Compatibility'),
                    'message': _('Only compatible field types are shown for "%s" (type: %s). %d compatible field(s) available.') % (
                        self.form_field_id.label, form_field_type, len(available_fields)
                    )
                }
            }
