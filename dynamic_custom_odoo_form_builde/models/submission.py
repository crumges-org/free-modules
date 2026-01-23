from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError, UserError
import json
import base64
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class DynamicFormSubmission(models.Model):
    _name = 'dynamic.form.submission'
    _description = 'Dynamic Form Submission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Submission ID', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    form_id = fields.Many2one('dynamic.form', 'Form', required=True, ondelete='cascade')
    form_name = fields.Char(related='form_id.name', store=True)
    
    # Submission Data
    form_data = fields.Text('Form Data (JSON)', required=True)
    parsed_data = fields.Html('Parsed Data', compute='_compute_parsed_data', store=True)
    formatted_json_data = fields.Text('Formatted JSON Data', compute='_compute_formatted_json_data', store=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('processed', 'Processed'),
        ('error', 'Error'),
    ], default='draft', tracking=True)
    
    # Target Record
    target_model = fields.Char(related='form_id.model_name', store=True)
    target_record_id = fields.Integer('Target Record ID')
    target_record_name = fields.Char('Target Record Name')
    
    # Metadata
    ip_address = fields.Char('IP Address')
    user_agent = fields.Char('User Agent')
    referrer = fields.Char('Referrer URL')
    session_id = fields.Char('Session ID')
    
    # File Attachments
    attachment_ids = fields.Many2many('ir.attachment', 'dynamic_form_submission_attachment_rel',
                                     'submission_id', 'attachment_id', 'Attachments')
    
    # Processing
    processing_error = fields.Text('Processing Error')
    processed_date = fields.Datetime('Processed Date')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('dynamic.form.submission') or _('New')
        return super().create(vals_list)
    
    @api.model
    def create_from_form_data(self, form_id, form_data, metadata=None):
        """Create a submission from form data"""
        metadata = metadata or {}
        
        # Convert form data to JSON string
        form_data_json = json.dumps(form_data)
        
        # Create submission record
        submission_vals = {
            'form_id': form_id,
            'form_data': form_data_json,
            'state': 'submitted',
            'ip_address': metadata.get('ip_address'),
            'user_agent': metadata.get('user_agent'),
            'referrer': metadata.get('referrer'),
            'session_id': metadata.get('session_id'),
        }
        
        return self.create(submission_vals)
    
    @api.depends('form_data')
    def _compute_parsed_data(self):
        for submission in self:
            try:
                if submission.form_data:
                    data = json.loads(submission.form_data)
                    # Format the data as HTML table for better display
                    html_parts = ['<div style="font-family: Arial, sans-serif; max-width: 100%; overflow-x: auto;">']
                    html_parts.append('<table style="border-collapse: collapse; width: 100%; margin: 10px 0; border: 1px solid #dee2e6; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">')
                    
                    # Table header
                    html_parts.append('<thead>')
                    html_parts.append('<tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">')
                    html_parts.append('<th style="border: 1px solid #dee2e6; padding: 12px 15px; text-align: left; font-weight: 600; font-size: 14px;">Field Name</th>')
                    html_parts.append('<th style="border: 1px solid #dee2e6; padding: 12px 15px; text-align: left; font-weight: 600; font-size: 14px;">Value</th>')
                    html_parts.append('</tr>')
                    html_parts.append('</thead>')
                    
                    # Table body
                    html_parts.append('<tbody>')
                    
                    for field_name, value in data.items():
                        field = submission.form_id.field_ids.filtered(lambda f: f.name == field_name)
                        field_label = field.label if field else field_name
                        
                        # Handle different value types
                        if isinstance(value, dict):
                            # Handle file uploads
                            if 'name' in value and 'data' in value:
                                display_value = f"📎 {value['name']} ({value['type']}, {self._format_file_size(value.get('size', 0))})"
                            else:
                                display_value = str(value)
                        elif isinstance(value, bool):
                            display_value = "✅ Yes" if value else "❌ No"
                        elif value is None or value == "":
                            display_value = "<em style='color: #6c757d;'>Not provided</em>"
                        else:
                            display_value = str(value)
                        
                        # Add row with alternating colors
                        html_parts.append('<tr style="background-color: #ffffff;">')
                        html_parts.append(f'<td style="border: 1px solid #dee2e6; padding: 10px 15px; font-weight: 500; color: #495057; font-size: 13px;">{field_label}</td>')
                        html_parts.append(f'<td style="border: 1px solid #dee2e6; padding: 10px 15px; color: #212529; font-size: 13px;">{display_value}</td>')
                        html_parts.append('</tr>')
                    
                    html_parts.append('</tbody>')
                    html_parts.append('</table>')
                    
                    # Add summary
                    html_parts.append(f'<div style="margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; border-left: 4px solid #007bff;">')
                    html_parts.append(f'<strong>Total Fields:</strong> {len(data)} | ')
                    html_parts.append(f'<strong>Submission ID:</strong> {submission.name} | ')
                    html_parts.append(f'<strong>Date:</strong> {submission.create_date.strftime("%Y-%m-%d %H:%M:%S") if submission.create_date else "N/A"}')
                    html_parts.append('</div>')
                    
                    html_parts.append('</div>')
                    
                    submission.parsed_data = ''.join(html_parts)
                else:
                    submission.parsed_data = '<div style="padding: 20px; text-align: center; color: #6c757d;"><em>No form data available</em></div>'
            except (json.JSONDecodeError, TypeError) as e:
                submission.parsed_data = f'<div style="padding: 20px; text-align: center; color: #dc3545;"><strong>Error parsing form data:</strong> {str(e)}</div>'
    
    @api.depends('form_data')
    def _compute_formatted_json_data(self):
        """Compute formatted JSON data for better display"""
        for submission in self:
            try:
                if submission.form_data:
                    # Parse and re-format JSON with proper indentation
                    data = json.loads(submission.form_data)
                    submission.formatted_json_data = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
                else:
                    submission.formatted_json_data = ""
            except (json.JSONDecodeError, TypeError) as e:
                submission.formatted_json_data = f"Error parsing JSON: {str(e)}"
    
    def get_field_value(self, field_name):
        """Get value of a specific form field by name"""
        self.ensure_one()
        try:
            if self.form_data:
                data = json.loads(self.form_data)
                return data.get(field_name, '')
            return ''
        except (json.JSONDecodeError, TypeError):
            return ''
    
    def get_field_label(self, field_name):
        """Get label of a specific form field by name"""
        self.ensure_one()
        field = self.form_id.field_ids.filtered(lambda f: f.name == field_name)
        return field.label if field else field_name
    
    def get_all_field_values(self):
        """Get all form field values as a dictionary with labels"""
        self.ensure_one()
        try:
            if self.form_data:
                data = json.loads(self.form_data)
                result = {}
                for field_name, value in data.items():
                    field = self.form_id.field_ids.filtered(lambda f: f.name == field_name)
                    field_label = field.label if field else field_name
                    result[field_label] = value
                return result
            return {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def get_formatted_data_html(self):
        """Get formatted form data as HTML for email templates"""
        self.ensure_one()
        try:
            if self.form_data:
                data = json.loads(self.form_data)
                html_parts = ['<div style="font-family: Arial, sans-serif;">']
                html_parts.append('<table style="border-collapse: collapse; width: 100%; margin: 10px 0; border: 1px solid #dee2e6; border-radius: 4px; overflow: hidden;">')
                
                # Table header
                html_parts.append('<thead>')
                html_parts.append('<tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">')
                html_parts.append('<th style="border: 1px solid #dee2e6; padding: 12px 15px; text-align: left; font-weight: 600; font-size: 14px;">Field Name</th>')
                html_parts.append('<th style="border: 1px solid #dee2e6; padding: 12px 15px; text-align: left; font-weight: 600; font-size: 14px;">Value</th>')
                html_parts.append('</tr>')
                html_parts.append('</thead>')
                
                # Table body
                html_parts.append('<tbody>')
                
                for field_name, value in data.items():
                    field = self.form_id.field_ids.filtered(lambda f: f.name == field_name)
                    field_label = field.label if field else field_name
                    
                    # Handle different value types
                    if isinstance(value, dict):
                        # Handle file uploads
                        if 'name' in value and 'data' in value:
                            display_value = f"📎 {value['name']} ({value['type']}, {self._format_file_size(value.get('size', 0))})"
                        else:
                            display_value = str(value)
                    elif isinstance(value, bool):
                        display_value = "✅ Yes" if value else "❌ No"
                    elif value is None or value == "":
                        display_value = "<em style='color: #6c757d;'>Not provided</em>"
                    else:
                        display_value = str(value)
                    
                    # Add row with alternating colors
                    html_parts.append('<tr style="background-color: #ffffff;">')
                    html_parts.append(f'<td style="border: 1px solid #dee2e6; padding: 10px 15px; font-weight: 500; color: #495057; font-size: 13px;">{field_label}</td>')
                    html_parts.append(f'<td style="border: 1px solid #dee2e6; padding: 10px 15px; color: #212529; font-size: 13px;">{display_value}</td>')
                    html_parts.append('</tr>')
                
                html_parts.append('</tbody>')
                html_parts.append('</table>')
                
                # Add summary
                html_parts.append(f'<div style="margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; border-left: 4px solid #007bff;">')
                html_parts.append(f'<strong>Total Fields:</strong> {len(data)} | ')
                html_parts.append(f'<strong>Submission ID:</strong> {self.name} | ')
                html_parts.append(f'<strong>Date:</strong> {self.create_date.strftime("%Y-%m-%d %H:%M:%S") if self.create_date else "N/A"}')
                html_parts.append('</div>')
                
                html_parts.append('</div>')
                return ''.join(html_parts)
            return '<div style="padding: 20px; text-align: center; color: #6c757d;"><em>No form data available</em></div>'
        except (json.JSONDecodeError, TypeError) as e:
            return f'<div style="padding: 20px; text-align: center; color: #dc3545;"><strong>Error parsing form data:</strong> {str(e)}</div>'
    
    def action_process_submission(self):
        """Process the submission and create/update target record"""
        self.ensure_one()
        
        # Send email notifications
        self.send_email_notifications()
        
        try:
            # Parse form data
            form_data = json.loads(self.form_data)
            
            # Check if there are any active field mappings
            active_mappings = self.form_id.field_mapping_ids.filtered(lambda m: m.active)
            
            # If no active mappings exist, skip model creation but mark as processed
            if not active_mappings:
                _logger.info("No active field mappings found for form '%s'. Skipping model entry creation.", self.form_id.name)
                self.write({
                    'state': 'processed',
                    'processed_date': fields.Datetime.now(),
                    'processing_error': False,
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Submission received successfully. No model entry created as no field mappings are configured.'),
                        'type': 'success',
                    }
                }
            
            # Get target model
            if not self.target_model:
                raise ValidationError(_('No target model specified for this form.'))
            
            try:
                target_model = self.env[self.target_model]
            except KeyError:
                raise ValidationError(_('Target model "%s" not found or not accessible.') % self.target_model)
            
            # Prepare record values
            record_values = self._prepare_record_values(form_data)
            _logger.info("Prepared record values: %s", record_values)
            
            # Only create/update if we have at least one mapped field value
            if not record_values:
                _logger.info("No mapped field values found. Skipping model entry creation.")
                self.write({
                    'state': 'processed',
                    'processed_date': fields.Datetime.now(),
                    'processing_error': False,
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Submission received successfully. No model entry created as no mapped field values were found.'),
                        'type': 'success',
                    }
                }
            
            # Create or update target record
            target_record = None
            try:
                if self.target_record_id:
                    # Update existing record
                    target_record = target_model.browse(self.target_record_id)
                    target_record.write(record_values)
                    self.target_record_name = target_record.display_name
                else:
                    # Create new record
                    target_record = target_model.create(record_values)
                    self.target_record_id = target_record.id
                    self.target_record_name = target_record.display_name
                
                # Update submission status to processed
                self.write({
                    'state': 'processed',
                    'processed_date': fields.Datetime.now(),
                    'processing_error': False,
                })
                
                # Send notifications if configured
                if target_record:
                    self._send_notifications(target_record)
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Submission processed successfully.'),
                        'type': 'success',
                    }
                }
                
            except Exception as target_error:
                _logger.error("Error creating/updating target record: %s", str(target_error))
                _logger.error("Record values: %s", record_values)
                
                # Update submission status to error but don't raise exception
                self.write({
                    'state': 'error',
                    'processing_error': f'Error creating target record: {str(target_error)}',
                    'processed_date': fields.Datetime.now(),
                })
                
                # Still send email notifications for the submission
                self.send_email_notifications()
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Warning'),
                        'message': _('Submission received but there was an error creating the target record. Please check the submission details.'),
                        'type': 'warning',
                    }
                }
            
        except Exception as e:
            _logger.error("Error processing submission: %s", str(e))
            import traceback
            _logger.error("Full traceback: %s", traceback.format_exc())
            
            # Update submission state to error
            # Use sudo() to ensure we can write even if there are permission issues
            try:
                self.sudo().write({
                    'state': 'error',
                    'processing_error': str(e),
                    'processed_date': fields.Datetime.now(),
                })
                # Flush to ensure the state is saved in the current transaction
                self.env.flush_all()
            except Exception as write_error:
                _logger.error("Error updating submission state: %s", str(write_error))
            
            # Still send email notifications even if processing fails
            try:
                self.send_email_notifications()
            except Exception as email_error:
                _logger.error("Error sending email notifications: %s", str(email_error))
            
            # Don't raise ValidationError - let the caller handle it
            # This allows HTTP controllers to return proper JSON responses
            # Instead, we'll return None to indicate failure
            return None
    
    def _prepare_record_values(self, form_data):
        """Prepare values for target record creation/update"""
        record_values = {}
        label_value = None
        
        # Get target model to check required fields
        target_model = self.env[self.target_model]
        
        for field_name, value in form_data.items():
            # Find corresponding field in form
            field = self.form_id.field_ids.filtered(lambda f: f.name == field_name)
            if not field:
                continue
            
            # Handle file uploads first (create attachments regardless of mapping)
            if field.field_type == 'file' and value:
                _logger.info("Processing file upload for field '%s' (label: '%s')", field.name, field.label)
                attachment_id = self._handle_file_upload(value)
                if attachment_id:
                    _logger.info("Created attachment with ID %s for field '%s'", attachment_id, field.name)
                else:
                    _logger.warning("Failed to create attachment for field '%s'", field.name)
            
            # Map form field to model field
            model_field = self._get_model_field_mapping(field)
            if model_field:
                # Double-check that the field exists and is compatible
                if model_field not in target_model._fields:
                    _logger.warning("Model field '%s' does not exist in target model '%s'", model_field, self.target_model)
                    continue
                
                target_field = target_model._fields[model_field]
                # Verify type compatibility one more time
                if not self._is_field_type_compatible(field.field_type, target_field.type):
                    _logger.warning("Field type mismatch: form field '%s' (type: %s) cannot be mapped to model field '%s' (type: %s). Skipping.",
                                  field.label, field.field_type, model_field, target_field.type)
                    continue
                
                # Skip relational fields - they require special handling
                if target_field.type in ['many2one', 'many2many', 'one2many', 'one2one']:
                    _logger.warning("Skipping relational field '%s' (type: %s) - requires manual mapping or special handling.",
                                  model_field, target_field.type)
                    continue
                
                # Convert value based on field type with target model info
                try:
                    converted_value = self._convert_field_value(field, value, target_model, model_field)
                    if converted_value is not None and converted_value is not False:
                        # Additional validation for monetary fields
                        if target_field.type == 'monetary' and isinstance(converted_value, str):
                            # Try to extract numeric value from strings like "$5,000 - $10,000"
                            import re
                            numbers = re.findall(r'[\d,]+', converted_value.replace('$', '').replace(',', ''))
                            if numbers:
                                try:
                                    # Take the first number found
                                    converted_value = float(numbers[0])
                                except (ValueError, TypeError):
                                    _logger.warning("Could not extract numeric value from '%s' for monetary field '%s'. Skipping.",
                                                  value, model_field)
                                    continue
                            else:
                                _logger.warning("No numeric value found in '%s' for monetary field '%s'. Skipping.",
                                              value, model_field)
                                continue
                        
                        record_values[model_field] = converted_value
                        
                        # Check if this field is marked as label field
                        mapping = self.form_id.field_mapping_ids.filtered(
                            lambda m: m.form_field_id.id == field.id and m.active and m.label_field
                        )
                        if mapping:
                            label_value = converted_value
                            _logger.info("Using field '%s' (label: '%s') as label field with value: %s", 
                                        field.name, field.label, label_value)
                        
                        _logger.info("Mapped field '%s' (label: '%s') to model field '%s' with value: %s", 
                                    field.name, field.label, model_field, converted_value)
                except Exception as conv_error:
                    _logger.error("Error converting value '%s' for field '%s' to model field '%s': %s. Skipping this field.",
                                value, field.label, model_field, str(conv_error))
                    import traceback
                    _logger.error("Traceback: %s", traceback.format_exc())
                    continue
            else:
                _logger.warning("No mapping found for field '%s' (label: '%s')", field.name, field.label)
        
        # Set the name field using the label field value if available
        if label_value and 'name' in target_model._fields:
            record_values['name'] = str(label_value)
            _logger.info("Set record name to: %s", label_value)
        
        # If name field is required but not set, try to find a suitable value
        if 'name' in target_model._fields:
            name_field = target_model._fields['name']
            if name_field.required and 'name' not in record_values:
                # Try to find a suitable value from form data
                name_candidates = []
                
                # Priority 1: Check if there's a form field named "name"
                name_field_obj = self.form_id.field_ids.filtered(lambda f: f.name == 'name')
                if name_field_obj and 'name' in form_data:
                    name_candidates.append(form_data['name'])
                
                # Priority 2: Check for common name-like fields
                for field_name in ['contact_name', 'company_name', 'first_name', 'title', 'subject']:
                    if field_name in record_values:
                        name_candidates.append(str(record_values[field_name]))
                
                # Priority 3: Use the first text field value
                if not name_candidates:
                    for field_name, value in form_data.items():
                        if value and isinstance(value, str) and value.strip():
                            field = self.form_id.field_ids.filtered(lambda f: f.name == field_name)
                            if field and field.field_type in ['text', 'textarea', 'email', 'phone']:
                                name_candidates.append(value)
                                break
                
                # Set name if we found a candidate
                if name_candidates:
                    record_values['name'] = str(name_candidates[0]).strip()
                    _logger.info("Set record name from fallback to: %s", record_values['name'])
                else:
                    # Last resort: use a default name
                    record_values['name'] = f"Form Submission {self.name or 'New'}"
                    _logger.info("Set record name to default: %s", record_values['name'])
        
        # Add default values for required fields that are not provided
        record_values = self._add_default_values(record_values, target_model)
        
        return record_values
    
    def _add_default_values(self, record_values, target_model):
        """Add default values for required fields that are not provided"""
        # Common default values for different models
        default_values = {
            'account.analytic.account': {
                'plan_id': self._get_default_analytic_plan(),
            },
            'res.partner': {
                'is_company': False,
            },
            'crm.lead': {
                'type': 'lead',
            },
            'hr.applicant': {
                'stage_id': self._get_default_applicant_stage(),
            },
        }
        
        # Get defaults for this model
        model_defaults = default_values.get(self.target_model, {})
        
        # Add defaults for required fields that are not already set
        for field_name, default_value in model_defaults.items():
            if field_name not in record_values and hasattr(target_model, field_name):
                field = target_model._fields.get(field_name)
                if field and field.required:
                    record_values[field_name] = default_value
                    _logger.info("Added default value for required field '%s': %s", field_name, default_value)
        
        return record_values
    
    def _get_default_analytic_plan(self):
        """Get default analytic plan for account.analytic.account"""
        try:
            # Try to find the first available plan
            plan = self.env['account.analytic.plan'].search([], limit=1)
            if plan:
                return plan.id
            else:
                # If no plan exists, create a default one
                plan = self.env['account.analytic.plan'].create({
                    'name': 'Default Plan',
                    'description': 'Default analytic plan for dynamic forms',
                })
                return plan.id
        except Exception as e:
            _logger.error("Error getting default analytic plan: %s", str(e))
            return False
    
    def _get_default_applicant_stage(self):
        """Get default stage for hr.applicant"""
        try:
            # Try to find the first stage
            stage = self.env['hr.recruitment.stage'].search([], limit=1)
            if stage:
                return stage.id
            else:
                return False
        except Exception as e:
            _logger.error("Error getting default applicant stage: %s", str(e))
            return False
    
    def _get_model_field_mapping(self, field):
        """Get the corresponding model field name for the form field"""
        # Only use manual mappings - no automatic mapping fallback
        # This ensures we only create model entries when mappings are explicitly defined
        mapping = self.form_id.field_mapping_ids.filtered(
            lambda m: m.form_field_id.id == field.id and m.active
        )
        if mapping:
            _logger.info("Found manual mapping: form field '%s' (label: '%s') -> model field '%s'", 
                       field.name, field.label, mapping[0].model_field)
            return mapping[0].model_field
        
        # No mapping found - return None to skip this field
        _logger.debug("No mapping found for form field '%s' (label: '%s') - skipping", 
                     field.name, field.label)
        return None
    
    def _is_field_type_compatible(self, form_field_type, model_field_type):
        """Check if form field type is compatible with model field type"""
        # Never allow mapping to relational fields (many2one, many2many, one2many, one2one)
        # These require special handling and should be mapped manually
        relational_types = ['many2one', 'many2many', 'one2many', 'one2one']
        if model_field_type in relational_types:
            return False
        
        compatibility_map = {
            # Text fields
            'text': ['char', 'text', 'html'],
            'textarea': ['char', 'text', 'html'],
            'email': ['char', 'text'],
            'phone': ['char', 'text'],
            
            # Number fields
            'number': ['integer', 'float', 'monetary'],
            
            # Date fields
            'date': ['date', 'datetime'],
            'datetime': ['date', 'datetime'],
            
            # Boolean fields
            'checkbox': ['boolean'],
            'radio': ['char', 'text', 'selection'],
            'select': ['char', 'text', 'selection'],
            
            # File fields
            'file': ['binary'],
            
            # Special cases
            'url': ['char', 'text'],
            'password': ['char', 'text'],
        }
        
        # Get compatible model field types for this form field type
        compatible_types = compatibility_map.get(form_field_type, [])
        
        # Check if model field type is compatible
        return model_field_type in compatible_types
    
    def _convert_field_value(self, field, value, target_model=None, model_field=None):
        """Convert form field value to appropriate type for model field"""
        if not value:
            return False
        
        # If we have target model and model field info, use it for better conversion
        if target_model and model_field and hasattr(target_model, '_fields') and model_field in target_model._fields:
            target_field = target_model._fields[model_field]
            target_field_type = target_field.type
            
            try:
                if target_field_type == 'integer':
                    return int(value) if value else 0
                elif target_field_type == 'float':
                    return float(value) if value else 0.0
                elif target_field_type == 'boolean':
                    return bool(value)
                elif target_field_type == 'date':
                    return fields.Date.from_string(value) if value else False
                elif target_field_type == 'datetime':
                    return fields.Datetime.from_string(value) if value else False
                elif target_field_type == 'many2one':
                    # For many2one fields, try to find the record by name
                    if value and hasattr(target_field, 'comodel_name'):
                        comodel = self.env[target_field.comodel_name]
                        # Try to find by name field
                        record = comodel.search([('name', '=', value)], limit=1)
                        return record.id if record else False
                    return False
                else:
                    # For other types (char, text, etc.), return as string
                    return str(value) if value else ''
            except (ValueError, TypeError) as e:
                _logger.warning("Error converting value '%s' for field '%s' to type '%s': %s", 
                               value, model_field, target_field_type, str(e))
                # Return a safe default value based on field type
                if target_field_type == 'integer':
                    return 0
                elif target_field_type == 'float':
                    return 0.0
                elif target_field_type == 'boolean':
                    return False
                elif target_field_type in ['date', 'datetime']:
                    return False
                else:
                    return str(value) if value else ''
        
        # Fallback to form field type conversion
        if field.field_type == 'number':
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        elif field.field_type == 'date':
            try:
                return fields.Date.from_string(value)
            except (ValueError, TypeError):
                return False
        elif field.field_type == 'datetime':
            try:
                return fields.Datetime.from_string(value)
            except (ValueError, TypeError):
                return False
        elif field.field_type == 'checkbox':
            return bool(value)
        elif field.field_type == 'file':
            # For file fields, if they're mapped to a model field, return the file name or attachment ID
            if isinstance(value, dict) and 'name' in value:
                return value['name']  # Return file name for model field
            elif isinstance(value, str):
                return value  # Return string value as is
            else:
                return False
        else:
            return str(value)
    
    def _handle_file_upload(self, file_data):
        """Handle file upload data and create attachment"""
        _logger.info("Handling file upload with data type: %s", type(file_data))
        if isinstance(file_data, dict):
            _logger.info("File data keys: %s", list(file_data.keys()))
        
        try:
            if isinstance(file_data, dict):
                # Handle file data from form submission
                if 'name' in file_data and 'data' in file_data:
                    _logger.info("Creating attachment with name: %s, data length: %s", 
                                file_data['name'], len(file_data['data']) if file_data['data'] else 0)
                    
                    # Create attachment
                    attachment = self.env['ir.attachment'].create({
                        'name': file_data['name'],
                        'datas': file_data['data'],
                        'res_model': 'dynamic.form.submission',
                        'res_id': self.id,
                        'public': False,
                    })
                    
                    # Add to submission attachments
                    self.attachment_ids = [(4, attachment.id)]
                    
                    _logger.info("Created attachment '%s' (ID: %s) for submission %s", 
                                file_data['name'], attachment.id, self.name)
                    return attachment.id
                    
                elif 'attachment_id' in file_data:
                    # File was already uploaded via separate endpoint
                    attachment_id = int(file_data['attachment_id'])
                    attachment = self.env['ir.attachment'].browse(attachment_id)
                    if attachment.exists():
                        # Update attachment to link to this submission
                        attachment.write({
                            'res_model': 'dynamic.form.submission',
                            'res_id': self.id,
                        })
                        
                        # Add to submission attachments
                        self.attachment_ids = [(4, attachment.id)]
                        
                        _logger.info("Linked attachment %s to submission %s", attachment.name, self.name)
                        return attachment.id
                        
            elif isinstance(file_data, str) and file_data.startswith('data:'):
                # Handle base64 data URL
                import base64
                import re
                
                # Extract file data from data URL
                match = re.match(r'data:([^;]+);base64,(.+)', file_data)
                if match:
                    mime_type = match.group(1)
                    base64_data = match.group(2)
                    
                    # Determine file extension from MIME type
                    file_extension = self._get_file_extension_from_mime_type(mime_type)
                    filename = f"uploaded_file{file_extension}"
                    
                    # Create attachment
                    attachment = self.env['ir.attachment'].create({
                        'name': filename,
                        'datas': base64_data,
                        'mimetype': mime_type,
                        'res_model': 'dynamic.form.submission',
                        'res_id': self.id,
                        'public': False,
                    })
                    
                    # Add to submission attachments
                    self.attachment_ids = [(4, attachment.id)]
                    
                    _logger.info("Created attachment from data URL for submission %s", self.name)
                    return attachment.id
                    
        except Exception as e:
            _logger.error("Error handling file upload for submission %s: %s", self.name, str(e))
            
        return False
    
    def _get_file_extension_from_mime_type(self, mime_type):
        """Get file extension from MIME type"""
        mime_to_extension = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'text/plain': '.txt',
            'text/csv': '.csv',
            'application/zip': '.zip',
            'application/x-zip-compressed': '.zip',
        }
        return mime_to_extension.get(mime_type, '.bin')
    
    def _format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def _send_notifications(self, target_record):
        """Send notifications for processed submission"""
        # Send email notification if configured
        if self.form_id.target_model_id.model == 'crm.lead':
            # Example: Send notification for CRM leads
            self._send_crm_notification(target_record)
    
    def _send_crm_notification(self, lead):
        """Send notification for CRM lead creation"""
        template = self.env.ref('crm.mail_template_crm_case_new', raise_if_not_found=False)
        if template:
            template.send_mail(lead.id, force_send=True)
    
    def action_view_target_record(self):
        """View the target record"""
        if not self.target_record_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No target record found.'),
                    'type': 'warning',
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.target_model,
            'res_id': self.target_record_id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_reset_to_draft(self):
        """Reset submission to draft state"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'processing_error': False,
            'processed_date': False,
        })
    
    def action_export_csv(self):
        """Export selected submissions to CSV"""
        if not self:
            raise UserError(_('No submissions selected for export.'))
        
        reporting = self.env['dynamic.forms.reporting']
        return reporting.export_submissions_to_csv(self.ids)
    
    def action_retry_processing(self):
        """Retry processing the submission"""
        self.ensure_one()
        if self.state == 'error':
            return self.action_process_submission()
    
    @api.model
    def create_from_form_data(self, form_id, form_data, metadata=None):
        """Create submission from form data"""
        metadata = metadata or {}
        
        # Validate form exists and is published
        form = self.env['dynamic.form'].browse(form_id)
        if not form.exists() or not form.is_published:
            raise ValidationError(_('Form not found or not published.'))
        
        # Validate form data
        self._validate_form_data(form, form_data)
        
        # Create submission
        submission_data = {
            'form_id': form_id,
            'form_data': json.dumps(form_data),
            'state': 'submitted',
            'ip_address': metadata.get('ip_address'),
            'user_agent': metadata.get('user_agent'),
            'referrer': metadata.get('referrer'),
            'session_id': metadata.get('session_id'),
        }
        
        submission = self.create(submission_data)
        
        # Increment form submission count
        form.increment_submission_count()
        
        return submission
    
    def _validate_form_data(self, form, form_data):
        """Validate form data against field definitions"""
        for field in form.field_ids:
            if field.required and not form_data.get(field.name):
                raise ValidationError(_('Field "%s" is required.') % field.label)
            
            value = form_data.get(field.name)
            if value:
                self._validate_field_value(field, value)
    
    def _validate_field_value(self, field, value):
        """Validate individual field value"""
        validation_rules = field.get_validation_rules()
        
        # Length validation
        if validation_rules.get('min_length') and len(str(value)) < validation_rules['min_length']:
            raise ValidationError(_('Field "%s" must be at least %d characters long.') % 
                                (field.label, validation_rules['min_length']))
        
        if validation_rules.get('max_length') and len(str(value)) > validation_rules['max_length']:
            raise ValidationError(_('Field "%s" must be no more than %d characters long.') % 
                                (field.label, validation_rules['max_length']))
        
        # Value validation for numbers
        if field.field_type == 'number':
            try:
                num_value = float(value)
                if validation_rules.get('min_value') is not None and num_value < validation_rules['min_value']:
                    raise ValidationError(_('Field "%s" must be at least %s.') % 
                                        (field.label, validation_rules['min_value']))
                if validation_rules.get('max_value') is not None and num_value > validation_rules['max_value']:
                    raise ValidationError(_('Field "%s" must be no more than %s.') % 
                                        (field.label, validation_rules['max_value']))
            except (ValueError, TypeError):
                raise ValidationError(_('Field "%s" must be a valid number.') % field.label)
        
        # Pattern validation
        if validation_rules.get('pattern'):
            import re
            if not re.match(validation_rules['pattern'], str(value)):
                raise ValidationError(_('Field "%s" format is invalid.') % field.label)
    
    def send_email_notifications(self):
        """Send email notifications based on form configuration"""
        self.ensure_one()
        
        if not self.form_id.enable_email_notifications:
            return
        
        # Send configured email notifications
        for notification in self.form_id.email_notification_ids.filtered(lambda n: n.active):
            try:
                notification.send_notification(self)
                _logger.info(f"Email notification '{notification.name}' sent for submission {self.name}")
            except Exception as e:
                _logger.error(f"Error sending email notification '{notification.name}' for submission {self.name}: {str(e)}")
        
        # Send legacy notifications if configured
        self._send_legacy_email_notifications()
    
    def _send_legacy_email_notifications(self):
        """Send legacy email notifications for backward compatibility"""
        self.ensure_one()
        
        # Admin notification
        if self.form_id.admin_email and self.form_id.notification_email_template_id:
            try:
                self.form_id.notification_email_template_id.send_mail(
                    self.id,
                    force_send=True,
                    email_values={
                        'email_to': self.form_id.admin_email,
                        'email_from': self.env.company.email or self.env.user.email,
                    }
                )
                _logger.info(f"Admin notification sent to {self.form_id.admin_email} for submission {self.name}")
            except Exception as e:
                _logger.error(f"Error sending admin notification for submission {self.name}: {str(e)}")
        
        # User confirmation
        if self.form_id.send_confirmation_email and self.form_id.confirmation_email_template_id:
            try:
                # Get user email from selected field or try to find it automatically
                submission_data = json.loads(self.form_data)
                user_email = None
                
                # First try to use the selected email field
                if self.form_id.user_email_field_id:
                    user_email = submission_data.get(self.form_id.user_email_field_id.name)
                    if user_email and '@' in str(user_email):
                        _logger.info(f"Using selected email field '{self.form_id.user_email_field_id.name}' for confirmation email")
                
                # Fallback: try to find email field automatically
                if not user_email:
                    for field_name, value in submission_data.items():
                        if 'email' in field_name.lower() and '@' in str(value):
                            user_email = value
                            _logger.info(f"Using auto-detected email field '{field_name}' for confirmation email")
                            break
                
                if user_email:
                    self.form_id.confirmation_email_template_id.send_mail(
                        self.id,
                        force_send=True,
                        email_values={
                            'email_to': user_email,
                            'email_from': self.env.company.email or self.env.user.email,
                        }
                    )
                    _logger.info(f"Confirmation email sent to {user_email} for submission {self.name}")
                else:
                    _logger.warning(f"No email field found in submission {self.name} for confirmation email")
                    
            except Exception as e:
                _logger.error(f"Error sending confirmation email for submission {self.name}: {str(e)}")
