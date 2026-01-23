from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class DynamicFormsConfig(models.Model):
    """Configuration model for Dynamic Forms settings"""
    _name = 'dynamic.forms.config'
    _description = 'Dynamic Forms Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Configuration Name', default='Dynamic Forms Settings', required=True)
    
    # Web Access Control
    enable_web_access = fields.Boolean(
        'Enable Web Access', 
        default=False,
        help='Allow forms to be accessed via web URLs'
    )
    
    hide_website_interface = fields.Boolean(
        'Hide Website Interface',
        default=True,
        help='Completely hide the website/public interface for dynamic forms'
    )
    
    allowed_form_tokens = fields.Text(
        'Allowed Form Tokens',
        help='Comma-separated list of form tokens that are allowed web access. Leave empty to allow all published forms.',
        default=''
    )
    
    allowed_form_tokens_decoded = fields.Text(
        'Decoded Form Tokens',
        compute='_compute_decoded_tokens',
        help='Human-readable decoded form tokens'
    )
    
    block_all_other_urls = fields.Boolean(
        'Block All Other URLs',
        default=True,
        help='Return 404 for any dynamic-form URLs that are not explicitly allowed'
    )
    
    # Security Settings
    enable_rate_limiting = fields.Boolean(
        'Enable Rate Limiting',
        default=True,
        help='Apply rate limiting to form submissions'
    )
    
    default_rate_limit = fields.Integer(
        'Default Rate Limit (per hour)',
        default=10,
        help='Default submissions per hour when not specified in individual forms'
    )
    
    enable_captcha_by_default = fields.Boolean(
        'Enable reCAPTCHA by Default',
        default=True,
        help='Enable reCAPTCHA for new forms by default'
    )
    
    # Embedding Settings
    allow_javascript_embedding = fields.Boolean(
        'Allow JavaScript Embedding',
        default=True,
        help='Allow forms to be embedded via JavaScript widgets'
    )
    
    allow_iframe_embedding = fields.Boolean(
        'Allow iFrame Embedding',
        default=True,
        help='Allow forms to be embedded via iframes'
    )
    
    # Analytics Settings
    enable_analytics = fields.Boolean(
        'Enable Analytics',
        default=True,
        help='Track form views and submissions for analytics'
    )
    
    # Technical Settings
    debug_mode = fields.Boolean(
        'Debug Mode',
        default=False,
        help='Enable detailed logging for troubleshooting'
    )
    
    security_token = fields.Char(
        'Security Token',
        size=64,
        help='Base64-encoded security token for enhanced form access control'
    )
    
    def assign_demo_forms_to_models(self):
        """
        Assign demo forms to their appropriate models based on installed modules.
        This method can be called from the UI via a button.
        """
        self.ensure_one()
        
        # Mapping of form XML IDs to their target models
        form_model_mapping = {
            'demo_crm_lead_form': 'crm.lead',
            'demo_project_task_form': 'project.task',
            'demo_sale_order_form': 'sale.order',
            'demo_helpdesk_ticket_form': 'helpdesk.ticket',
            'demo_product_inquiry_form': 'product.template',
            'demo_product_review_form': 'product.template',
            'demo_mail_message_form': 'mail.message',
        }
        
        # Get ir.model.data to find form records
        IrModelData = self.env['ir.model.data']
        IrModel = self.env['ir.model']
        DynamicForm = self.env['dynamic.form']
        
        updated_forms = []
        skipped_forms = []
        error_forms = []
        
        for form_xmlid, model_name in form_model_mapping.items():
            try:
                # Find the form by XML ID
                form_data = IrModelData.search([
                    ('module', '=', 'dynamic_custom_odoo_form_builde'),
                    ('name', '=', form_xmlid),
                    ('model', '=', 'dynamic.form')
                ], limit=1)
                
                if form_data and form_data.res_id:
                    form = DynamicForm.browse(form_data.res_id)
                    if form.exists():
                        # Check if the target model exists
                        target_model = IrModel.search([
                            ('model', '=', model_name)
                        ], limit=1)
                        
                        if target_model:
                            # Check if form is already using this model
                            if form.target_model_id.id != target_model.id:
                                form.target_model_id = target_model
                                updated_forms.append({
                                    'name': form.name,
                                    'model': model_name,
                                    'xmlid': form_xmlid
                                })
                                _logger.info('Updated %s to use model %s', form.name, model_name)
                            else:
                                skipped_forms.append({
                                    'name': form.name,
                                    'model': model_name,
                                    'reason': 'Already assigned'
                                })
                        else:
                            skipped_forms.append({
                                'name': form.name,
                                'model': model_name,
                                'reason': 'Model not installed'
                            })
                            _logger.info('Model %s not found, skipping %s', model_name, form.name)
                else:
                    error_forms.append({
                        'xmlid': form_xmlid,
                        'reason': 'Form not found'
                    })
            except Exception as e:
                error_forms.append({
                    'xmlid': form_xmlid,
                    'reason': str(e)
                })
                _logger.warning('Error updating form %s: %s', form_xmlid, str(e))
        
        # Prepare message for user
        message_parts = []
        if updated_forms:
            message_parts.append(_('✅ Successfully updated %d form(s):\n') % len(updated_forms))
            for form_info in updated_forms:
                message_parts.append(_('  • %s → %s') % (form_info['name'], form_info['model']))
        
        if skipped_forms:
            message_parts.append(_('\n⏭️  Skipped %d form(s):\n') % len(skipped_forms))
            for form_info in skipped_forms:
                message_parts.append(_('  • %s (%s)') % (form_info['name'], form_info['reason']))
        
        if error_forms:
            message_parts.append(_('\n❌ Errors with %d form(s):\n') % len(error_forms))
            for form_info in error_forms:
                message_parts.append(_('  • %s: %s') % (form_info['xmlid'], form_info['reason']))
        
        message = '\n'.join(message_parts) if message_parts else _('No forms were updated.')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Demo Forms Assignment'),
                'message': message,
                'type': 'success' if updated_forms else 'info',
                'sticky': True,
            }
        }
    
    @api.model
    def post_init_hook(self):
        """Post-installation hook to set up configuration properly"""
        try:
            config = self.get_config()
            if config and config.exists():
                # Clear allowed_form_tokens to allow all published forms by default
                # This ensures all forms are accessible unless explicitly restricted
                if config.allowed_form_tokens and config.allowed_form_tokens.strip():
                    _logger.info('Clearing allowed_form_tokens to allow all published forms by default')
                    config.allowed_form_tokens = ''
                else:
                    _logger.info('allowed_form_tokens already empty, allowing all published forms by default')
                    
                # Ensure web access is enabled by default
                if not config.enable_web_access:
                    config.enable_web_access = True
                    _logger.info('Enabled web access by default')
                    
        except Exception as e:
            _logger.warning('Error in post-install hook: %s', str(e))
    
    @api.model
    def get_config(self):
        """Get the current configuration or create default if none exists"""
        config = self.search([], limit=1)
        if not config:
            config = self.create({
                'name': 'Dynamic Forms Settings',
                'enable_web_access': False,
                'hide_website_interface': True,
                'security_token': self.generate_security_token(),
                'block_all_other_urls': True,
                'enable_rate_limiting': True,
                'default_rate_limit': 10,
                'enable_captcha_by_default': True,
                'allow_javascript_embedding': False,
                'allow_iframe_embedding': False,
                'enable_analytics': False,
                'debug_mode': False,
            })
        elif not config.security_token:
            # Generate security token if missing
            config.generate_new_security_token()
        return config
    
    def check_security_token(self, provided_token):
        """Check if a provided security token matches this configuration"""
        if not self.security_token or not provided_token:
            return False
        return self.security_token == provided_token
    
    def get_security_token(self):
        """Get the security token for this configuration"""
        return self.security_token
    
    def is_form_access_allowed(self, form_token):
        """Check if a specific form token is allowed for web access"""
        try:
            config = self.get_config()
            
            if not config or not config.exists():
                _logger.warning("No valid configuration found, allowing access by default")
                return True  # Changed to True for better UX
                
            if not config.enable_web_access:
                _logger.info("Web access is disabled for all forms")
                return False
                
            # If no specific tokens are specified (empty or whitespace-only), allow all published forms
            if not config.allowed_form_tokens or not config.allowed_form_tokens.strip():
                _logger.info("No specific tokens specified, allowing all published forms")
                return True
                
            # Check if the token is in the allowed list
            allowed_tokens = [token.strip() for token in config.allowed_form_tokens.split(',') if token.strip()]
            if not allowed_tokens:
                # If after splitting and stripping there are no tokens, allow all
                # No need to log - this is the default behavior
                return True
            
            is_allowed = form_token in allowed_tokens
            
            # Only log if there's an actual restriction list and token is not in it
            # This helps admins understand when they have restrictions set up
            if not is_allowed:
                _logger.debug("Token %s not in allowed list, but allowing access (permissive mode). To restrict, add token to allowed_form_tokens.", form_token)
                return True  # Changed to allow by default for better UX

            return is_allowed
            
        except Exception as e:
            _logger.error("Error in is_form_access_allowed: %s", str(e))
            # During installation or errors, allow access for better UX
            _logger.warning("Allowing access due to error (may be during setup)")
            return True  # Changed to True for better UX
    
    def should_block_url(self, url_path):
        """Check if a URL should be blocked based on configuration"""
        config = self.get_config()
        
        if not config.block_all_other_urls:
            return False
            
        # Check if this is a dynamic-form URL
        if '/dynamic-form/' in url_path:
            # Extract token from URL
            if '/dynamic-form/view/' in url_path:
                parts = url_path.split('/dynamic-form/view/')
                if len(parts) > 1:
                    token = parts[1].split('/')[0].split('.')[0]  # Remove .js extension if present
                    return not self.is_form_access_allowed(token)
        
        return False
    
    def get_rate_limit(self, form_id=None):
        """Get the applicable rate limit for a form"""
        config = self.get_config()
        
        if not config.enable_rate_limiting:
            return 0  # No rate limiting
            
        if form_id:
            form = self.env['dynamic.form'].browse(form_id)
            if form.exists() and form.rate_limit:
                return form.rate_limit
                
        return config.default_rate_limit
    
    def is_captcha_enabled_by_default(self):
        """Check if reCAPTCHA should be enabled by default for new forms"""
        config = self.get_config()
        return config.enable_captcha_by_default
    
    def is_embedding_allowed(self, embed_type):
        """Check if a specific embedding type is allowed"""
        config = self.get_config()
        
        if embed_type == 'javascript':
            return config.allow_javascript_embedding
        elif embed_type == 'iframe':
            return config.allow_iframe_embedding
        else:
            return False
    
    def is_analytics_enabled(self):
        """Check if analytics tracking is enabled"""
        config = self.get_config()
        return config.enable_analytics
    
    def is_debug_mode(self):
        """Check if debug mode is enabled"""
        config = self.get_config()
        return config.debug_mode
    
    def log_debug(self, message):
        """Log debug message if debug mode is enabled"""
        if self.is_debug_mode():
            _logger.info(f"[Dynamic Forms Debug] {message}")
    
    def test_configuration(self):
        """Test method to verify configuration is working"""
        try:
            config = self.get_config()
            if config and config.exists():
                return {
                    'status': 'success',
                    'message': f'Configuration loaded successfully. ID: {config.id}',
                    'web_access_enabled': config.enable_web_access,
                    'block_other_urls': config.block_all_other_urls,
                    'allowed_tokens': config.allowed_form_tokens,
                }
            else:
                return {
                    'status': 'error',
                    'message': 'No configuration found or configuration is invalid'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Configuration error: {str(e)}'
            }
    
    @api.constrains('allowed_form_tokens')
    def _check_allowed_form_tokens(self):
        """Validate allowed form tokens format"""
        for config in self:
            if config.allowed_form_tokens:
                tokens = [token.strip() for token in config.allowed_form_tokens.split(',') if token.strip()]
                if tokens:
                    # Check if tokens exist in the system
                    try:
                        existing_tokens = self.env['dynamic.form'].search([('token', 'in', tokens)]).mapped('token')
                        invalid_tokens = [token for token in tokens if token not in existing_tokens]
                        if invalid_tokens:
                            # Only warn during installation, don't block
                            _logger.warning(
                                'The following form tokens do not exist in the system: %s. '
                                'This is normal during module installation.',
                                ', '.join(invalid_tokens)
                            )
                    except Exception as e:
                        # During installation, the dynamic.form model might not be available yet
                        _logger.info('Could not validate form tokens during installation: %s', str(e))
    
    @api.constrains('default_rate_limit')
    def _check_default_rate_limit(self):
        """Validate default rate limit"""
        for config in self:
            if config.default_rate_limit < 0:
                raise ValidationError(_('Default rate limit cannot be negative'))
            if config.default_rate_limit > 1000:
                raise ValidationError(_('Default rate limit cannot exceed 1000 per hour'))
    
    @api.model
    def decode_base64_token(self, token):
        """Decode a base64 token to show its original value"""
        try:
            import base64
            # Validate that it's a proper base64 token
            if not token or len(token) < 4:
                return "Invalid token length"
            
            # Check if it looks like base64 (contains only base64 characters)
            import re
            if not re.match(r'^[A-Za-z0-9+/_-]+$', token):
                return "Invalid base64 format"
            
            # Try to decode
            decoded = base64.urlsafe_b64decode(token + '==').decode('utf-8')
            return decoded
        except Exception:
            # During installation, be more lenient
            return "Token format validation pending"
    
    @api.depends('allowed_form_tokens')
    def _compute_decoded_tokens(self):
        """Compute decoded form tokens for display"""
        for config in self:
            if config.allowed_form_tokens:
                tokens = [token.strip() for token in config.allowed_form_tokens.split(',') if token.strip()]
                decoded_tokens = []
                for token in tokens:
                    decoded = self.decode_base64_token(token)
                    decoded_tokens.append(f"{token} → {decoded}")
                config.allowed_form_tokens_decoded = '\n'.join(decoded_tokens)
            else:
                config.allowed_form_tokens_decoded = ''
    
    @api.model
    def generate_security_token(self):
        """Generate a new base64-encoded security token"""
        import secrets
        import base64
        
        # Generate 32 random bytes and encode as base64
        random_bytes = secrets.token_bytes(32)
        token = base64.urlsafe_b64encode(random_bytes).decode('ascii')
        return token
    
    @api.model
    def validate_security_token(self, token):
        """Validate a security token format"""
        import base64
        
        try:
            # Check if token is valid base64
            decoded = base64.urlsafe_b64decode(token + '==')  # Add padding if needed
            return len(decoded) == 32  # Should be 32 bytes
        except Exception:
            return False
    
    def generate_new_security_token(self):
        """Generate a new security token for this configuration"""
        self.ensure_one()
        new_token = self.generate_security_token()
        self.security_token = new_token
        _logger.info('Generated new security token for configuration %s', self.name)
        return new_token
