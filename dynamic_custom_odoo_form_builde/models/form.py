from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import uuid
import logging

_logger = logging.getLogger(__name__)


class DynamicForm(models.Model):
    _name = 'dynamic.form'
    _description = 'Dynamic Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Form Name', required=True, tracking=True)
    description = fields.Text('Description')
    active = fields.Boolean('Active', compute='_compute_active', store=True, inverse='_inverse_active')
    
    # Form Configuration
    target_model_id = fields.Many2one('ir.model', 'Target Model', required=True, tracking=True,
                                     help='Odoo model where form submissions will be stored',
                                     ondelete='cascade')
    model_name = fields.Char('Model Name', compute='_compute_model_name', store=True)
    
    # Embedding Configuration
    embed_type = fields.Selection([
        ('javascript', 'JavaScript Widget'),
        ('iframe', 'iFrame'),
    ], default='javascript', required=True, tracking=True)
    
    embed_code = fields.Text('Embed Code', compute='_compute_embed_code', store=True)
    public_url = fields.Char('Public URL', compute='_compute_public_url', store=True)
    
    # Styling Configuration
    theme = fields.Selection([
        ('light', 'Light Theme'),
        ('dark', 'Dark Theme'),
        ('blue', 'Blue Theme'),
        ('green', 'Green Theme'),
        ('purple', 'Purple Theme'),
        ('orange', 'Orange Theme'),
        ('custom', 'Custom CSS'),
    ], default='light', required=True)
    
    layout = fields.Selection([
        ('standard', 'Standard Layout'),
        ('card', 'Card Layout'),
        ('minimal', 'Minimal Layout'),
        ('split', 'Split Layout'),
        ('wizard', 'Wizard/Step Layout'),
        ('inline', 'Inline Layout'),
        ('grid', 'Grid Layout (2 Columns)'),
        ('sidebar', 'Sidebar Layout'),
        ('tabbed', 'Tabbed Layout'),
        ('accordion', 'Accordion Layout'),
        ('compact', 'Compact Layout'),
        ('modern', 'Modern Layout'),
    ], default='standard', required=True, string='Form Layout',
    help='Choose the layout style for your form')
    
    position = fields.Selection([
        ('center', 'Center'),
        ('left', 'Left Sidebar'),
        ('right', 'Right Sidebar'),
        ('full', 'Full Width'),
        ('modal', 'Modal Popup'),
    ], default='center', required=True)
    
    header_layout = fields.Selection([
        ('centered', 'Centered (Logo Above)'),
        ('split', 'Split (Logo Left, Content Right)'),
        ('split-reverse', 'Split Reverse (Content Left, Logo Right)'),
        ('inline', 'Inline (Logo, Title, Description in Row)'),
        ('stacked', 'Stacked (All Elements Stacked)'),
        ('minimal', 'Minimal (Title Only with Border)'),
        ('banner', 'Banner (Large Banner Style)'),
        ('compact', 'Compact (Logo and Title Side by Side)'),
    ], default='centered', string='Header Layout',
    help='Choose the structural layout style for the form header')
    
    hide_header = fields.Boolean('Hide Header', default=False,
                                help='Hide the form header (title, description, and logo)')
    
    custom_css = fields.Text('Custom CSS')
    logo = fields.Binary('Logo')
    primary_color = fields.Char('Primary Color', default='#007bff')
    secondary_color = fields.Char('Secondary Color', default='#6c757d')
    background_style = fields.Selection([
        ('gradient', 'Gradient (Theme Default)'),
        ('solid', 'Solid Color'),
        ('image', 'Background Image'),
        ('pattern', 'Pattern'),
    ], default='gradient', string='Background Style',
    help='Choose how the form background should be styled')
    background_color = fields.Char('Background Color', 
                                 help='Solid background color (e.g., #ffffff or rgba(255,255,255,1))')
    background_gradient = fields.Text('Background Gradient',
                                     help='Custom CSS gradient (e.g., linear-gradient(135deg, #667eea 0%, #764ba2 100%))')
    background_image = fields.Binary('Background Image',
                                     help='Upload a background image for the form')
    background_image_url = fields.Char('Background Image URL',
                                      help='Or provide a URL to a background image')
    
    # Form Settings
    show_progress_bar = fields.Boolean('Show Progress Bar', default=True)
    show_submit_button = fields.Boolean('Show Submit Button', default=True)
    submit_button_text = fields.Char('Submit Button Text', default='Submit')
    success_message = fields.Text('Success Message', default='Thank you! Your submission has been received.')
    error_message = fields.Text('Error Message', default='An error occurred. Please try again.')
    
    # Security Settings
    enable_captcha = fields.Boolean('Enable reCAPTCHA', default=True)
    captcha_site_key = fields.Char('reCAPTCHA Site Key')
    captcha_secret_key = fields.Char('reCAPTCHA Secret Key')
    rate_limit = fields.Integer('Rate Limit (submissions per hour)', default=10)
    
    # Email Notification Settings
    enable_email_notifications = fields.Boolean('Enable Email Notifications', default=False)
    admin_email = fields.Char('Admin Email', help='Email address to receive form submissions')
    send_confirmation_email = fields.Boolean('Send Confirmation Email to User', default=False)
    user_email_field_id = fields.Many2one('dynamic.form.field', 'User Email Field', 
                                         domain="[('form_id', '=', id), ('field_type', '=', 'email')]",
                                         help='Form field containing user email address for confirmation emails')
    confirmation_email_template_id = fields.Many2one('mail.template', 'Confirmation Email Template', 
                                                    domain=[('model', '=', 'dynamic.form.submission')])
    notification_email_template_id = fields.Many2one('mail.template', 'Admin Notification Template', 
                                                    domain=[('model', '=', 'dynamic.form.submission')])
    
    # Analytics & Status
    view_count = fields.Integer('View Count', default=0)
    submission_count = fields.Integer('Submission Count', default=0)
    conversion_rate = fields.Float('Conversion Rate (%)', compute='_compute_conversion_rate', store=False)
    field_count = fields.Integer('Field Count', compute='_compute_field_count', store=True)
    mapping_count = fields.Integer('Mapping Count', compute='_compute_mapping_count', store=True)
    active_field_count = fields.Integer('Active Fields', compute='_compute_active_field_count', store=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready to Publish'),
        ('published', 'Published'),
    ], string='Status', compute='_compute_status', store=True)
    is_ready = fields.Boolean('Ready to Publish', compute='_compute_is_ready', store=True)
    last_submission_date = fields.Datetime('Last Submission', compute='_compute_last_submission_date', store=True)
    
    # Relationships
    field_ids = fields.One2many('dynamic.form.field', 'form_id', 'Form Fields')
    submission_ids = fields.One2many('dynamic.form.submission', 'form_id', 'Submissions')
    field_mapping_ids = fields.One2many('dynamic.form.field.mapping', 'form_id', 'Field Mappings')
    email_notification_ids = fields.One2many('dynamic.form.email.notification', 'form_id', 'Email Notifications')
    
    # Technical Fields
    token = fields.Char('Security Token', default=lambda self: str(uuid.uuid4()), copy=False)
    security_token = fields.Char('Enhanced Security Token', size=64, copy=False,
                                help='Base64-encoded security token for enhanced form access control')
    is_published = fields.Boolean('Published', default=False, tracking=True)
    
    @api.depends('embed_type', 'token')
    def _compute_embed_code(self):
        for form in self:
            if form.token:
                base_url = self._get_base_url()
                if form.embed_type == 'javascript':
                    form.embed_code = f'''<script src="{base_url}/dynamic-form/view/{form.token}.js"></script>'''
                else:
                    form.embed_code = f'''<iframe src="{base_url}/dynamic-form/view/{form.token}" width="100%" height="600" frameborder="0"></iframe>'''
    
    @api.depends('token')
    def _compute_public_url(self):
        for form in self:
            if form.token:
                # Try to get base URL from current request first
                base_url = self._get_base_url()
                form.public_url = f"{base_url}/dynamic-form/view/{form.token}"
    
    def _get_base_url(self):
        """Get the base URL dynamically"""
        # Try to get from current request
        try:
            from odoo.http import request
            if request and hasattr(request, 'httprequest'):
                return request.httprequest.url_root.rstrip('/')
        except Exception:
            pass
        
        # Fallback to system parameter
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if not base_url:
            # Default fallback
            base_url = 'http://localhost:8003'
        
        return base_url.rstrip('/')
    
    def refresh_urls(self):
        """Refresh public URL and embed code with current domain"""
        for form in self:
            form._compute_public_url()
            form._compute_embed_code()
    
    def get_available_model_fields(self):
        """Get available fields for the target model as selection options"""
        self.ensure_one()
        if not self.target_model_id:
            return []
        
        try:
            target_model = self.env[self.target_model_id.model]
            available_fields = []
            
            for field_name, field in target_model._fields.items():
                # Skip technical fields
                if field_name in ['id', 'create_date', 'write_date', 'create_uid', 'write_uid']:
                    continue
                
                field_label = f"{field.string or field_name} ({field_name})"
                if field.required:
                    field_label += " *"
                
                available_fields.append((field_name, field_label))
            
            return available_fields
        except Exception:
            return []
    
    def action_configure_options(self):
        """Open options configuration wizard for fields that need options"""
        self.ensure_one()
        
        # Get fields that need options
        fields_needing_options = self.field_ids.filtered(
            lambda f: f.field_type in ['select', 'radio', 'checkbox'] and not f.options
        )
        
        if not fields_needing_options:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Fields Need Options',
                    'message': 'All dropdown, radio, and checkbox fields already have options configured.',
                    'type': 'info',
                }
            }
        
        # Create wizard action
        return {
            'name': 'Configure Field Options',
            'type': 'ir.actions.act_window',
            'res_model': 'dynamic.form.field.options.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_form_id': self.id,
                'default_field_ids': [(6, 0, fields_needing_options.ids)],
            }
        }
    
    def action_validate_field_mappings(self):
        """Validate all field mappings and show results"""
        self.ensure_one()
        
        if not self.field_mapping_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Field Mappings',
                    'message': 'No field mappings to validate.',
                    'type': 'info',
                }
            }
        
        incompatible_mappings = []
        compatible_mappings = []
        
        for mapping in self.field_mapping_ids:
            if mapping.form_field_id and mapping.model_field and self.target_model_id:
                try:
                    target_model = self.env[self.target_model_id.model]
                    model_field = target_model._fields.get(mapping.model_field)
                    
                    if model_field:
                        form_field_type = mapping.form_field_id.field_type
                        model_field_type = model_field.type
                        
                        if mapping._are_field_types_compatible(form_field_type, model_field_type):
                            compatible_mappings.append({
                                'form_field': mapping.form_field_id.label,
                                'form_type': form_field_type,
                                'model_field': mapping.model_field,
                                'model_type': model_field_type
                            })
                        else:
                            incompatible_mappings.append({
                                'form_field': mapping.form_field_id.label,
                                'form_type': form_field_type,
                                'model_field': mapping.model_field,
                                'model_type': model_field_type
                            })
                except Exception as e:
                    _logger.warning("Error validating field mapping: %s", str(e))
        
        # Prepare message
        message_parts = []
        
        if compatible_mappings:
            message_parts.append("✅ Compatible Mappings:")
            for mapping in compatible_mappings:
                message_parts.append(f"  • {mapping['form_field']} ({mapping['form_type']}) → {mapping['model_field']} ({mapping['model_type']})")
        
        if incompatible_mappings:
            message_parts.append("\n❌ Incompatible Mappings:")
            for mapping in incompatible_mappings:
                message_parts.append(f"  • {mapping['form_field']} ({mapping['form_type']}) → {mapping['model_field']} ({mapping['model_type']})")
        
        if not compatible_mappings and not incompatible_mappings:
            message_parts.append("No field mappings to validate.")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Field Mapping Validation Results',
                'message': '\n'.join(message_parts),
                'type': 'warning' if incompatible_mappings else 'success',
            }
        }
    
    @api.depends('target_model_id')
    def _compute_model_name(self):
        """Compute model name from target_model_id"""
        for form in self:
            if form.target_model_id:
                # Access the model field directly from the ir.model record
                form.model_name = form.target_model_id.model
            else:
                form.model_name = False
    
    @api.depends('view_count', 'submission_count')
    def _compute_conversion_rate(self):
        for form in self:
            if form.view_count > 0:
                form.conversion_rate = round((form.submission_count / form.view_count) * 100, 2)
            else:
                form.conversion_rate = 0.0
    
    @api.depends('is_published')
    def _compute_active(self):
        """Make active field sync with is_published - they represent the same thing"""
        for form in self:
            form.active = form.is_published
    
    def _inverse_active(self):
        """When active is set, update is_published to match"""
        for form in self:
            form.is_published = form.active
    
    @api.depends('field_ids')
    def _compute_field_count(self):
        for form in self:
            form.field_count = len(form.field_ids)
    
    @api.depends('field_ids', 'field_ids.active')
    def _compute_active_field_count(self):
        for form in self:
            form.active_field_count = len(form.field_ids.filtered(lambda f: f.active))
    
    @api.depends('field_mapping_ids')
    def _compute_mapping_count(self):
        for form in self:
            form.mapping_count = len(form.field_mapping_ids.filtered(lambda m: m.active))
    
    @api.depends('is_published', 'field_ids', 'field_mapping_ids', 'target_model_id')
    def _compute_status(self):
        for form in self:
            if form.is_published:
                form.status = 'published'
            elif form._is_ready_to_publish():
                form.status = 'ready'
            else:
                form.status = 'draft'
    
    @api.depends('is_published', 'field_ids', 'field_mapping_ids', 'target_model_id')
    def _compute_is_ready(self):
        for form in self:
            form.is_ready = form._is_ready_to_publish()
    
    @api.depends('submission_ids', 'submission_ids.create_date')
    def _compute_last_submission_date(self):
        for form in self:
            if form.submission_ids:
                form.last_submission_date = max(form.submission_ids.mapped('create_date'))
            else:
                form.last_submission_date = False
    
    def _is_ready_to_publish(self):
        """Check if form is ready to be published"""
        self.ensure_one()
        # Form must have at least one field
        if not self.field_ids or not self.active_field_count:
            return False
        # Form must have target model
        if not self.target_model_id:
            return False
        # Form should have at least one field mapping (optional but recommended)
        # We'll make this optional for now
        return True
    
    @api.constrains('field_mapping_ids')
    def _check_field_mapping_compatibility(self):
        """Check field type compatibility for all field mappings when form is saved"""
        for form in self:
            if form.field_mapping_ids:
                incompatible_mappings = []
                
                for mapping in form.field_mapping_ids:
                    if mapping.form_field_id and mapping.model_field and form.target_model_id:
                        try:
                            target_model = self.env[form.target_model_id.model]
                            model_field = target_model._fields.get(mapping.model_field)
                            
                            if model_field:
                                form_field_type = mapping.form_field_id.field_type
                                model_field_type = model_field.type
                                
                                # Check compatibility using the field mapping model's method
                                if not mapping._are_field_types_compatible(form_field_type, model_field_type):
                                    incompatible_mappings.append({
                                        'form_field': mapping.form_field_id.label,
                                        'form_type': form_field_type,
                                        'model_field': mapping.model_field,
                                        'model_type': model_field_type
                                    })
                        except Exception as e:
                            _logger.warning("Error checking field mapping compatibility: %s", str(e))
                
                if incompatible_mappings:
                    error_messages = []
                    for mapping in incompatible_mappings:
                        error_messages.append(
                            f"• Form field '{mapping['form_field']}' (type: {mapping['form_type']}) "
                            f"cannot be mapped to model field '{mapping['model_field']}' (type: {mapping['model_type']})"
                        )
                    
                    raise ValidationError(_(
                        "Field Type Compatibility Errors:\n\n%s\n\n"
                        "Please fix these field mappings before saving the form."
                    ) % "\n".join(error_messages))
    
    @api.constrains('field_ids')
    def _check_fields(self):
        for form in self:
            if not form.field_ids:
                raise ValidationError(_('At least one field is required for the form.'))
    

    
    def action_preview(self):
        """Open form preview in new window"""
        return {
            'type': 'ir.actions.act_url',
            'url': self.public_url,
            'target': 'new',
        }
    
    def action_view_submissions(self):
        """View form submissions"""
        return {
            'name': _('Form Submissions'),
            'type': 'ir.actions.act_window',
            'res_model': 'dynamic.form.submission',
            'view_mode': 'list,form',
            'domain': [('form_id', '=', self.id)],
            'context': {'default_form_id': self.id},
        }
    
    def action_duplicate(self):
        """Duplicate the form"""
        self.ensure_one()
        new_form = self.copy({
            'name': f"{self.name} (Copy)",
            'token': str(uuid.uuid4()),
            'is_published': False,
        })
        
        # Duplicate fields
        for field in self.field_ids:
            field.copy({
                'form_id': new_form.id,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dynamic.form',
            'res_id': new_form.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_publish(self):
        """Publish the form"""
        self.ensure_one()
        if not self.field_ids:
            raise ValidationError(_('Cannot publish form without fields.'))
        
        self.is_published = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Form has been published successfully.'),
                'type': 'success',
            }
        }
    
    def action_unpublish(self):
        """Unpublish the form"""
        self.ensure_one()
        self.is_published = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Form has been unpublished.'),
                'type': 'success',
            }
        }
    
    def increment_view_count(self):
        """Increment view count for analytics"""
        self.ensure_one()
        self.view_count += 1
    
    def increment_submission_count(self):
        """Increment submission count for analytics"""
        self.ensure_one()
        self.submission_count += 1

    @api.model
    def generate_security_token(self):
        """Generate a new base64-encoded security token"""
        import secrets
        import base64
        
        # Generate 32 random bytes and encode as base64
        random_bytes = secrets.token_bytes(32)
        token = base64.urlsafe_b64encode(random_bytes).decode('ascii')
        return token
    
    def generate_new_security_token(self):
        """Generate a new security token for this form"""
        self.ensure_one()
        new_token = self.generate_security_token()
        self.security_token = new_token
        _logger.info('Generated new security token for form %s', self.name)
        return new_token
    
    def check_security_token(self, provided_token):
        """Check if a provided security token matches this form"""
        if not self.security_token or not provided_token:
            return False
        return self.security_token == provided_token
    
    @api.model_create_multi
    def create(self, vals_list):
        """Create new forms with security tokens"""
        for vals in vals_list:
            if 'security_token' not in vals:
                vals['security_token'] = self.generate_security_token()
        return super().create(vals_list)
    
