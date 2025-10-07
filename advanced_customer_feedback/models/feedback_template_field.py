from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FeedbackTemplateField(models.Model):
    _name = 'feedback.template.field'
    _description = 'Feedback Template Field'
    _order = 'sequence, id'

    template_id = fields.Many2one('feedback.template', string='Template', required=True, ondelete='cascade')
    name = fields.Char(string='Field Name', required=True)
    field_type = fields.Selection([
        ('text', 'Text'),
        ('textarea', 'Text Area'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('select', 'Selection'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkbox'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
    ], string='Field Type', required=True, default='text')
    required = fields.Boolean(string='Required', default=False)
    sequence = fields.Integer(string='Sequence', default=10)
    help_text = fields.Text(string='Help Text')
    selection_options = fields.Text(string='Selection Options', 
                                   help='Enter options one per line for selection fields')
    default_value = fields.Char(string='Default Value')
    validation_regex = fields.Char(string='Validation Regex', 
                                 help='Regular expression for field validation')
    
    @api.constrains('field_type', 'selection_options')
    def _check_selection_options(self):
        for field in self:
            if field.field_type in ['select', 'radio'] and not field.selection_options:
                raise ValidationError(_('Selection options are required for %s field type.') % field.field_type)
    
    @api.constrains('validation_regex')
    def _check_validation_regex(self):
        for field in self:
            if field.validation_regex:
                try:
                    import re
                    re.compile(field.validation_regex)
                except re.error:
                    raise ValidationError(_('Invalid regular expression: %s') % field.validation_regex)
    
    def get_selection_list(self):
        """Return selection options as a list"""
        if self.field_type in ['select', 'radio'] and self.selection_options:
            return [line.strip() for line in self.selection_options.split('\n') if line.strip()]
        return []
    
    def validate_field_value(self, value):
        """Validate field value based on field type and constraints"""
        if self.required and not value:
            raise ValidationError(_('Field %s is required.') % self.name)
        
        if value and self.validation_regex:
            import re
            if not re.match(self.validation_regex, str(value)):
                raise ValidationError(_('Field %s does not match the required format.') % self.name)
        
        if value and self.field_type == 'email':
            if '@' not in value or '.' not in value:
                raise ValidationError(_('Please enter a valid email address.'))
        
        if value and self.field_type == 'number':
            try:
                float(value)
            except ValueError:
                raise ValidationError(_('Please enter a valid number.'))
        
        if value and self.field_type in ['select', 'radio']:
            options = self.get_selection_list()
            if value not in options:
                raise ValidationError(_('Please select a valid option.'))
        
        return True
