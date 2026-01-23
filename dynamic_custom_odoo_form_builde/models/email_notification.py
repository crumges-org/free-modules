from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DynamicFormEmailNotification(models.Model):
    _name = 'dynamic.form.email.notification'
    _description = 'Dynamic Form Email Notification'
    _order = 'sequence, id'

    name = fields.Char('Notification Name', required=True)
    form_id = fields.Many2one('dynamic.form', 'Form', required=True, ondelete='cascade')
    
    # Trigger Settings
    trigger_type = fields.Selection([
        ('on_submission', 'On Form Submission'),
        ('on_field_value', 'On Specific Field Value'),
        ('on_condition', 'On Custom Condition'),
    ], default='on_submission', required=True)
    
    # Field-based trigger
    trigger_field_id = fields.Many2one('dynamic.form.field', 'Trigger Field')
    trigger_value = fields.Char('Trigger Value', help='Value that triggers this email')
    trigger_operator = fields.Selection([
        ('equals', 'Equals'),
        ('contains', 'Contains'),
        ('not_equals', 'Not Equals'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
    ], default='equals')
    
    # Email Settings
    email_type = fields.Selection([
        ('admin_notification', 'Admin Notification'),
        ('user_confirmation', 'User Confirmation'),
        ('custom_recipient', 'Custom Recipient'),
    ], default='admin_notification', required=True)
    
    recipient_email = fields.Char('Recipient Email', 
                                 help='Email address for custom recipient notifications')
    recipient_field_id = fields.Many2one('dynamic.form.field', 'Recipient Field', 
                                        domain="[('field_type', '=', 'email')]",
                                        help='Form field containing recipient email')
    
    # Template Settings
    email_template_id = fields.Many2one('mail.template', 'Email Template', 
                                       domain="[('model', '=', 'dynamic.form.submission')]",
                                       required=True)
    
    # Additional Settings
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    description = fields.Text('Description')
    
    @api.constrains('trigger_type', 'trigger_field_id', 'trigger_value')
    def _check_trigger_configuration(self):
        for notification in self:
            if notification.trigger_type == 'on_field_value':
                if not notification.trigger_field_id:
                    raise ValidationError(_('Trigger field is required when trigger type is "On Specific Field Value"'))
                if not notification.trigger_value:
                    raise ValidationError(_('Trigger value is required when trigger type is "On Specific Field Value"'))
    
    @api.constrains('email_type', 'recipient_email', 'recipient_field_id')
    def _check_recipient_configuration(self):
        for notification in self:
            if notification.email_type == 'custom_recipient':
                if not notification.recipient_email and not notification.recipient_field_id:
                    raise ValidationError(_('Either recipient email or recipient field must be specified for custom recipient notifications'))
    
    @api.constrains('trigger_field_id', 'recipient_field_id', 'form_id')
    def _check_field_belongs_to_form(self):
        for notification in self:
            if notification.trigger_field_id and notification.trigger_field_id.form_id != notification.form_id:
                raise ValidationError(_('Trigger field must belong to the same form'))
            if notification.recipient_field_id and notification.recipient_field_id.form_id != notification.form_id:
                raise ValidationError(_('Recipient field must belong to the same form'))
            if notification.recipient_field_id and notification.recipient_field_id.field_type != 'email':
                raise ValidationError(_('Recipient field must be an email field'))
    
    def should_send_notification(self, submission_data):
        """Check if notification should be sent based on trigger conditions"""
        self.ensure_one()
        
        if self.trigger_type == 'on_submission':
            return True
        
        elif self.trigger_type == 'on_field_value':
            if not self.trigger_field_id or not self.trigger_value:
                return False
            
            field_value = submission_data.get(self.trigger_field_id.name, '')
            
            if self.trigger_operator == 'equals':
                return str(field_value) == str(self.trigger_value)
            elif self.trigger_operator == 'contains':
                return str(self.trigger_value) in str(field_value)
            elif self.trigger_operator == 'not_equals':
                return str(field_value) != str(self.trigger_value)
            elif self.trigger_operator == 'greater_than':
                try:
                    return float(field_value) > float(self.trigger_value)
                except (ValueError, TypeError):
                    return False
            elif self.trigger_operator == 'less_than':
                try:
                    return float(field_value) < float(self.trigger_value)
                except (ValueError, TypeError):
                    return False
        
        elif self.trigger_type == 'on_condition':
            # Custom condition logic can be extended here
            return True
        
        return False
    
    def get_recipient_email(self, submission_data):
        """Get recipient email based on notification configuration"""
        self.ensure_one()
        
        if self.email_type == 'admin_notification':
            return self.form_id.admin_email
        
        elif self.email_type == 'user_confirmation':
            # Try to find email field in submission data
            for field_name, value in submission_data.items():
                if 'email' in field_name.lower() and '@' in str(value):
                    return value
            return None
        
        elif self.email_type == 'custom_recipient':
            if self.recipient_field_id:
                return submission_data.get(self.recipient_field_id.name)
            else:
                return self.recipient_email
        
        return None
    
    def get_available_form_fields(self):
        """Get available form fields for this notification"""
        self.ensure_one()
        return self.form_id.field_ids
    
    def get_available_email_fields(self):
        """Get available email fields for this notification"""
        self.ensure_one()
        return self.form_id.field_ids.filtered(lambda f: f.field_type == 'email')
    
    def send_notification(self, submission):
        """Send email notification"""
        self.ensure_one()
        
        try:
            # Get submission data
            import json
            submission_data = json.loads(submission.form_data)
            
            # Check if notification should be sent
            if not self.should_send_notification(submission_data):
                return False
            
            # Get recipient email
            recipient_email = self.get_recipient_email(submission_data)
            if not recipient_email:
                return False
            
            # Send email using template
            self.email_template_id.send_mail(
                submission.id,
                force_send=True,
                email_values={
                    'email_to': recipient_email,
                    'email_from': self.env.company.email or self.env.user.email,
                }
            )
            
            return True
            
        except Exception as e:
            _logger.error(f"Error sending email notification {self.name}: {str(e)}")
            return False
