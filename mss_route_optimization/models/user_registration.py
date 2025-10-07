from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import json
from odoo.exceptions import AccessError
import logging
import re
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}$", re.I)
BLACKLIST_DOMAINS = {"example.com", "odoo.com", "yopmial.com"}

class UserRegistration(models.Model):
    _name = 'mss_route_optimization.user.registration'
    _description = 'User Registration'

    partner_id = fields.Many2one('res.partner', string="User Contact")
    company_id = fields.Many2one('res.company', string="Company")

    # Editable Fields
    name = fields.Char(string="Name")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    company_name = fields.Char(string="Business Legal Name")
    country_id = fields.Many2one('res.country', string="Country")
    employee_count = fields.Selection([
        ('1-5', '1-5'),
        ('5-10', '5-10'),
        ('10-50', '10-50'),
        ('50-100', '50-100'),
        ('100-200', '100-200'),
        ('200-500', '200-500'),
        ('500-1000', '500-1000'),
        ('1000+', '1000+')
    ], string="Employee Count")

    customer_type = fields.Selection([
        ('mostly businesses', 'Mostly Businesses'), 
        ('mostly residential', 'Mostly Residential'),
        ('businesses and residential equally', 'Businesses and Residential Equally'),
    ], string="Customer Type")

    business_type = fields.Selection([
        ('distributer', 'Distributer'),
        ('manufacturer', 'Manufacturer'),
        ('others', 'Others'),
        ('producer', 'Producer'),
        ('retailer', 'Retailer'),
        ('supplier', 'Supplier'),
        ('wholesaler', 'WholeSaler'),
    ], string="What best describes your business?")
    
    delivery_method = fields.Selection([
        ('own_fleet', 'Own Fleet (Company-Owned Trucks & Drivers)'),
        ('3pl', 'Third-Party Logistics (FedEx, UPS, DHL, Local 3PL etc)'),
        ('hybrid', 'Hybrid Model (Own Fleet + 3PL Vendors)'),
        ('dropshipping', 'Dropshipping (Products shipped directly from suppliers)')
    ], string="How do you distribute/deliver your products?")

    annual_turnover = fields.Selection([
        ('<$1m', '<$1M'),
        ('$1m-$5m', '$1M-$5M'),
        ('$5m-$10m', '$5M-$10M'),
        ('$10m-$50m', '$10M-$50M'),
        ('$50m-$100m', '$50M-$100M'),
        ('$100m+', '$100M+'),
    ], string="Annual Turnover")

    # Hidden original values
    actual_name = fields.Char(string="Original Name")
    actual_email = fields.Char(string="Original Email")
    actual_phone = fields.Char(string="Original Phone")
    actual_company_name = fields.Char(string="Original Business Name")
    actual_country_id = fields.Many2one('res.country', string="Original Country")

    google_map_api_key = fields.Char(string="Google Maps API Key")
    route_api = fields.Char(string="Route API Key")
    registered_date = fields.Datetime(string="Registered On", default=fields.Datetime.now)
    usage_display = fields.Char(string="Usage Display")


class UserRegisterWizard(models.TransientModel):
    _name = 'user.register.wizard'
    _description = 'Activate Plugin'

    otp = fields.Char(string="OTP")
    is_verified = fields.Boolean(string="OTP Verified", default=False, readonly=True)
    otp_sent_at = fields.Datetime(string="OTP Sent At", readonly=True)
    otp_resend_count = fields.Integer(string="OTP Resent", readonly=True, default=0)
    stage = fields.Selection(
        [('draft','Draft'), ('otp_sent','OTP Sent'), ('verified','Verified')],
        compute='_compute_stage', store=False
    )

    # Hidden (original) fields
    actual_name = fields.Char(string="Actual Name", readonly=True)
    actual_email = fields.Char(string="Actual Email", readonly=True)
    actual_phone = fields.Char(string="Actual Phone", readonly=True)
    actual_company_name = fields.Char(string="Actual Company Name", readonly=True)
    actual_country = fields.Many2one('res.country', string="Actual Country", readonly=True)

    # Editable fields
    name = fields.Char(string="Name")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    company_name = fields.Char(string="Business Legal Name")
    country_id = fields.Many2one('res.country', string="Country")

    employee_count = fields.Selection([
        ('1-5', '1-5'),
        ('5-10', '5-10'),
        ('10-50', '10-50'),
        ('50-100', '50-100'),
        ('100-200', '100-200'),
        ('200-500', '200-500'),
        ('500-1000', '500-1000'),
        ('1000+', '1000+')
    ], string="Employee Count")

    customer_type = fields.Selection([
        ('mostly businesses', 'Mostly Businesses'), 
        ('mostly residential', 'Mostly Residential'),
        ('businesses and residential equally', 'Businesses and Residential Equally'),
    ], string="Customer Type")

    business_type = fields.Selection([
        ('distributer', 'Distributer'),
        ('manufacturer', 'Manufacturer'),
        ('others', 'Others'),
        ('producer', 'Producer'),
        ('retailer', 'Retailer'),
        ('supplier', 'Supplier'),
        ('wholesaler', 'WholeSaler'),
    ], string="What best describes your business?")

    delivery_method = fields.Selection([
        ('own_fleet', 'Own Fleet (Company-Owned Trucks & Drivers)'),
        ('3pl', 'Third-Party Logistics (FedEx, UPS, DHL, Local 3PL etc)'),
        ('hybrid', 'Hybrid Model (Own Fleet + 3PL Vendors)'),
        ('dropshipping', 'Dropshipping (Products shipped directly from suppliers)')
    ], string="How do you distribute/deliver your products?")
    annual_turnover = fields.Selection([
        ('<$1m', '<$1M'),
        ('$1m-$5m', '$1M-$5M'),
        ('$5m-$10m', '$5M-$10M'),
        ('$10m-$50m', '$10M-$50M'),
        ('$50m-$100m', '$50M-$100M'),
        ('$100m+', '$100M+'),
    ], string="Annual Turnover")


    # Technical fields
    partner_id = fields.Many2one('res.partner', string="User", default=lambda self: self.env.user.partner_id)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    google_map_api_key = fields.Char(string="Google Maps API Key")
    route_api = fields.Char(string="Route API Key")

    @api.depends('otp_sent_at', 'is_verified')
    def _compute_stage(self):
        for r in self:
            r.stage = 'verified' if r.is_verified else ('otp_sent' if r.otp_sent_at else 'draft')
    def _assert_valid_email(self):
        self.ensure_one()
        email = (self.email or "").strip()
        if not email:
            raise UserError("Enter your email first.")
        if not EMAIL_RE.match(email):
            raise UserError("Please enter a valid email address (e.g. name@example.com).")

        # domain blacklist (blocks exact domain and subdomains)
        domain = email.split('@')[-1].lower()
        if domain in BLACKLIST_DOMAINS or any(domain.endswith('.' + d) for d in BLACKLIST_DOMAINS):
            raise UserError("Please use a non-blacklisted email domain.")

        # normalize (optional)
        self.email = email

    @api.constrains('email')
    def _constrains_email(self):
        for rec in self:
            if rec.email:
                e = rec.email.strip()
                if not EMAIL_RE.match(e):
                    raise ValidationError("Please enter a valid email address.")
                domain = e.split('@')[-1].lower()
                if domain in BLACKLIST_DOMAINS or any(domain.endswith('.' + d) for d in BLACKLIST_DOMAINS):
                    raise ValidationError("Please use a non-blacklisted email domain.")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user = self.env.user
        partner = user.partner_id
        company = user.company_id
        config = self.env['ir.config_parameter'].sudo()

        # Original values
        res['actual_name'] = partner.name
        res['actual_email'] = partner.email
        res['actual_phone'] = partner.phone
        res['actual_company_name'] = company.name
        res['actual_country'] = partner.country_id.id

        # Prefilled editable
        # res['name'] = partner.name
        # res['email'] = False
        # res['phone'] = partner.phone
        # res['company_name'] = company.name
        # res['country_id'] = partner.country_id.id

        res['google_map_api_key'] = config.get_param('address_autocomplete_gmap_widget.google_map_api_key', '')
        res['route_api'] = config.get_param('mss_route_optimization.route_api', '')

        return res
        
    @api.onchange('email')
    def _onchange_email(self):
        # changing email invalidates previous OTP/verification
        self.is_verified = False
        self.otp = False
        self.otp_sent_at = False
        self.otp_resend_count = 0

    @api.constrains('name', 'company_name')
    def _check_name_company(self):
        for rec in self:
            if rec.name and rec.name.strip().lower() == 'administrator':
                raise ValidationError("Please enter your full name instead of 'Administrator'.")
            if rec.company_name and rec.company_name.strip().lower() == 'my company':
                raise ValidationError("Please provide your real company name instead of 'My Company'.")

    def _require_fields(self, fields_list, stage):
        self.ensure_one()
        missing = []
        for f in fields_list:
            val = getattr(self, f)
            if not val or (isinstance(val, str) and not val.strip()):
                missing.append(self._fields[f].string or f)
        if missing:
            raise UserError(f"{stage}: please fill the following: {', '.join(missing)}")
    def action_register(self):
        # if self.env.user.name == "Administrator":
        #     raise UserError("Please enter your full name instead of the default name 'Administrator'.")
        # if self.company_name.strip().lower() == "my company":
        #     raise UserError("Kindly provide your company's actual name in place of the default 'My Company'")
        if not self.email:
            raise UserError("Email is required.")
        required_for_activation = [
                'company_name', 'country_id',
                'employee_count', 'customer_type',
                'business_type', 'delivery_method',
            ]
        self._require_fields(required_for_activation, "Activate")
        registration = self.env['mss_route_optimization.user.registration'].create({
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'google_map_api_key': self.google_map_api_key,
            'route_api': self.route_api,

            # New values
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'company_name': self.company_name,
            'country_id': self.country_id.id,
            'employee_count': self.employee_count,
            'customer_type': self.customer_type,
            'business_type': self.business_type,
            'delivery_method': self.delivery_method,
            'annual_turnover': self.annual_turnover or "",

            # Original values
            'actual_name': self.actual_name,
            'actual_email': self.actual_email,
            'actual_phone': self.actual_phone,
            'actual_company_name': self.actual_company_name,
            'actual_country_id': self.actual_country.id,
        })

        config = self.env['ir.config_parameter'].sudo()
        if self.google_map_api_key:
            config.set_param('address_autocomplete_gmap_widget.google_map_api_key', self.google_map_api_key)
        if self.route_api:
            config.set_param('mss_route_optimization.route_api', self.route_api)

        # External API call
        api_url = 'https://optimize.trakop.com/route/register-with-otp'
        user_info = {
            "name": self.name,
            "email": self.email,
            "otp": self.otp,
            "phone": self.phone,
            "company_name": self.company_name,
            "country": self.country_id.name if self.country_id else "",
            "employee_count": self.employee_count,
            "customer_type": self.customer_type,
            "business_type": self.business_type,
            "delivery_method": self.delivery_method,
            "annual_turnover": self.annual_turnover or "",
            "original_name": self.actual_name,
            "original_email": self.actual_email,
            "original_phone": self.actual_phone,
            "original_company_name": self.actual_company_name,
            "original_country": self.actual_country.name if self.actual_country else "",
        }
        _logger.info("Preparing to register user: %s", user_info)
        payload = {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'company_name': self.company_name,
            'country': self.country_id.name if self.country_id else "",
            'employee_count': self.employee_count,
            'customer_type': self.customer_type,
            'business_type': self.business_type,
            'delivery_method': self.delivery_method,
            'annual_turnover': self.annual_turnover or "",
            'original_name': self.actual_name,
            'original_email': self.actual_email,
            'original_phone': self.actual_phone if self.actual_phone else "",
            'original_company_name': self.actual_company_name,
            'original_country': self.actual_country.name if self.actual_country else "",
            }
        _logger.info("Registering user via API: %s", payload)

        try:
            response = requests.post(api_url, headers={'Content-Type': 'application/json'},
                                     data=json.dumps(payload), timeout=30)
            _logger.info("Response: %s - %s", response.status_code, response.text)
            response_json = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else {}

            if response.status_code == 200 and 'api_key' in response_json:
                api_key = response_json['api_key']
                config.set_param('mss_route_optimization.route_api', api_key)

                # 🔁 Log Usage API Call
                usage_payload = {
                    "email": self.email
                }
                try:
                    usage_response = requests.post(
                        "https://optimize.trakop.com/route/log-usage",
                        headers={'Content-Type': 'application/json'},
                        data=json.dumps(usage_payload),
                        timeout=20
                    )
                    _logger.info("Usage log response: %s - %s", usage_response.status_code, usage_response.text)
                    usage_data = usage_response.json() if usage_response.status_code == 200 else {}

                    usage_display = usage_data.get("usage_display", "N/A")

                except Exception as e:
                    _logger.error("Failed to log usage: %s", str(e))
                    usage_display = "N/A"
                registration.sudo().write({'route_api': api_key,'usage_display': usage_display})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': f'Registration successful! Usage: {usage_display}',
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }

            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Failed',
                        'message': f'Error {response.status_code}: {response.text}',
                        'type': 'danger',
                        'sticky': True,
                    }
                }

        except requests.exceptions.Timeout:
            _logger.error("Timeout while registering user: %s", self.email)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Error',
                    'message': 'Request timeout. Please try again.',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.error("Registration failed: %s", str(e), exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }


    def action_get_otp(self):
        self.ensure_one()
        self._assert_valid_email()
        self._require_fields(['name', 'email'], "Get OTP")
        
        if not self.email:
            raise UserError("Enter your email first.")
        
        api_url = 'https://optimize.trakop.com/route/send-otp'
        payload = {'email': self.email,'name': self.name}

        try:
            response = requests.post(
                api_url,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                data=json.dumps(payload),
                timeout=20
            )
            _logger.info("OTP send %s -> %s | %s", api_url, response.status_code, response.text)

            # Parse JSON from response
            response_data = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else {}

            if response.status_code == 200:
                # Check if the response indicates failure (success is false)
                if not response_data.get('success', True):  # if success is False
                    message = response_data.get('message', 'An unknown error occurred.')
                    # Only show the message from the API in the UserError
                    raise UserError(f"{message}")
                
                # If success, process OTP sending
                self.write({
                    'otp_sent_at': fields.Datetime.now(),
                    'stage': 'otp_sent'
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'OTP Sent',
                        'message': 'Check your email for the OTP.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                # Handle non-200 status codes (errors)
                error_message = response_data.get('message', 'An error occurred while processing your OTP request.')
                raise UserError(f"{error_message}")  # Only show the message from the API

        except requests.exceptions.Timeout:
            raise UserError("OTP request timed out. Please try again.")



    def _post_otp(self, endpoint, stage_label):
        self.ensure_one()
        self._assert_valid_email()
        self._require_fields(['name', 'email'], stage_label)

        payload = {'email': self.email}
        try:
            r = requests.post(
                endpoint,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                data=json.dumps(payload),
                timeout=20
            )
            _logger.info("%s -> %s | %s", stage_label, r.status_code, r.text)

            # Try to parse JSON body
            data = {}
            ct = r.headers.get('Content-Type', '')
            if 'application/json' in ct:
                try:
                    data = r.json()
                except Exception:
                    pass

            # Prefer explicit success flag
            api_success = data.get('success', None)
            message = data.get('message') or r.text or 'Request finished without message.'
            error_code = data.get('error_code')

            # Treat success:false as failure even if HTTP 200
            if api_success is False or (api_success is None and r.status_code not in (200, 201)):
                # Pretty-print wait time if rate limited
                wait_secs = None
                m = re.search(r'(\d+)\s*seconds', message or '')
                if m:
                    wait_secs = int(m.group(1))
                if wait_secs:
                    h = wait_secs // 3600
                    m_ = (wait_secs % 3600) // 60
                    s_ = wait_secs % 60
                    pretty = (f"{h}h {m_}m {s_}s" if h else f"{m_}m {s_}s")
                    raise UserError(f"{message} (~{pretty})")
                # Generic failure
                raise UserError(message)

            if r.status_code not in (200, 201):
                raise UserError(f"{stage_label} failed ({r.status_code}): {message}")

        except requests.exceptions.Timeout:
            raise UserError(f"{stage_label} timed out. Please try again.")
        except Exception:
            _logger.exception("%s error", stage_label)
            raise

        # Success -> mark state and notify
        self.write({'otp_sent_at': fields.Datetime.now(), 'stage': 'otp_sent'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': stage_label,
                'message': 'Check your email for the OTP.',
                'type': 'success',
                'sticky': False,
            }
        }
    def action_resend_otp(self):
        # backend-only: still require name + email
        self._require_fields(['name', 'email'], "Resend OTP")
        if self.is_verified:
            raise UserError("This email is already verified. No need to resend the OTP.")

        # optional cooldown
        COOLDOWN_SECONDS = 60
        now_dt = fields.Datetime.to_datetime(fields.Datetime.now())
        last_dt = fields.Datetime.to_datetime(self.otp_sent_at) if self.otp_sent_at else None
        if last_dt:
            elapsed = (now_dt - last_dt).total_seconds()
            if elapsed < COOLDOWN_SECONDS:
                wait = int(COOLDOWN_SECONDS - elapsed)
                raise UserError(f"Please wait {wait} seconds before resending the OTP.")

        res = self._post_otp(
            endpoint='https://optimize.trakop.com/route/resend-otp',  # ← your resend endpoint
            stage_label='Resend OTP'
        )
        self.write({'otp_resend_count': (self.otp_resend_count or 0) + 1})
        return res

    def action_verify_otp(self):
        self.ensure_one()
        self._assert_valid_email()
        self._require_fields(['name', 'email', 'otp'], "Verify OTP")
        if not self.email or not self.otp:
            raise UserError("Enter both Email and OTP.")

        api_url = 'https://optimize.trakop.com/route/verify-otp'
        payload = {'email': self.email, 'otp': self.otp}

        try:
            r = requests.post(
                api_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(payload),
                timeout=20
            )
            _logger.info("OTP verify -> %s | %s", r.status_code, r.text)

            # Parse JSON if present
            data = {}
            if r.headers.get('Content-Type', '').startswith('application/json'):
                try:
                    data = r.json()
                except Exception:
                    data = {}

            # Fail on non-200
            if r.status_code != 200:
                msg = data.get('message') or r.text
                raise UserError(f"OTP verification failed ({r.status_code}): {msg}")

            # Accept common success shapes, but default to True on 200 if none provided
            verified = data.get('verified', data.get('status') in ('ok', 'verified', True) if 'status' in data else True)
            if not verified:
                raise UserError("Incorrect OTP. Please try again.")

        except requests.exceptions.Timeout:
            raise UserError("Verification timed out. Please try again.")
        except Exception as e:
            _logger.exception("OTP verify error")
            raise UserError(f"OTP verification error: {e}")

        # Mark verified
        self.write({'is_verified': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Verified',
                'message': 'Email verified successfully.',
                'type': 'success',
                'sticky': False,
            }
        }

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def open_module_action(self):
        _logger.info(">>> open_module_action() called by user ID: %s (Partner ID: %s)", self.env.user.id, self.env.user.partner_id.id)

        registration = self.env['mss_route_optimization.user.registration'].sudo().search([
            ('route_api', '!=', False)
        ], limit=1)

        if registration:
            _logger.info(">>> Found registration record: ID=%s | route_api=%s", registration.id, registration.route_api)
        else:
            _logger.warning(">>> No registration record found for user: %s", self.env.user.id)

        if registration and registration.route_api:
            _logger.info(">>> route_api found. Granting access to module (action_traktop).")
            return self.env.ref('mss_route_optimization.action_traktop').sudo().read()[0]
        else:
            _logger.info(">>> route_api not found. Opening registration wizard.")
            _logger.info(">>> Admin user. Opening registration wizard.")
            return {
                'type': 'ir.actions.act_window',
                'name': 'Activate Plugin',
                'res_model': 'user.register.wizard',
                'view_mode': 'form',
                'target': 'new',
                'view_id': self.env.ref('mss_route_optimization.view_user_register_wizard').id,
            }

class OpenModuleTrigger(models.TransientModel):
    _name = 'open.module.trigger'
    _description = 'Trigger for opening Route Optimization module'        

