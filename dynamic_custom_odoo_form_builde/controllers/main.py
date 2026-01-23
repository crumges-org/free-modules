from odoo import http # type: ignore # ignore
from odoo.http import request, Response # type: ignore # ignore
from odoo.exceptions import ValidationError # type: ignore # ignore
import json
import base64
from werkzeug.exceptions import NotFound, BadRequest # type: ignore # ignore
from urllib.parse import unquote
import logging

_logger = logging.getLogger(__name__)


class DynamicFormController(http.Controller):
    
    def _check_form_access(self, token):
        """Check if form access is allowed based on configuration"""
        try:
            # Check if the configuration model exists
            if 'dynamic.forms.config' not in request.env:
                _logger.warning("Configuration model not available, allowing access")
                return True, None
            
            try:
                config = request.env['dynamic.forms.config'].sudo().get_config()
            except Exception as config_error:
                _logger.warning("Could not get configuration (may not be set up yet): %s. Allowing access.", str(config_error))
                return True, None
            
            if not config or not config.exists():
                _logger.warning("No configuration found, allowing access")
                return True, None
            
            # Check if website interface is hidden
            if config.hide_website_interface:
                _logger.warning("Website interface is hidden for all forms")
                return False, "Website interface is hidden"
            
            # Check if web access is enabled
            if not config.enable_web_access:
                _logger.warning("Web access is disabled for all forms")
                return False, "Web access is disabled"
            
            # Check if this specific token is allowed
            if not config.is_form_access_allowed(token):
                _logger.warning("Form access denied for token: %s", token)
                return False, "Form access denied"
            
            return True, None
            
        except Exception as e:
            _logger.error("Error checking form access: %s", str(e))
            # In case of error during setup, allow access (more permissive)
            _logger.warning("Allowing access due to configuration error (may be during setup)")
            return True, None
    
    @http.route('/dynamic-form/test-config', type='http', auth='public')
    def test_config(self, **kwargs):
        """Test route to verify configuration is working"""
        try:
            if 'dynamic.forms.config' in request.env:
                config = request.env['dynamic.forms.config'].sudo().get_config()
                if config and config.exists():
                    return Response(
                        json.dumps({
                            'status': 'success',
                            'message': 'Configuration system is working',
                            'config_id': config.id,
                            'web_access_enabled': config.enable_web_access,
                            'block_other_urls': config.block_all_other_urls,
                            'allowed_tokens': config.allowed_form_tokens,
                        }),
                        content_type='application/json'
                    )
                else:
                    return Response(
                        json.dumps({
                            'status': 'error',
                            'message': 'No configuration found'
                        }),
                        content_type='application/json'
                    )
            else:
                return Response(
                    json.dumps({
                        'status': 'error',
                        'message': 'Configuration model not available'
                    }),
                    content_type='application/json'
                )
        except Exception as e:
            return Response(
                json.dumps({
                    'status': 'error',
                    'message': f'Configuration error: {str(e)}'
                }),
                content_type='application/json'
            )
    
    @http.route('/dynamic-form/view/<string:token>', type='http', auth='public')
    def view_form(self, token, **kwargs):
        """Render the form for public access"""
        try:
            # URL-decode the token in case it was URL-encoded
            token = unquote(token)
            
            # Check configuration-based access control (using original token)
            access_allowed, error_message = self._check_form_access(token)
            if not access_allowed:
                _logger.warning("Access denied for token %s: %s", token, error_message)
                return request.not_found()
            
            # Try to decode base64 token if it looks like base64
            decoded_token = self._decode_token_if_base64(token)
            search_token = decoded_token if decoded_token else token
            
            _logger.info("Looking for form with token: %s (decoded: %s)", token, search_token)
            # Search with both original and decoded token, and also try security_token
            # Domain: is_published=True AND (token=original OR token=decoded OR security_token=token)
            token_conditions = [('token', '=', token)]
            if decoded_token and decoded_token != token:
                token_conditions.append(('token', '=', search_token))
            token_conditions.append(('security_token', '=', token))
            
            # Build domain: ['&', ('is_published', '=', True), '|', '|', ...conditions...]
            domain = ['&', ('is_published', '=', True)]
            if len(token_conditions) > 1:
                domain.extend(['|'] * (len(token_conditions) - 1))
            domain.extend(token_conditions)
            form = request.env['dynamic.form'].sudo().search(domain, limit=1)
            _logger.info("Found form: %s (ID: %s)", form.name if form else "None", form.id if form else "None")
            
            # If not found, try a simpler search as fallback
            if not form:
                _logger.info("Form not found with complex domain, trying simple search...")
                # Try simple search by token only
                form = request.env['dynamic.form'].sudo().search([
                    ('is_published', '=', True),
                    ('token', '=', token)
                ], limit=1)
                if not form:
                    # Try with decoded token
                    if decoded_token and decoded_token != token:
                        form = request.env['dynamic.form'].sudo().search([
                            ('is_published', '=', True),
                            ('token', '=', decoded_token)
                        ], limit=1)
                if not form:
                    # Try with security_token
                    form = request.env['dynamic.form'].sudo().search([
                        ('is_published', '=', True),
                        ('security_token', '=', token)
                    ], limit=1)
            
            if not form:
                _logger.warning("Form not found or not published for token: %s (decoded: %s). Domain used: %s", 
                              token, search_token, domain)
                # Log all published forms for debugging
                all_published = request.env['dynamic.form'].sudo().search([('is_published', '=', True)])
                _logger.info("All published forms: %s", [(f.id, f.name, f.token[:20] + '...' if len(f.token) > 20 else f.token) for f in all_published])
                return request.not_found()
            
            # Increment view count
            form.increment_view_count()
            
            # Get form configuration
            try:
                form_config = self._get_form_config(form)
                _logger.info("Form config keys: %s", list(form_config.keys()) if isinstance(form_config, dict) else "Not a dict")
            except Exception as config_error:
                _logger.error("Error getting form config: %s", str(config_error))
                raise
            
            # Debug logging
            _logger.info("Form config: %s", form_config)
            _logger.info("Form fields count: %s", len(form.field_ids))
            
            # Generate HTML directly instead of using templates
            # Use original token from URL for form action URLs
            try:
                html_content = self._generate_form_html(form, form_config, token)
            except KeyError as ke:
                _logger.error("KeyError in _generate_form_html: %s. Form config keys: %s", str(ke), list(form_config.keys()) if isinstance(form_config, dict) else "Not a dict")
                raise
            except Exception as html_error:
                _logger.error("Error generating HTML: %s", str(html_error))
                import traceback
                _logger.error("Traceback: %s", traceback.format_exc())
                raise
            
            return Response(html_content, content_type='text/html')
            
        except Exception as e:
            _logger.error("Error rendering form: %s", str(e))
            import traceback
            _logger.error("Full traceback: %s", traceback.format_exc())
            return request.not_found()
    
    @http.route('/dynamic-form/view/<string:token>.js', type='http', auth='public')
    def embed_js(self, token, **kwargs):
        """Return JavaScript embed code"""
        try:
            # URL-decode the token in case it was URL-encoded
            token = unquote(token)
            
            # Check configuration-based access control (using original token)
            access_allowed, error_message = self._check_form_access(token)
            if not access_allowed:
                _logger.warning("Access denied for JS embed token %s: %s", token, error_message)
                return Response("console.error('Form access denied');", content_type='application/javascript')
            
            # Try to decode base64 token if it looks like base64
            decoded_token = self._decode_token_if_base64(token)
            search_token = decoded_token if decoded_token else token
            
            # Search with both original and decoded token, and also try security_token
            # Domain: is_published=True AND (token=original OR token=decoded OR security_token=token)
            token_conditions = [('token', '=', token)]
            if decoded_token and decoded_token != token:
                token_conditions.append(('token', '=', search_token))
            token_conditions.append(('security_token', '=', token))
            
            # Build domain: ['&', ('is_published', '=', True), '|', '|', ...conditions...]
            domain = ['&', ('is_published', '=', True)]
            if len(token_conditions) > 1:
                domain.extend(['|'] * (len(token_conditions) - 1))
            domain.extend(token_conditions)
            form = request.env['dynamic.form'].sudo().search(domain, limit=1)
            if not form:
                return Response("console.error('Form not found');", content_type='application/javascript')
            
            # Get form configuration
            form_config = self._get_form_config(form)
            
            # Convert to JSON string for embedding in JavaScript
            form_config_json = json.dumps(form_config, ensure_ascii=False)
            # Escape for JavaScript string: escape backslashes, single quotes, and newlines
            form_config_json_escaped = (form_config_json
                                       .replace('\\', '\\\\')  # Escape backslashes first
                                       .replace("'", "\\'")    # Escape single quotes
                                       .replace('\n', '\\n')   # Escape newlines
                                       .replace('\r', '\\r')   # Escape carriage returns
                                       .replace('\t', '\\t'))  # Escape tabs
            
            # Render JavaScript template
            js_content = request.env['ir.ui.view'].sudo()._render_template('dynamic_custom_odoo_form_builde.embed_js_template', {
                'form': form,
                'form_config': form_config_json_escaped,
                'base_url': request.httprequest.url_root.rstrip('/'),
            })
            
            return Response(js_content, content_type='application/javascript')
            
        except Exception as e:
            _logger.error("Error generating embed JS: %s", str(e))
            import traceback
            _logger.error("Full traceback: %s", traceback.format_exc())
            return Response(f"console.error('Error loading form: {str(e)}');", content_type='application/javascript')
    
    @http.route('/dynamic-form/submit/<string:token>', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_form(self, token, **kwargs):
        """Handle form submission via HTTP POST with CORS support"""
        # Set CORS headers
        response_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With',
            'Content-Type': 'application/json',
        }
        
        # Handle preflight OPTIONS request
        if request.httprequest.method == 'OPTIONS':
            return Response('', headers=response_headers)
        
        try:
            # URL-decode the token in case it was URL-encoded
            token = unquote(token)
            
            # Search for form with more detailed logging
            _logger.info("Searching for form with token: %s", token)
            
            # Try to decode base64 token if it looks like base64
            decoded_token = self._decode_token_if_base64(token)
            search_token = decoded_token if decoded_token else token
            
            # First, search for any form with this token (try both original and decoded)
            if decoded_token and decoded_token != token:
                search_domain = ['|', ('token', '=', token), ('token', '=', search_token)]
            else:
                search_domain = [('token', '=', token)]
            all_forms = request.env['dynamic.form'].sudo().search(search_domain)
            _logger.info("All forms with token %s (decoded: %s): %s (count: %s)", token, search_token, all_forms, len(all_forms))
            
            # Then search for published form
            if decoded_token and decoded_token != token:
                domain = ['|', ('token', '=', token), ('token', '=', search_token), ('is_published', '=', True)]
            else:
                domain = [('token', '=', token), ('is_published', '=', True)]
            form = request.env['dynamic.form'].sudo().search(domain, limit=1)
            _logger.info("Published form with token %s: %s", token, form)
            _logger.info("Form count: %s", len(form))
            
            if form:
                _logger.info("Form ID: %s", form.id)
                _logger.info("Form token: %s", form.token)
                _logger.info("Form published: %s", form.is_published)
                _logger.info("Form name: %s", form.name)
                _logger.info("Form recordset type: %s", type(form))
                _logger.info("Form recordset length: %s", len(form))
                
                # Ensure we have exactly one form
                if len(form) > 1:
                    _logger.warning("Multiple forms found with token %s, using first one", token)
                    form = form[0]
                elif len(form) == 1:
                    form = form[0]  # Get the single record
                else:
                    form = None
            else:
                _logger.warning("No published form found with token: %s", token)
                form = None
            
            if not form:
                _logger.warning("Form not found or not published for token: %s", token)
                return Response(
                    json.dumps({'success': False, 'error': 'Form not found or not published'}),
                    headers=response_headers
                )
            
            _logger.info("Form: %s", form)
            _logger.info("Request kwargs: %s", kwargs)
            
            # Get form data from request FIRST (before using it)
            form_data = {}
            try:
                request_data = request.httprequest.get_json()
                if request_data and 'form_data' in request_data:
                    form_data = request_data['form_data']
                elif 'form_data' in kwargs:
                    form_data = kwargs['form_data']
            except Exception as e:
                _logger.warning("Could not parse request body as JSON: %s", e)
                # Try to get from form data
                form_data = request.httprequest.form.to_dict()
            
            _logger.info("Extracted form_data: %s", form_data)
            
            # Validate that form_data is not empty
            if not form_data or (isinstance(form_data, dict) and not any(form_data.values())):
                _logger.warning("Form data is empty for token: %s", token)
                return Response(
                    json.dumps({'success': False, 'error': 'No form data provided. Please fill in the form fields.'}),
                    headers=response_headers
                )
            
            # Validate security token if provided (after form_data is extracted)
            security_token = form_data.get('security_token') or kwargs.get('security_token')
            if security_token and form.security_token:
                if not form.check_security_token(security_token):
                    _logger.warning("Invalid security token for form: %s", token)
                    return Response(
                        json.dumps({'success': False, 'error': 'Invalid security token'}),
                        headers=response_headers
                    )
                _logger.info("Security token validated successfully for form: %s", token)
            
            if not form_data:
                return Response(
                    json.dumps({'success': False, 'error': 'No form data provided'}),
                    headers=response_headers
                )
            
            # Get metadata
            metadata = {
                'ip_address': request.httprequest.remote_addr,
                'user_agent': request.httprequest.headers.get('User-Agent'),
                'referrer': request.httprequest.headers.get('Referer'),
                'session_id': request.session.sid,
            }
            
            # Check rate limiting
            if not self._check_rate_limit(form, metadata['ip_address']):
                return Response(
                    json.dumps({'success': False, 'error': 'Rate limit exceeded. Please try again later.'}),
                    headers=response_headers
                )
            
            # Validate reCAPTCHA if enabled
            if form.enable_captcha:
                captcha_response = form_data.get('captcha_response') or kwargs.get('captcha_response')
                _logger.info("reCAPTCHA enabled, response: %s", captcha_response)
                if not self._validate_captcha(form, captcha_response):
                    return Response(
                        json.dumps({'success': False, 'error': 'Invalid captcha response'}),
                        headers=response_headers
                    )
            else:
                _logger.info("reCAPTCHA disabled for this form")
            
            # Create submission
            _logger.info("Creating submission for form %s with data: %s", form.id, form_data)
            _logger.info("Form object: %s", form)
            _logger.info("Form ID type: %s", type(form.id))
            _logger.info("Form ID value: %s", form.id)
            
            # Validate form ID before proceeding
            if not form.id:
                _logger.error("Form ID is null or invalid: %s", form.id)
                return Response(
                    json.dumps({'success': False, 'error': 'Invalid form ID'}),
                    headers=response_headers
                )
            
            # Create submission with explicit form_id
            submission_vals = {
                'form_id': int(form.id),  # Ensure it's an integer
                'form_data': json.dumps(form_data),
                'state': 'submitted',
                'ip_address': metadata.get('ip_address'),
                'user_agent': metadata.get('user_agent'),
                'referrer': metadata.get('referrer'),
                'session_id': metadata.get('session_id'),
            }
            _logger.info("Submission values: %s", submission_vals)
            _logger.info("Form ID in submission_vals: %s (type: %s)", submission_vals['form_id'], type(submission_vals['form_id']))
            
            # Double-check form exists before creating submission
            form_check = request.env['dynamic.form'].sudo().browse(int(form.id))
            if not form_check.exists():
                _logger.error("Form with ID %s does not exist", form.id)
                return Response(
                    json.dumps({'success': False, 'error': 'Form not found'}),
                    headers=response_headers
                )
            
            try:
                # Create submission - let Odoo handle the transaction
                submission = request.env['dynamic.form.submission'].sudo().create(submission_vals)
                _logger.info("Submission created successfully: %s", submission.name)
                
                # Process submission - wrap in try/except to catch processing errors
                try:
                    result = submission.action_process_submission()
                    if result is None:
                        # Processing failed but submission state was updated
                        _logger.warning("Submission processing returned None - check submission state")
                        # Refresh submission to get latest state
                        submission.invalidate_recordset(['state', 'processing_error'])
                        if submission.state == 'error':
                            # Still return success to user, but log the error
                            _logger.warning("Submission %s created but processing failed", submission.name)
                            return Response(
                                json.dumps({
                                    'success': True,
                                    'message': form.success_message or 'Thank you! Your submission has been received. We will process it shortly.',
                                    'submission_id': submission.name,
                                }),
                                headers=response_headers
                            )
                    else:
                        _logger.info("Submission processed successfully")
                except ValidationError as validation_error:
                    # ValidationError is raised by action_process_submission on errors
                    # But submission should already be saved with error state
                    _logger.error("Validation error processing submission: %s", str(validation_error))
                    import traceback
                    _logger.error("Processing traceback: %s", traceback.format_exc())
                    
                    # Refresh submission to get latest state
                    submission.invalidate_recordset(['state', 'processing_error'])
                    
                    # Check if submission was created but processing failed
                    if submission and submission.state == 'error':
                        # Submission was saved but processing failed
                        # Still return success to user, but log the error
                        _logger.warning("Submission %s created but processing failed: %s", submission.name, str(validation_error))
                        return Response(
                            json.dumps({
                                'success': True,
                                'message': form.success_message or 'Thank you! Your submission has been received. We will process it shortly.',
                                'submission_id': submission.name,
                            }),
                            headers=response_headers
                        )
                    else:
                        # Processing error - return error to user
                        return Response(
                            json.dumps({
                                'success': False, 
                                'error': f'Error processing submission: {str(validation_error)}'
                            }),
                            headers=response_headers
                        )
                except Exception as process_error:
                    _logger.error("Error processing submission: %s", str(process_error))
                    import traceback
                    _logger.error("Processing traceback: %s", traceback.format_exc())
                    
                    # Refresh submission to get latest state
                    submission.invalidate_recordset(['state', 'processing_error'])
                    
                    # Check if submission was created but processing failed
                    if submission and submission.state == 'error':
                        # Submission was saved but processing failed
                        # Still return success to user, but log the error
                        _logger.warning("Submission %s created but processing failed: %s", submission.name, str(process_error))
                        return Response(
                            json.dumps({
                                'success': True,
                                'message': form.success_message or 'Thank you! Your submission has been received. We will process it shortly.',
                                'submission_id': submission.name,
                            }),
                            headers=response_headers
                        )
                    else:
                        # Processing error - return error to user
                        return Response(
                            json.dumps({
                                'success': False, 
                                'error': f'Error processing submission: {str(process_error)}'
                            }),
                            headers=response_headers
                        )
                
            except ValidationError as validation_error:
                _logger.error("Validation error creating submission: %s", str(validation_error))
                import traceback
                _logger.error("Traceback: %s", traceback.format_exc())
                return Response(
                    json.dumps({
                        'success': False, 
                        'error': f'Error processing submission: {str(validation_error)}'
                    }),
                    headers=response_headers
                )
            except Exception as e:
                _logger.error("Error creating/processing submission: %s", str(e))
                import traceback
                _logger.error("Traceback: %s", traceback.format_exc())
                # Let Odoo handle the rollback automatically
                return Response(
                    json.dumps({
                        'success': False, 
                        'error': f'Error processing submission: {str(e)}'
                    }),
                    headers=response_headers
                )
            
            return Response(
                json.dumps({
                    'success': True,
                    'message': form.success_message or 'Thank you! Your submission has been received.',
                    'submission_id': submission.name,
                }),
                headers=response_headers
            )
            
        except Exception as e:
            _logger.error("Error submitting form: %s", str(e))
            error_message = form.error_message if 'form' in locals() else 'An error occurred. Please try again.'
            return Response(
                json.dumps({'success': False, 'error': str(e) if request.env.user.has_group('base.group_system') else error_message}),
                headers=response_headers
            )
    
    @http.route('/dynamic-form/submit/<string:token>', type='http', auth='public', methods=['OPTIONS'], csrf=False)
    def submit_form_options(self, token, **kwargs):
        """Handle CORS preflight OPTIONS request"""
        response_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With',
            'Content-Type': 'application/json',
        }
        return Response('', headers=response_headers)
    
    @http.route('/dynamic-form/upload/<string:token>', type='http', auth='public', methods=['POST'], csrf=False)
    def upload_file(self, token, **kwargs):
        """Handle file uploads with CORS support"""
        # Set CORS headers
        response_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With',
            'Content-Type': 'application/json',
        }
        
        # Handle preflight OPTIONS request
        if request.httprequest.method == 'OPTIONS':
            return Response('', headers=response_headers)
        
        try:
            # URL-decode the token in case it was URL-encoded
            token = unquote(token)
            
            # Try to decode base64 token if it looks like base64
            decoded_token = self._decode_token_if_base64(token)
            search_token = decoded_token if decoded_token else token
            
            # Search with both original and decoded token, and also try security_token
            token_conditions = [('token', '=', token)]
            if decoded_token and decoded_token != token:
                token_conditions.append(('token', '=', search_token))
            token_conditions.append(('security_token', '=', token))
            
            # Build domain: ['&', ('is_published', '=', True), '|', '|', ...conditions...]
            domain = ['&', ('is_published', '=', True)]
            if len(token_conditions) > 1:
                domain.extend(['|'] * (len(token_conditions) - 1))
            domain.extend(token_conditions)
            form = request.env['dynamic.form'].sudo().search(domain, limit=1)
            if not form:
                return Response(
                    json.dumps({'success': False, 'error': 'Form not found'}),
                    headers=response_headers
                )
            
            # Get uploaded file
            uploaded_file = request.httprequest.files.get('file')
            if not uploaded_file:
                return Response(
                    json.dumps({'success': False, 'error': 'No file provided'}),
                    headers=response_headers
                )
            
            # Validate file
            validation_result = self._validate_uploaded_file(form, uploaded_file)
            if not validation_result['valid']:
                return Response(
                    json.dumps({'success': False, 'error': validation_result['error']}),
                    headers=response_headers
                )
            
            # Create attachment
            attachment = request.env['ir.attachment'].sudo().create({
                'name': uploaded_file.filename,
                'datas': base64.b64encode(uploaded_file.read()),
                'res_model': 'dynamic.form',
                'res_id': form.id,
            })
            
            return Response(
                json.dumps({
                    'success': True,
                    'attachment_id': attachment.id,
                    'filename': attachment.name,
                }),
                headers=response_headers
            )
            
        except Exception as e:
            _logger.error("Error uploading file: %s", str(e))
            return Response(
                json.dumps({'success': False, 'error': 'Upload failed'}),
                headers=response_headers
            )
    
    def _decode_token_if_base64(self, token):
        """Try to decode a token if it appears to be base64 encoded"""
        try:
            # Check if token looks like base64 (contains only base64 characters and has reasonable length)
            import re
            if not token or len(token) < 4:
                return None
            
            # Check if it looks like base64 (contains only base64 characters)
            if not re.match(r'^[A-Za-z0-9+/_-]+=*$', token):
                return None
            
            # Try to decode
            try:
                decoded = base64.urlsafe_b64decode(token + '==').decode('utf-8')
                # Only return if decoded value is different and looks like a valid token
                if decoded != token and len(decoded) > 0:
                    _logger.info("Decoded base64 token: %s -> %s", token, decoded)
                    return decoded
            except Exception:
                # If decoding fails, it's not base64
                return None
        except Exception as e:
            _logger.debug("Error decoding token: %s", str(e))
        return None
    
    def _get_form_config(self, form):
        """Get complete form configuration for frontend"""
        # Process logo using helper function
        logo_data, logo_format = self._process_logo(form.logo)
        
        config = {
            'id': form.id,
            'token': form.token,
            'security_token': form.security_token,
            'name': form.name,
            'description': form.description,
            'theme': form.theme,
            'layout': form.layout,
            'position': form.position,
            'header_layout': form.header_layout,
            'hide_header': form.hide_header,
            'custom_css': form.custom_css,
            'primary_color': form.primary_color,
            'secondary_color': form.secondary_color,
            'logo': logo_data,  # Base64 encoded logo as string
            'logo_format': logo_format,  # Image format (png, jpeg, etc.)
            'show_progress_bar': form.show_progress_bar,
            'show_submit_button': form.show_submit_button,
            'submit_button_text': form.submit_button_text,
            'enable_captcha': form.enable_captcha,
            'captcha_site_key': form.captcha_site_key,
            'background_style': form.background_style,
            'background_color': form.background_color,
            'background_gradient': form.background_gradient,
            'background_image': form.background_image,
            'background_image_url': form.background_image_url,
            'fields': [],
        }
        
        # Add field configurations
        for field in form.field_ids.filtered(lambda f: f.active):
            config['fields'].append(field.get_field_config())
        
        return config
    
    def _check_rate_limit(self, form, ip_address):
        """Check if submission rate limit is exceeded"""
        if not form.rate_limit:
            return True
        
        # Count submissions in the last hour
        from datetime import datetime, timedelta
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        recent_submissions = request.env['dynamic.form.submission'].sudo().search_count([
            ('form_id', '=', form.id),
            ('ip_address', '=', ip_address),
            ('create_date', '>=', one_hour_ago),
        ])
        
        return recent_submissions < form.rate_limit
    
    def _validate_captcha(self, form, captcha_response):
        """Validate reCAPTCHA response"""
        if not form.captcha_secret_key or not captcha_response:
            return False
        
        try:
            import requests
            response = requests.post('https://www.google.com/recaptcha/api/siteverify', data={
                'secret': form.captcha_secret_key,
                'response': captcha_response,
            })
            result = response.json()
            return result.get('success', False)
        except Exception as e:
            _logger.error("Error validating captcha: %s", str(e))
            return False
    
    def _validate_uploaded_file(self, form, uploaded_file):
        """Validate uploaded file"""
        # Check file size
        if form.field_ids.filtered(lambda f: f.field_type == 'file'):
            max_size = form.field_ids.filtered(lambda f: f.field_type == 'file')[0].max_file_size * 1024 * 1024
            uploaded_file.seek(0, 2)  # Seek to end
            file_size = uploaded_file.tell()
            uploaded_file.seek(0)  # Reset to beginning
            
            if file_size > max_size:
                return {
                    'valid': False,
                    'error': f'File size exceeds maximum allowed size of {form.field_ids.filtered(lambda f: f.field_type == "file")[0].max_file_size}MB'
                }
        
        # Check file type
        if form.field_ids.filtered(lambda f: f.field_type == 'file'):
            allowed_types = form.field_ids.filtered(lambda f: f.field_type == 'file')[0].allowed_file_types
            if allowed_types:
                file_extension = '.' + uploaded_file.filename.split('.')[-1].lower()
                allowed_extensions = [ext.strip().lower() for ext in allowed_types.split(',')]
                if file_extension not in allowed_extensions:
                    return {
                        'valid': False,
                        'error': f'File type not allowed. Allowed types: {allowed_types}'
                    }
        
        return {'valid': True}
    
    def _process_logo(self, logo_field):
        """Process logo field and return (base64_data, image_format) tuple."""
        if not logo_field:
            return None, None
        
        import base64
        
        try:
            # Odoo Binary fields return base64-encoded strings directly
            logo_data = logo_field
            
            # If it's bytes, encode to base64 string
            if isinstance(logo_data, bytes):
                logo_data = base64.b64encode(logo_data).decode('utf-8')
            elif not isinstance(logo_data, str):
                # Try to convert to bytes first
                try:
                    logo_data = base64.b64encode(bytes(logo_data)).decode('utf-8')
                except:
                    _logger.warning("Could not convert logo to base64 string")
                    return None, None
            
            # Ensure logo_data is a valid base64 string
            if not logo_data or not isinstance(logo_data, str):
                return None, None
            
            # Remove any whitespace, newlines, and other invalid base64 characters
            logo_data = ''.join(logo_data.split())
            
            # Detect image format by decoding and checking magic bytes
            image_format = 'png'  # default
            try:
                # Decode the base64 to get raw bytes
                decoded_bytes = base64.b64decode(logo_data, validate=True)
                
                # Check magic bytes to determine format
                if len(decoded_bytes) >= 8:
                    if decoded_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                        image_format = 'png'
                    elif decoded_bytes.startswith(b'\xff\xd8\xff'):
                        image_format = 'jpeg'
                    elif decoded_bytes.startswith(b'GIF87a') or decoded_bytes.startswith(b'GIF89a'):
                        image_format = 'gif'
                    elif decoded_bytes.startswith(b'RIFF') and len(decoded_bytes) > 12 and b'WEBP' in decoded_bytes[:12]:
                        image_format = 'webp'
                    elif decoded_bytes.startswith(b'<svg') or decoded_bytes.startswith(b'<?xml'):
                        image_format = 'svg+xml'
                    else:
                        # Try to decode as string to check if it's double-encoded
                        try:
                            decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                            if decoded_str.startswith('iVBORw0KGgo'):
                                # It's a PNG that was base64 encoded twice
                                # Use the decoded string as the actual base64
                                logo_data = decoded_str
                                image_format = 'png'
                            elif decoded_str.startswith('/9j/'):
                                # It's a JPEG that was base64 encoded twice
                                logo_data = decoded_str
                                image_format = 'jpeg'
                        except:
                            pass
            except Exception as e:
                _logger.warning("Error detecting logo format: %s", str(e))
                # Fallback: check base64 string itself for common patterns
                if logo_data.startswith('iVBORw0KGgo'):
                    image_format = 'png'
                elif logo_data.startswith('/9j/'):
                    image_format = 'jpeg'
                else:
                    # Try one more time with a simpler decode
                    try:
                        # Sometimes the data might have padding issues
                        # Add padding if needed
                        missing_padding = len(logo_data) % 4
                        if missing_padding:
                            logo_data += '=' * (4 - missing_padding)
                        decoded_bytes = base64.b64decode(logo_data, validate=False)
                        if decoded_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                            image_format = 'png'
                        elif decoded_bytes.startswith(b'\xff\xd8\xff'):
                            image_format = 'jpeg'
                    except:
                        _logger.warning("Could not decode logo data even with padding fix")
            
            return logo_data, image_format
        except Exception as e:
            _logger.warning("Error processing logo: %s", str(e))
            import traceback
            _logger.debug("Logo processing traceback: %s", traceback.format_exc())
            return None, None
    
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _get_body_background(self, background_style, default_gradient, background_color, 
                             background_gradient, background_image, background_image_url):
        """Get the body background CSS based on background style."""
        if background_style == 'solid' and background_color:
            return background_color
        elif background_style == 'gradient' and background_gradient:
            return background_gradient
        elif background_style == 'image':
            if background_image_url:
                return f"url('{background_image_url}') center/cover no-repeat"
            elif background_image:
                # For binary images, we'd need to convert to data URL or serve via controller
                # For now, return default if binary image is provided
                return default_gradient
        elif background_style == 'pattern':
            # Pattern backgrounds can be created with CSS
            if background_gradient:
                return background_gradient
        # Default to theme gradient
        return default_gradient
    
    def _get_theme_colors(self, theme, primary_color=None, secondary_color=None):
        """Get theme-specific color scheme."""
        themes = {
            'light': {
                'primary': '#007bff',
                'secondary': '#0056b3',
                'bg_gradient': 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
                'container_bg': '#ffffff',
                'text_color': '#2d3436',
                'input_bg': '#fafbfc',
                'input_border': '#e0e0e0',
            },
            'dark': {
                'primary': '#6c5ce7',
                'secondary': '#5f3dc4',
                'bg_gradient': 'linear-gradient(135deg, #2d3436 0%, #636e72 100%)',
                'container_bg': '#2d3436',
                'text_color': '#ffffff',
                'input_bg': '#3d4549',
                'input_border': '#4a5568',
            },
            'blue': {
                'primary': '#0d6efd',
                'secondary': '#0a58ca',
                'bg_gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                'container_bg': '#ffffff',
                'text_color': '#1a202c',
                'input_bg': '#f0f4ff',
                'input_border': '#cbd5e0',
            },
            'green': {
                'primary': '#198754',
                'secondary': '#146c43',
                'bg_gradient': 'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)',
                'container_bg': '#ffffff',
                'text_color': '#1a202c',
                'input_bg': '#f0fff4',
                'input_border': '#c6f6d5',
            },
            'purple': {
                'primary': '#6f42c1',
                'secondary': '#5a32a3',
                'bg_gradient': 'linear-gradient(135deg, #a78bfa 0%, #c084fc 100%)',
                'container_bg': '#ffffff',
                'text_color': '#1a202c',
                'input_bg': '#faf5ff',
                'input_border': '#e9d5ff',
            },
            'orange': {
                'primary': '#fd7e14',
                'secondary': '#dc6502',
                'bg_gradient': 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
                'container_bg': '#ffffff',
                'text_color': '#1a202c',
                'input_bg': '#fff7ed',
                'input_border': '#fed7aa',
            },
            'custom': {
                'primary': primary_color or '#4CAF50',
                'secondary': secondary_color or '#45a049',
                'bg_gradient': f'linear-gradient(135deg, {primary_color or "#4CAF50"} 0%, {secondary_color or "#45a049"} 100%)',
                'container_bg': '#ffffff',
                'text_color': '#2d3436',
                'input_bg': '#fafbfc',
                'input_border': '#e0e0e0',
            },
        }
        return themes.get(theme, themes['light'])
    
    def _generate_form_html(self, form, form_config, url_token=None):
        """Generates the HTML content for the dynamic form."""
        # Validate inputs
        if not isinstance(form_config, dict):
            raise ValueError(f"form_config must be a dict, got {type(form_config)}")
        
        # Use URL token if provided (for base64 tokens), otherwise use form token
        token = url_token if url_token else form.token
        
        # Ensure all required keys exist in form_config with defaults
        theme = form_config.get('theme', form.theme or 'light')
        layout = form_config.get('layout', form.layout or 'standard')
        position = form_config.get('position', form.position or 'center')
        header_layout = form_config.get('header_layout', form.header_layout or 'centered')
        hide_header = form_config.get('hide_header', form.hide_header or False)
        # Store original form colors before theme processing
        form_primary_color = form_config.get('primary_color') or form.primary_color
        form_secondary_color = form_config.get('secondary_color') or form.secondary_color
        primary_color = form_primary_color or '#4CAF50'
        secondary_color = form_secondary_color or '#45a049'
        custom_css = form_config.get('custom_css', form.custom_css or '')
        enable_captcha = 'true' if form.enable_captcha else 'false'
        submit_button_text = form.submit_button_text or 'Submit'
        show_progress_bar = form_config.get('show_progress_bar', form.show_progress_bar if hasattr(form, 'show_progress_bar') else True)
        
        # Background customization
        background_style = form_config.get('background_style', form.background_style or 'gradient')
        background_color = form_config.get('background_color', form.background_color or '')
        background_gradient = form_config.get('background_gradient', form.background_gradient or '')
        background_image = form_config.get('background_image', form.background_image or '')
        background_image_url = form_config.get('background_image_url', form.background_image_url or '')
        
        # Get theme-specific colors
        theme_colors = self._get_theme_colors(theme, primary_color, secondary_color)
        theme_primary_color = theme_colors['primary']
        theme_secondary_color = theme_colors['secondary']
        default_bg_gradient = theme_colors['bg_gradient']
        container_bg = theme_colors['container_bg']
        text_color = theme_colors['text_color']
        input_bg = theme_colors['input_bg']
        input_border = theme_colors['input_border']
        
        # Use form's custom colors if set, otherwise use theme colors
        # This ensures custom colors are always used when specified
        final_primary_color = form_primary_color if form_primary_color else theme_primary_color
        final_secondary_color = form_secondary_color if form_secondary_color else theme_secondary_color
        
        # Use form's custom colors for header if set, otherwise use theme colors
        header_primary_color = form_primary_color if form_primary_color else theme_primary_color
        header_secondary_color = form_secondary_color if form_secondary_color else theme_secondary_color
        
        # Determine final background style
        body_background = self._get_body_background(
            background_style, 
            default_bg_gradient, 
            background_color, 
            background_gradient, 
            background_image, 
            background_image_url
        )
        
        # Convert primary color to RGB for rgba values (use header color for consistency)
        try:
            primary_rgb = self._hex_to_rgb(header_primary_color)
            primary_color_rgb = f"{primary_rgb[0]}, {primary_rgb[1]}, {primary_rgb[2]}"
        except:
            primary_color_rgb = "76, 175, 80"  # Default green RGB
        
        # Generate modal close button if position is modal
        modal_close_button = ''
        if position == 'modal':
            modal_close_button = '<button type="button" class="modal-close" onclick="this.closest(\'.position-modal\').style.display=\'none\'" aria-label="Close">&times;</button>'
        
        # Generate logo HTML if logo exists
        logo_html = ''
        if form.logo:
            logo_data, image_format = self._process_logo(form.logo)
            if logo_data and image_format:
                logo_html = f'<img src="data:image/{image_format};base64,{logo_data}" class="form-logo" alt="Form Logo">'
        
        # Generate progress bar HTML based on show_progress_bar
        progress_bar_html = ''
        if show_progress_bar:
            progress_bar_html = '''<div class="progress-bar">
                <div class="progress-bar-fill" id="progress_bar" style="width: 0%;"></div>
            </div>'''
        
        # Generate header HTML based on hide_header and header_layout
        header_html = ''
        if not hide_header:
            header_layout_class = f'header-layout-{header_layout}'
            
            # Generate different HTML structures based on layout
            if header_layout == 'split':
                # Split: Logo left, content right
                header_html = f'''<div class="form-header {header_layout_class}">
            <div class="header-logo-section">
                {logo_html}
            </div>
            <div class="header-content-section">
                <h1>{form.name or ''}</h1>
                <p>{form.description or ''}</p>
            </div>
        </div>'''
            elif header_layout == 'split-reverse':
                # Split Reverse: Content left, logo right
                header_html = f'''<div class="form-header {header_layout_class}">
            <div class="header-content-section">
                <h1>{form.name or ''}</h1>
                <p>{form.description or ''}</p>
            </div>
            <div class="header-logo-section">
                {logo_html}
            </div>
        </div>'''
            elif header_layout == 'inline':
                # Inline: Logo, title, description in a row
                header_html = f'''<div class="form-header {header_layout_class}">
            <div class="header-logo-section">
                {logo_html}
            </div>
            <div class="header-content-section">
                <h1>{form.name or ''}</h1>
                <p>{form.description or ''}</p>
            </div>
        </div>'''
            elif header_layout == 'stacked':
                # Stacked: All elements stacked vertically
                header_html = f'''<div class="form-header {header_layout_class}">
            <div class="header-logo-section">
                {logo_html}
            </div>
            <div class="header-content-section">
                <h1>{form.name or ''}</h1>
                <p>{form.description or ''}</p>
            </div>
        </div>'''
            elif header_layout == 'compact':
                # Compact: Logo and title side by side
                header_html = f'''<div class="form-header {header_layout_class}">
            <div class="header-logo-section">
                {logo_html}
            </div>
            <div class="header-content-section">
                <h1>{form.name or ''}</h1>
                <p class="header-description">{form.description or ''}</p>
            </div>
        </div>'''
            elif header_layout == 'minimal':
                # Minimal: Just title with border, no logo/description
                header_html = f'''<div class="form-header {header_layout_class}">
            <h1>{form.name or ''}</h1>
        </div>'''
            else:
                # Centered (default) or Banner: Logo above, title and description centered
                header_html = f'''<div class="form-header {header_layout_class}">
            {logo_html}
            <h1>{form.name or ''}</h1>
            <p>{form.description or ''}</p>
        </div>'''
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dynamic Form - {form_name}</title>
    <style>
        /* Modern Form Styles */
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: {text_color};
            background: {body_background};
            min-height: 100vh;
            padding: 40px 20px;
        }}
        
        /* Background image overlay for better text readability */
        body[style*="url("]::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.3);
            z-index: -1;
        }}
        
        .container {{
            max-width: 700px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
            animation: slideUp 0.5s ease-out;
        }}
        
        /* Layout-specific styles */
        .layout-card .container {{
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
        }}
        
        .layout-card .form-group {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #e9ecef;
        }}
        
        .layout-minimal .container {{
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            border: 1px solid #e9ecef;
        }}
        
        .layout-minimal .form-header {{
            background: transparent;
            color: {text_color};
            border-bottom: 2px solid {primary_color};
            padding: 30px 30px 20px;
        }}
        
        .layout-minimal .form-header h1 {{
            color: {text_color};
        }}
        
        .layout-split .container {{
            display: flex;
            max-width: 1000px;
            border-radius: 0;
            box-shadow: none;
        }}
        
        .layout-split .form-header {{
            flex: 0 0 40%;
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 60px 40px;
            border-radius: 0;
        }}
        
        .layout-split .form-body {{
            flex: 0 0 60%;
            padding: 60px 40px;
        }}
        
        .layout-wizard .container {{
            max-width: 800px;
        }}
        
        .layout-wizard .form-group {{
            margin-bottom: 30px;
            padding-bottom: 30px;
            border-bottom: 2px dashed #e9ecef;
        }}
        
        .layout-wizard .form-group:last-child {{
            border-bottom: none;
        }}
        
        .layout-inline .container {{
            max-width: 100%;
        }}
        
        .layout-inline .form-body {{
            padding: 30px;
        }}
        
        .layout-inline .form-body form {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: flex-end;
        }}
        
        .layout-inline .form-group {{
            flex: 1;
            min-width: 200px;
            margin-bottom: 0;
            display: flex;
            flex-direction: column;
        }}
        
        .layout-inline .form-group label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .layout-inline .form-group input,
        .layout-inline .form-group select,
        .layout-inline .form-group textarea {{
            width: 100%;
            flex: 1;
        }}
        
        .layout-inline .submit-button {{
            flex: 0 0 auto;
            align-self: flex-end;
            margin-top: 0;
        }}
        
        .layout-inline .form-body .progress-bar,
        .layout-inline .form-body #submission_message {{
            width: 100%;
            margin-top: 20px;
        }}
        
        /* Grid Layout (2 Columns) */
        .layout-grid .form-body form {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }}
        
        .layout-grid .form-group {{
            margin-bottom: 0;
        }}
        
        .layout-grid .form-group:last-child,
        .layout-grid .submit-button {{
            grid-column: 1 / -1;
        }}
        
        /* Sidebar Layout */
        .layout-sidebar .container {{
            display: flex;
            max-width: 1000px;
        }}
        
        .layout-sidebar .form-header {{
            flex: 0 0 300px;
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            padding: 40px 30px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        
        .layout-sidebar .form-body {{
            flex: 1;
            padding: 40px;
        }}
        
        /* Tabbed Layout */
        .layout-tabbed .form-tabs {{
            display: flex;
            border-bottom: 2px solid #e9ecef;
            margin-bottom: 30px;
            padding: 0 30px;
        }}
        
        .layout-tabbed .form-tab {{
            padding: 15px 25px;
            cursor: pointer;
            border: none;
            background: transparent;
            color: #6c757d;
            font-weight: 500;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            transition: all 0.3s ease;
        }}
        
        .layout-tabbed .form-tab.active {{
            color: {primary_color};
            border-bottom-color: {primary_color};
        }}
        
        .layout-tabbed .form-tab-content {{
            display: none;
        }}
        
        .layout-tabbed .form-tab-content.active {{
            display: block;
        }}
        
        /* Accordion Layout */
        .layout-accordion .form-group {{
            margin-bottom: 10px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .layout-accordion .form-group-header {{
            padding: 15px 20px;
            background: #f8f9fa;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 500;
            color: #495057;
        }}
        
        .layout-accordion .form-group-header:hover {{
            background: #e9ecef;
        }}
        
        .layout-accordion .form-group-header::after {{
            content: '+';
            font-size: 20px;
            font-weight: bold;
            color: {primary_color};
        }}
        
        .layout-accordion .form-group.active .form-group-header::after {{
            content: '−';
        }}
        
        .layout-accordion .form-group-content {{
            padding: 0 20px;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease, padding 0.3s ease;
        }}
        
        .layout-accordion .form-group.active .form-group-content {{
            padding: 20px;
            max-height: 1000px;
        }}
        
        .layout-accordion .form-group.active .form-group-content label {{
            display: block;
            margin-bottom: 8px;
        }}
        
        /* Compact Layout */
        .layout-compact .form-body {{
            padding: 20px;
        }}
        
        .layout-compact .form-group {{
            margin-bottom: 15px;
        }}
        
        .layout-compact .form-group label {{
            font-size: 13px;
            margin-bottom: 5px;
        }}
        
        .layout-compact .form-group input,
        .layout-compact .form-group select,
        .layout-compact .form-group textarea {{
            padding: 8px 12px;
            font-size: 14px;
        }}
        
        .layout-compact .submit-button {{
            padding: 10px 25px;
            font-size: 14px;
        }}
        
        /* Modern Layout */
        .layout-modern .container {{
            border-radius: 20px;
            overflow: hidden;
        }}
        
        .layout-modern .form-header {{
            padding: 50px 40px;
            position: relative;
            overflow: hidden;
        }}
        
        .layout-modern .form-header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            pointer-events: none;
        }}
        
        .layout-modern .form-body {{
            padding: 50px 40px;
        }}
        
        .layout-modern .form-group {{
            margin-bottom: 30px;
            position: relative;
        }}
        
        .layout-modern .form-group label {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #2d3436;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .layout-modern .form-group input,
        .layout-modern .form-group select,
        .layout-modern .form-group textarea {{
            border: none;
            border-bottom: 2px solid #e9ecef;
            border-radius: 0;
            padding: 12px 0;
            background: transparent;
            transition: border-color 0.3s ease;
        }}
        
        .layout-modern .form-group input:focus,
        .layout-modern .form-group select:focus,
        .layout-modern .form-group textarea:focus {{
            outline: none;
            border-bottom-color: {primary_color};
        }}
        
        .layout-modern .submit-button {{
            border-radius: 50px;
            padding: 16px 50px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: 0 4px 15px rgba({primary_color_rgb}, 0.3);
        }}
        
        @media (max-width: 768px) {{
            .layout-split .container {{
                flex-direction: column;
            }}
            
            .layout-split .form-header {{
                flex: 0 0 auto;
            }}
            
            .layout-split .form-body {{
                flex: 0 0 auto;
            }}
            
            .layout-inline .form-body form {{
                flex-direction: column;
            }}
            
            .layout-inline .form-group {{
                width: 100%;
                min-width: 100%;
            }}
            
            .layout-grid .form-body form {{
                grid-template-columns: 1fr;
            }}
            
            .layout-sidebar .container {{
                flex-direction: column;
            }}
            
            .layout-sidebar .form-header {{
                flex: 0 0 auto;
            }}
            
            .layout-sidebar .form-body {{
                flex: 0 0 auto;
            }}
        }}
        
        @keyframes slideUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        /* Base Header Styles */
        .form-header {{
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        
        .form-header h1 {{
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .form-header p {{
            font-size: 16px;
            opacity: 0.95;
            margin: 0;
        }}
        
        .form-logo {{
            max-width: 150px;
            max-height: 80px;
            margin-bottom: 20px;
            display: block;
            margin-left: auto;
            margin-right: auto;
            border-radius: 8px;
        }}
        
        /* Header Section Containers */
        .header-logo-section {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .header-content-section {{
            display: flex;
            flex-direction: column;
        }}
        
        /* Centered Layout (Logo Above) */
        .form-header.header-layout-centered {{
            text-align: center;
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            color: white;
        }}
        
        .form-header.header-layout-centered h1 {{
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .form-header.header-layout-centered p {{
            color: rgba(255,255,255,0.9);
        }}
        
        /* Split Layout (Logo Left, Content Right) */
        .form-header.header-layout-split {{
            display: flex;
            align-items: center;
            gap: 30px;
            text-align: left;
            padding: 40px 30px;
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            color: white;
        }}
        
        .form-header.header-layout-split h1 {{
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .form-header.header-layout-split p {{
            color: rgba(255,255,255,0.9);
        }}
        
        .form-header.header-layout-split .header-logo-section {{
            flex: 0 0 auto;
            margin-bottom: 0;
        }}
        
        .form-header.header-layout-split .header-content-section {{
            flex: 1;
        }}
        
        .form-header.header-layout-split .form-logo {{
            margin: 0;
            max-width: 120px;
            max-height: 120px;
        }}
        
        /* Split Reverse Layout (Content Left, Logo Right) */
        .form-header.header-layout-split-reverse {{
            display: flex;
            align-items: center;
            gap: 30px;
            text-align: left;
            padding: 40px 30px;
            flex-direction: row;
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            color: white;
        }}
        
        .form-header.header-layout-split-reverse h1 {{
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .form-header.header-layout-split-reverse p {{
            color: rgba(255,255,255,0.9);
        }}
        
        .form-header.header-layout-split-reverse .header-content-section {{
            flex: 1;
            order: 1;
        }}
        
        .form-header.header-layout-split-reverse .header-logo-section {{
            flex: 0 0 auto;
            margin-bottom: 0;
            order: 2;
        }}
        
        .form-header.header-layout-split-reverse .form-logo {{
            margin: 0;
            max-width: 120px;
            max-height: 120px;
        }}
        
        /* Inline Layout (Logo, Title, Description in Row) */
        .form-header.header-layout-inline {{
            display: flex;
            align-items: center;
            gap: 20px;
            text-align: left;
            padding: 30px;
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            color: white;
        }}
        
        .form-header.header-layout-inline h1 {{
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .form-header.header-layout-inline p {{
            color: rgba(255,255,255,0.9);
        }}
        
        .form-header.header-layout-inline .header-logo-section {{
            flex: 0 0 auto;
            margin-bottom: 0;
        }}
        
        .form-header.header-layout-inline .header-content-section {{
            flex: 1;
        }}
        
        .form-header.header-layout-inline .form-logo {{
            margin: 0;
            max-width: 80px;
            max-height: 80px;
        }}
        
        .form-header.header-layout-inline h1 {{
            margin-bottom: 5px;
            font-size: 24px;
        }}
        
        .form-header.header-layout-inline p {{
            font-size: 14px;
        }}
        
        /* Stacked Layout (All Elements Stacked) */
        .form-header.header-layout-stacked {{
            text-align: center;
            padding: 40px 30px;
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            color: white;
        }}
        
        .form-header.header-layout-stacked h1 {{
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .form-header.header-layout-stacked p {{
            color: rgba(255,255,255,0.9);
        }}
        
        .form-header.header-layout-stacked .header-logo-section {{
            margin-bottom: 20px;
        }}
        
        .form-header.header-layout-stacked .header-content-section {{
            align-items: center;
        }}
        
        /* Compact Layout (Logo and Title Side by Side) */
        .form-header.header-layout-compact {{
            display: flex;
            align-items: center;
            gap: 20px;
            text-align: left;
            padding: 25px 30px;
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            color: white;
        }}
        
        .form-header.header-layout-compact h1 {{
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        .form-header.header-layout-compact p {{
            color: rgba(255,255,255,0.9);
        }}
        
        .form-header.header-layout-compact .header-logo-section {{
            flex: 0 0 auto;
            margin-bottom: 0;
        }}
        
        .form-header.header-layout-compact .header-content-section {{
            flex: 1;
        }}
        
        .form-header.header-layout-compact .form-logo {{
            margin: 0;
            max-width: 60px;
            max-height: 60px;
        }}
        
        .form-header.header-layout-compact h1 {{
            margin-bottom: 5px;
            font-size: 22px;
        }}
        
        .form-header.header-layout-compact .header-description {{
            font-size: 13px;
            margin-top: 5px;
        }}
        
        /* Minimal Layout (Title Only with Border) */
        .form-header.header-layout-minimal {{
            background: transparent;
            color: {text_color};
            border-bottom: 2px solid {primary_color};
            padding: 20px 30px;
            text-align: left;
        }}
        
        .form-header.header-layout-minimal h1 {{
            color: {text_color};
            text-shadow: none;
            margin: 0;
            font-size: 24px;
        }}
        
        /* Banner Layout (Large Banner Style) */
        .form-header.header-layout-banner {{
            padding: 60px 30px;
            background: linear-gradient(135deg, {header_primary_color} 0%, {header_secondary_color} 100%);
            position: relative;
            overflow: hidden;
            text-align: center;
        }}
        
        .form-header.header-layout-banner::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            pointer-events: none;
        }}
        
        .form-header.header-layout-banner h1 {{
            font-size: 36px;
            position: relative;
            z-index: 1;
        }}
        
        .form-header.header-layout-banner p {{
            font-size: 18px;
            position: relative;
            z-index: 1;
        }}
        
        .form-body {{
            padding: 40px 30px;
        }}
        
        .form-group {{
            margin-bottom: 24px;
        }}
        
        .form-group label {{
            display: block;
            margin-bottom: 8px;
            color: {text_color};
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .form-group label::after {{
            content: '';
            display: inline-block;
            width: 4px;
            height: 4px;
            background: {primary_color};
            border-radius: 50%;
            margin-left: 6px;
            vertical-align: middle;
        }}
        
        .form-group input[type="text"],
        .form-group input[type="email"],
        .form-group input[type="tel"],
        .form-group input[type="number"],
        .form-group input[type="date"],
        .form-group input[type="time"],
        .form-group input[type="file"],
        .form-group select,
        .form-group textarea {{
            width: 100%;
            padding: 14px 16px;
            border: 2px solid {input_border};
            border-radius: 10px;
            font-size: 15px;
            font-family: inherit;
            transition: all 0.3s ease;
            background: {input_bg};
            color: {text_color};
        }}
        
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {{
            outline: none;
            border-color: {primary_color};
            background: {container_bg};
            box-shadow: 0 0 0 4px rgba({primary_color_rgb}, 0.1);
        }}
        
        .form-group input[type="file"] {{
            padding: 12px;
            cursor: pointer;
        }}
        
        .form-group textarea {{
            min-height: 120px;
            resize: vertical;
            font-family: inherit;
        }}
        
        .form-group .error {{
            color: #e74c3c;
            font-size: 13px;
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .form-group .error::before {{
            content: '⚠';
            font-size: 16px;
        }}
        
        .form-group .success {{
            color: #27ae60;
            font-size: 13px;
            margin-top: 6px;
        }}
        
        .submit-button {{
            width: 100%;
            background: linear-gradient(135deg, {primary_color} 0%, {secondary_color} 100%);
            color: white;
            padding: 16px 32px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba({primary_color_rgb}, 0.3);
            margin-top: 10px;
        }}
        
        .submit-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba({primary_color_rgb}, 0.4);
        }}
        
        .submit-button:active {{
            transform: translateY(0);
        }}
        
        .submit-button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        
        .progress-bar {{
            height: 6px;
            background-color: #e9ecef;
            border-radius: 10px;
            margin-top: 20px;
            overflow: hidden;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
        }}
        
        .progress-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, {primary_color} 0%, {secondary_color} 100%);
            border-radius: 10px;
            transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 2px 4px rgba({primary_color_rgb}, 0.3);
        }}
        
        .captcha-container {{
            margin-top: 24px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            text-align: center;
        }}
        
        .captcha-image {{
            width: 200px;
            height: 70px;
            margin: 0 auto 12px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .captcha-refresh {{
            background: {primary_color};
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            border: none;
            transition: all 0.2s ease;
        }}
        
        .captcha-refresh:hover {{
            background: {secondary_color};
            transform: scale(1.05);
        }}
        
        .captcha-error {{
            color: #e74c3c;
            font-size: 13px;
            margin-top: 10px;
            display: block;
        }}
        
        #submission_message {{
            margin-top: 24px;
            padding: 0;
            border-radius: 10px;
            font-weight: 500;
        }}
        
        #submission_message .success,
        #submission_message .error,
        #submission_message .info {{
            animation: slideIn 0.3s ease-out;
        }}
        
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateY(-10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(-10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            body {{
                padding: 20px 10px;
            }}
            
            .container {{
                border-radius: 12px;
            }}
            
            .form-header {{
                padding: 30px 20px;
            }}
            
            .form-header h1 {{
                font-size: 24px;
            }}
            
            .form-body {{
                padding: 30px 20px;
            }}
            
            .form-group {{
                margin-bottom: 20px;
            }}
            
            /* Mobile: Sidebar positions become full width */
            .position-left .container,
            .position-right .container {{
                max-width: 100%;
                margin: 0;
                float: none;
            }}
            
            /* Mobile: Modal adjustments */
            .position-modal {{
                padding: 10px;
            }}
            
            .position-modal .container {{
                max-width: 100%;
                max-height: 95vh;
            }}
        }}
        
        {custom_css}
    </style>
</head>
<body class="theme-{theme} layout-{layout} position-{position}">
    <div class="container">
        {modal_close_button}
        {header_html}
        
        <div class="form-body">
            <form id="dynamic-form" method="POST" action="#" onsubmit="return false;">
                <input type="hidden" name="security_token" value="{security_token}">
                
                {fields}
                
                {captcha_field}
                
                <button type="submit" class="submit-button">{submit_button_text}</button>
            </form>
            
            {progress_bar_html}
            
            <div id="submission_message" style="display: none; min-height: 50px;"></div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const form = document.getElementById('dynamic-form');
            const submitButton = form.querySelector('.submit-button');
            const progressBar = document.getElementById('progress_bar');
            const submissionMessage = document.getElementById('submission_message');
            const captchaError = document.getElementById('captcha_error'); // May be null if captcha is disabled
            
            // Verify elements exist
            if (!submissionMessage) {{
                console.error('Submission message element not found in DOM');
            }}
            
            let submissionInProgress = false;
            
            // Initialize progress bar only if it exists
            if (progressBar) {{
                progressBar.style.width = '0%';
            }}
            
            // Setup progress tracking (only if progress bar exists)
            function setupProgressTracking() {{
                if (!progressBar) return;
                
                // Get all form fields (excluding hidden, submit button, security_token, captcha)
                const formFields = form.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([name="security_token"]):not([name="captcha_response"]), select, textarea');
                const totalFields = formFields.length;
                
                if (totalFields === 0) {{
                    progressBar.style.width = '100%';
                    return;
                }}
                
                function updateProgress() {{
                    let filledFields = 0;
                    
                    formFields.forEach(field => {{
                        let isFilled = false;
                        
                        if (field.type === 'checkbox') {{
                            // Checkbox is considered filled if checked
                            isFilled = field.checked;
                        }} else if (field.type === 'radio') {{
                            // Radio is filled if any radio with same name is checked
                            const radios = form.querySelectorAll('input[type="radio"][name="' + field.name + '"]');
                            isFilled = Array.from(radios).some(radio => radio.checked);
                        }} else if (field.type === 'file') {{
                            // File is filled if file is selected
                            isFilled = field.files && field.files.length > 0;
                        }} else {{
                            // Text, email, number, select, textarea - filled if has value
                            isFilled = field.value && field.value.trim() !== '';
                        }}
                        
                        if (isFilled) {{
                            filledFields++;
                        }}
                    }});
                    
                    // Calculate progress percentage
                    const progressPercent = totalFields > 0 ? Math.round((filledFields / totalFields) * 100) : 0;
                    progressBar.style.width = progressPercent + '%';
                }}
                
                // Update progress on field changes
                formFields.forEach(field => {{
                    field.addEventListener('input', updateProgress);
                    field.addEventListener('change', updateProgress);
                    
                    // For checkboxes and radios, also listen to click
                    if (field.type === 'checkbox' || field.type === 'radio') {{
                        field.addEventListener('click', updateProgress);
                    }}
                }});
                
                // Initial progress update
                updateProgress();
            }}
            
            // Initialize progress tracking (only if progress bar exists)
            if (progressBar) {{
                setupProgressTracking();
            }}

            function showMessage(message, type = 'info') {{
                if (!submissionMessage) {{
                    console.error('Submission message element not found');
                    alert(message); // Fallback to alert if element not found
                    return;
                }}
                
                // Clear any previous messages
                submissionMessage.innerHTML = '';
                
                // Set message content with appropriate styling
                const messageClass = type === 'success' ? 'success' : (type === 'error' ? 'error' : 'info');
                const icon = type === 'success' ? '✓' : (type === 'error' ? '✕' : 'ℹ');
                const bgColor = type === 'success' ? '#d4edda' : (type === 'error' ? '#f8d7da' : '#d1ecf1');
                const textColor = type === 'success' ? '#155724' : (type === 'error' ? '#721c24' : '#0c5460');
                const borderColor = type === 'success' ? '#c3e6cb' : (type === 'error' ? '#f5c6cb' : '#bee5eb');
                const iconBg = type === 'success' ? '#28a745' : (type === 'error' ? '#dc3545' : '#17a2b8');
                
                submissionMessage.innerHTML = '<div class="' + messageClass + '" style="' +
                    'padding: 18px 20px; ' +
                    'margin: 20px 0; ' +
                    'border-radius: 8px; ' +
                    'background: linear-gradient(135deg, ' + bgColor + ' 0%, ' + bgColor + 'dd 100%); ' +
                    'color: ' + textColor + '; ' +
                    'border-left: 4px solid ' + borderColor + '; ' +
                    'box-shadow: 0 2px 8px rgba(0,0,0,0.1); ' +
                    'font-weight: 500; ' +
                    'font-size: 15px; ' +
                    'line-height: 1.6; ' +
                    'display: flex; ' +
                    'align-items: center; ' +
                    'gap: 12px; ' +
                    'animation: slideIn 0.3s ease-out;' +
                    '">' +
                    '<span style="' +
                        'display: inline-flex; ' +
                        'align-items: center; ' +
                        'justify-content: center; ' +
                        'width: 28px; ' +
                        'height: 28px; ' +
                        'border-radius: 50%; ' +
                        'background-color: ' + iconBg + '; ' +
                        'color: white; ' +
                        'font-size: 14px; ' +
                        'font-weight: bold; ' +
                        'flex-shrink: 0;' +
                    '">' + icon + '</span>' +
                    '<span style="flex: 1;">' + message + '</span>' +
                    '</div>';
                submissionMessage.style.display = 'block';
                submissionMessage.style.visibility = 'visible';
                submissionMessage.style.opacity = '1';
                
                // Scroll to message to ensure it's visible
                setTimeout(() => {{
                    submissionMessage.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}, 100);
                
                // Hide after 10 seconds for success, 15 seconds for errors
                const timeout = type === 'success' ? 10000 : 15000;
                setTimeout(() => {{
                    submissionMessage.style.opacity = '0';
                    setTimeout(() => {{
                        submissionMessage.style.display = 'none';
                    }}, 300);
                }}, timeout);
            }}

            function handleError(message) {{
                showMessage(message, 'error');
                if (captchaError) {{
                    captchaError.textContent = message;
                    captchaError.style.display = 'block';
                }}
            }}

            function handleSuccess(message) {{
                showMessage(message, 'success');
                if (captchaError) {{
                    captchaError.textContent = '';
                    captchaError.style.display = 'none';
                }}
            }}

            function validateForm() {{
                let isValid = true;
                const errors = [];
                
                // Clear previous error styles
                const formGroups = form.querySelectorAll('.form-group');
                formGroups.forEach(group => {{
                    const errorDiv = group.querySelector('.field-error');
                    if (errorDiv) {{
                        errorDiv.remove();
                    }}
                    const input = group.querySelector('input, select, textarea');
                    if (input) {{
                        input.style.borderColor = '';
                    }}
                }});
                
                const formElements = form.elements;
                for (let i = 0; i < formElements.length; i++) {{
                    const element = formElements[i];
                    // Skip hidden fields, security_token, and captcha_response
                    if (!element.name || element.name === 'security_token' || element.name === 'captcha_response' || element.type === 'hidden') {{
                        continue;
                    }}
                    
                    const isRequired = element.hasAttribute('required');
                    let value = '';
                    
                    if (element.type === 'checkbox') {{
                        value = element.checked;
                    }} else if (element.type === 'radio') {{
                        // Check if any radio with this name is checked
                        const radios = form.querySelectorAll('input[type="radio"][name="' + element.name + '"]');
                        let radioChecked = false;
                        for (let r = 0; r < radios.length; r++) {{
                            if (radios[r].checked) {{
                                radioChecked = true;
                                value = radios[r].value;
                                break;
                            }}
                        }}
                        if (isRequired && !radioChecked) {{
                            isValid = false;
                            const label = form.querySelector('label[for="' + element.id + '"]') || form.querySelector('label');
                            errors.push((label ? label.textContent : element.name) + ' is required');
                            const formGroup = element.closest('.form-group');
                            if (formGroup) {{
                                element.style.borderColor = '#dc3545';
                                const errorDiv = document.createElement('div');
                                errorDiv.className = 'field-error';
                                errorDiv.style.color = '#dc3545';
                                errorDiv.style.fontSize = '0.9em';
                                errorDiv.style.marginTop = '5px';
                                errorDiv.textContent = (label ? label.textContent : element.name) + ' is required';
                                formGroup.appendChild(errorDiv);
                            }}
                        }}
                        continue; // Skip to next element for radio
                    }} else {{
                        value = element.value ? element.value.trim() : '';
                    }}
                    
                    // Check required fields
                    if (isRequired && !value && element.type !== 'checkbox') {{
                        isValid = false;
                        const label = form.querySelector('label[for="' + element.id + '"]');
                        errors.push((label ? label.textContent : element.name) + ' is required');
                        element.style.borderColor = '#dc3545';
                        const formGroup = element.closest('.form-group');
                        if (formGroup) {{
                            const errorDiv = document.createElement('div');
                            errorDiv.className = 'field-error';
                            errorDiv.style.color = '#dc3545';
                            errorDiv.style.fontSize = '0.9em';
                            errorDiv.style.marginTop = '5px';
                            errorDiv.textContent = (label ? label.textContent : element.name) + ' is required';
                            formGroup.appendChild(errorDiv);
                        }}
                    }}
                    
                    // Validate email format
                    if (element.type === 'email' && value && !/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(value)) {{
                        isValid = false;
                        const label = form.querySelector('label[for="' + element.id + '"]');
                        errors.push((label ? label.textContent : element.name) + ' must be a valid email address');
                        element.style.borderColor = '#dc3545';
                        const formGroup = element.closest('.form-group');
                        if (formGroup) {{
                            const errorDiv = document.createElement('div');
                            errorDiv.className = 'field-error';
                            errorDiv.style.color = '#dc3545';
                            errorDiv.style.fontSize = '0.9em';
                            errorDiv.style.marginTop = '5px';
                            errorDiv.textContent = 'Please enter a valid email address';
                            formGroup.appendChild(errorDiv);
                        }}
                    }}
                }}
                
                if (!isValid) {{
                    handleError('Please fix the errors in the form before submitting.');
                }}
                
                return isValid;
            }}

            function submitForm() {{
                if (submissionInProgress) {{
                    return;
                }}
                
                // Validate form before submission
                if (!validateForm()) {{
                    submissionInProgress = false;
                    return;
                }}
                
                submissionInProgress = true;
                // Set progress to 100% during submission
                if (progressBar) {{
                    progressBar.style.width = '100%';
                }}
                if (captchaError) {{
                    captchaError.textContent = '';
                    captchaError.style.display = 'none';
                }}

                const formData = new FormData(form);
                const securityToken = formData.get('security_token');
                const captchaResponse = formData.get('captcha_response');

                if (!securityToken) {{
                    handleError('Security token is missing.');
                    submissionInProgress = false;
                    return;
                }}

                // Only validate captcha if it's enabled
                if ({enable_captcha} && !captchaResponse) {{
                    handleError('Please complete the reCAPTCHA.');
                    submissionInProgress = false;
                    return;
                }}

                // Collect all form field values
                const formFields = {{}};
                const processedNames = new Set(); // Track processed field names to avoid duplicates
                const formElements = form.elements;
                
                for (let i = 0; i < formElements.length; i++) {{
                    const element = formElements[i];
                    // Skip security_token, captcha_response, and hidden fields
                    if (!element.name || element.name === 'security_token' || element.name === 'captcha_response' || element.type === 'hidden') {{
                        continue;
                    }}
                    
                    // Skip if already processed (for radio buttons)
                    if (processedNames.has(element.name)) {{
                        continue;
                    }}
                    
                    if (element.type === 'checkbox') {{
                        formFields[element.name] = element.checked;
                        processedNames.add(element.name);
                    }} else if (element.type === 'radio') {{
                        // Find the checked radio button with this name
                        const radios = form.querySelectorAll('input[type="radio"][name="' + element.name + '"]');
                        let checkedValue = '';
                        for (let r = 0; r < radios.length; r++) {{
                            if (radios[r].checked) {{
                                checkedValue = radios[r].value;
                                break;
                            }}
                        }}
                        formFields[element.name] = checkedValue;
                        processedNames.add(element.name);
                    }} else if (element.type === 'file') {{
                        // File handling is done separately via upload endpoint
                        if (element.files && element.files.length > 0) {{
                            formFields[element.name] = element.files[0].name;
                        }}
                        processedNames.add(element.name);
                    }} else {{
                        const value = element.value ? element.value.trim() : '';
                        // Always include the field, even if empty (server needs to know all fields)
                        formFields[element.name] = value;
                        processedNames.add(element.name);
                    }}
                }}
                
                // Log collected form data for debugging
                console.log('Collected form fields:', formFields);

                fetch('/dynamic-form/submit/{token}', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest' // For CORS
                    }},
                    body: JSON.stringify({{
                        'security_token': securityToken,
                        'captcha_response': captchaResponse || '',
                        'form_data': formFields
                    }})
                }})
                .then(response => {{
                    if (!response.ok) {{
                        return response.json().then(err => {{ throw new Error(err.error || 'Submission failed'); }});
                    }}
                    return response.json();
                }})
                .then(data => {{
                    if (data.success) {{
                        // Show success message first
                        const successMsg = data.message || 'Form submitted successfully!';
                        showMessage(successMsg, 'success');
                        
                        // Clear captcha error if exists
                        if (captchaError) {{
                            captchaError.textContent = '';
                            captchaError.style.display = 'none';
                        }}
                        
                        // Reset form after a short delay to ensure message is visible
                        setTimeout(() => {{
                            form.reset(); // Clear form fields
                            // Reset progress bar after form reset
                            if (progressBar) {{
                                progressBar.style.width = '0%';
                            }}
                            // Re-initialize progress tracking after reset
                            setupProgressTracking();
                        }}, 500);
                        
                        submissionInProgress = false;
                    }} else {{
                        handleError(data.error || 'An error occurred while submitting the form.');
                        submissionInProgress = false;
                        // Recalculate progress after error
                        setupProgressTracking();
                    }}
                }})
                .catch(error => {{
                    handleError(error.message || 'An unexpected error occurred.');
                    submissionInProgress = false;
                    // Recalculate progress after error
                    setupProgressTracking();
                }});
            }}

            // Prevent default form submission and use AJAX
            form.addEventListener('submit', function(event) {{
                event.preventDefault();
                event.stopPropagation();
                submitForm();
            }});
            
            // Also handle button click (in case form submit doesn't fire)
            submitButton.addEventListener('click', function(event) {{
                event.preventDefault();
                event.stopPropagation();
                submitForm();
            }});

            // Handle file uploads
            form.addEventListener('change', function(event) {{
                const fileInput = event.target;
                if (fileInput.type === 'file') {{
                    const file = fileInput.files[0];
                    if (file) {{
                        const reader = new FileReader();
                        reader.onload = function(e) {{
                            const formData = new FormData(form);
                            formData.append('file', file);
                            fetch('/dynamic-form/upload/{token}', {{
                                method: 'POST',
                                headers: {{
                                    'X-Requested-With': 'XMLHttpRequest' // For CORS
                                }},
                                body: formData
                            }})
                            .then(response => {{
                                if (!response.ok) {{
                                    return response.json().then(err => {{ throw new Error(err.error || 'File upload failed'); }});
                                }}
                                return response.json();
                            }})
                            .then(data => {{
                                if (data.success) {{
                                    showMessage('File uploaded successfully!');
                                    // Optionally, update the form_data object with the attachment ID
                                    // This requires a more complex state management if you want to re-render the form
                                    // For now, we'll just show a success message.
                                }} else {{
                                    handleError(data.error);
                                }}
                            }})
                            .catch(error => {{
                                handleError(error.message || 'File upload failed');
                            }});
                        }};
                        reader.readAsDataURL(file);
                    }}
                }}
            }});

            // Handle form reset (e.g., after successful submission)
            // Note: We don't clear the success message on reset - let it stay visible
            form.addEventListener('reset', function() {{
                if (captchaError) {{
                    captchaError.textContent = '';
                    captchaError.style.display = 'none';
                }}
                // Reset progress bar on form reset
                if (progressBar) {{
                    progressBar.style.width = '0%';
                }}
                // Re-initialize progress tracking after reset
                setTimeout(() => {{
                    setupProgressTracking();
                }}, 100);
            }});
        }});
    </script>
</body>
</html>
""".format(
            form_name=form.name or '',
            header_html=header_html,
            progress_bar_html=progress_bar_html,
            token=token or '',
            security_token=form.security_token or '',
            theme=theme,
            layout=layout,
            position=position,
            modal_close_button=modal_close_button,
            primary_color=final_primary_color,
            secondary_color=final_secondary_color,
            header_primary_color=header_primary_color,
            header_secondary_color=header_secondary_color,
            primary_color_rgb=primary_color_rgb,
            body_background=body_background,
            container_bg=container_bg,
            text_color=text_color,
            input_bg=input_bg,
            input_border=input_border,
            custom_css=custom_css,
            enable_captcha=enable_captcha,
            submit_button_text=submit_button_text,
            fields=self._generate_form_fields_html(form),
            captcha_field=self._generate_captcha_field_html(form) if form.enable_captcha else ""
        )
        return html_content
    
    def _generate_form_fields_html(self, form):
        """Generates the HTML for individual form fields."""
        field_html = ""
        for field in form.field_ids.filtered(lambda f: f.active):
            field_html += self._generate_single_field_html(field)
        return field_html
    
    def _generate_single_field_html(self, field):
        """Generate HTML for a single form field"""
        try:
            field_type = field.field_type or 'text'
            field_name = field.name or f"field_{field.id}"
            field_label = field.label or field_name
            field_required = "required" if field.required else ""
            field_placeholder = field.placeholder or ""
            field_help_text = field.help_text or ""
            help_text_html = ""
            if field_help_text:
                help_text_html = f'<small class="field-help-text" style="display: block; font-size: 12px; color: #666; margin-top: 5px;">{field_help_text}</small>'
        except Exception as e:
            _logger.error("Error accessing field attributes for field %s: %s", field.id if hasattr(field, 'id') else 'unknown', str(e))
            # Return a safe default field
            return f"""
                <div class="form-group">
                    <label>Field Error</label>
                    <input type="text" name="field_error" disabled placeholder="Error loading field">
                </div>
            """
        
        if field_type == 'text':
            return f"""
                <div class="form-group">
                    <label for="{field_name}">{field_label}</label>
                    <input type="text" id="{field_name}" name="{field_name}" 
                           placeholder="{field_placeholder}" {field_required}>
                    {help_text_html}
                </div>
            """
        elif field_type == 'email':
            return f"""
                <div class="form-group">
                    <label for="{field_name}">{field_label}</label>
                    <input type="email" id="{field_name}" name="{field_name}" 
                           placeholder="{field_placeholder}" {field_required}>
                    {help_text_html}
                </div>
            """
        elif field_type == 'phone':
            return f"""
                <div class="form-group">
                    <label for="{field_name}">{field_label}</label>
                    <input type="tel" id="{field_name}" name="{field_name}" 
                           placeholder="{field_placeholder}" {field_required}>
                    {help_text_html}
                </div>
            """
        elif field_type == 'textarea':
            return f"""
                <div class="form-group">
                    <label for="{field_name}">{field_label}</label>
                    <textarea id="{field_name}" name="{field_name}" 
                              placeholder="{field_placeholder}" rows="4" {field_required}></textarea>
                    {help_text_html}
                </div>
            """
        elif field_type == 'select':
            options_html = ""
            if field.options:
                for option in field.options.split('\n'):
                    if option.strip():
                        options_html += f'<option value="{option.strip()}">{option.strip()}</option>'
            
            return f"""
                <div class="form-group">
                    <label for="{field_name}">{field_label}</label>
                    <select id="{field_name}" name="{field_name}" {field_required}>
                        <option value="">Select an option</option>
                        {options_html}
                    </select>
                    {help_text_html}
                </div>
            """
        elif field_type == 'radio':
            options_html = ""
            if field.options:
                for option in field.options.split('\n'):
                    if option.strip():
                        options_html += f"""
                            <div>
                                <input type="radio" id="{field_name}_{option.strip().replace(' ', '_')}" 
                                       name="{field_name}" value="{option.strip()}" {field_required}>
                                <label for="{field_name}_{option.strip().replace(' ', '_')}">{option.strip()}</label>
                            </div>
                        """
            
            return f"""
                <div class="form-group">
                    <label>{field_label}</label>
                    {options_html}
                    {help_text_html}
                </div>
            """
        else:
            return f"""
                <div class="form-group">
                    <label for="{field_name}">{field_label}</label>
                    <input type="text" id="{field_name}" name="{field_name}" 
                           placeholder="{field_placeholder}" {field_required}>
                    {help_text_html}
                </div>
            """
    
    def _generate_captcha_field_html(self, form):
        """Generate HTML for captcha field if enabled"""
        if not form.enable_captcha:
            return ""
        
        return f"""
            <div class="form-group">
                <label for="captcha_response">reCAPTCHA:</label>
                <div class="captcha-container">
                    <img src="/dynamic-form/view/{form.token}.js" alt="reCAPTCHA" class="captcha-image">
                    <div class="captcha-refresh" onclick="this.src='/dynamic-form/view/{form.token}.js?' + Math.random()">Refresh</div>
                    <input type="text" name="captcha_response" id="captcha_response" required>
                    <div id="captcha_error" class="captcha-error"></div>
                </div>
            </div>
        """
    
    @http.route('/dynamic-form/analytics/<string:token>', type='json', auth='user')
    def get_analytics(self, token, **kwargs):
        """Get form analytics (requires authentication)"""
        try:
            form = request.env['dynamic.form'].sudo().search([('token', '=', token)])
            if not form:
                return {'success': False, 'error': 'Form not found'}
            
            # Get analytics data
            analytics = {
                'view_count': form.view_count,
                'submission_count': form.submission_count,
                'conversion_rate': form.conversion_rate,
                'recent_submissions': [],
            }
            
            # Get recent submissions
            recent_submissions = form.submission_ids.sorted('create_date', reverse=True)[:10]
            for submission in recent_submissions:
                analytics['recent_submissions'].append({
                    'id': submission.name,
                    'date': submission.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'state': submission.state,
                    'data': submission.parsed_data,
                })
            
            return {'success': True, 'analytics': analytics}
            
        except Exception as e:
            _logger.error("Error getting analytics: %s", str(e))
            return {'success': False, 'error': str(e)}
