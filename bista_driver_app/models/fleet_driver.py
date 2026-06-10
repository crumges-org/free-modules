from odoo import api, fields, models, _, SUPERUSER_ID
import math
import random
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from odoo.http import request
# from odoo.addons.bista_driver_app.common import verify_driver_phone


class BistaFleetDriver(models.Model):
    _name = "fleet.driver"
    _description = "Driver"
    _order = "id desc"
    # _inherits = {'res.users': 'user_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']

    driver_name = fields.Char(tracking=True, string="Name")
    name = fields.Char( string="Name")
    driver_login = fields.Char(tracking=True, string="Phone")
    login = fields.Char( string="Name")
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', string="Driver User")
    partner_id = fields.Many2one(related='user_id.partner_id', store=True, string="Driver Partner" )
    carrier_id = fields.Many2one('shipment.carrier', string="Carrier", required=True, tracking=True)
    otp = fields.Char(string="PIN", tracking=True)
    otp_expiration_time = fields.Datetime(string="PIN Expiration Date")
    truck_no = fields.Char(string="Truck No", required=True, tracking=True)
    test_user = fields.Boolean(string="Test User", tracking=True)
    is_continuous_location_tracking = fields.Boolean(String= "Currently tracked by mobile" ,default=False)
    current_shipment_id = fields.Integer(string="Current Location Tracking Shipment Id")
    phone = fields.Char(related="user_id.phone", string="Driver Phone")
    is_skip_sms = fields.Boolean(string="Skip SMS", default=False)
    is_valid_phone = fields.Boolean(string="Valid Phone Number?", readonly=True, help="This field is used to determine if the phone number is valid for sending SMS, verified by Twilio Lookup API.")
    is_from_logout = fields.Boolean(string="Is from Logout", readonly=True, default=False) #flag to keep trackig tracking pause from logout or not

    shipment_ids = fields.One2many('shipment.shipment', 'driver_id', string="Shipments")
    is_shipment_exists = fields.Boolean(string="Shipments Exist", compute="_compute_shipments_details", copy=False)
    shipment_count = fields.Char(string="Shipments Count", compute="_compute_shipments_details", copy=False)
    active = fields.Boolean(default=True, tracking=True)
    policy_accepted_on = fields.Datetime(string="Policy Accepted On", default=fields.Datetime.now, copy=False, tracking=True)


    def _compute_display_name(self):
        super()._compute_display_name()
        for rec in self:
            # user_name = rec.user_id.partner_id.name or ''
            user_name = rec.carrier_id.name or ''
            truck_no = rec.truck_no or ''
            rec.display_name = _("%(user_name)s <%(truck_no)s>", user_name=user_name, truck_no=truck_no)

    # @api.model
    # def name_search(self, name, args=None, operator='ilike', limit=100):
    #     args = args or []
    #     if self.env.context.get('is_from_call_out_mst'):
    #         domain = args + ['|', ('truck_no', operator, name), ('carrier_id.name', operator, name)]
    #         return self.search(domain, limit=limit).name_get()
    #     return super(BistaFleetDriver, self).name_search(name, args=args, operator=operator, limit=limit)
    
    # NOTE FIX: search in m2o field driver_id should add the domain of truck no and carrier
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if self.env.context.get('is_from_call_out_mst'):
            domain = args + ['|', ('truck_no', operator, name), ('carrier_id.name', operator, name)]
            driver_ids = self.search_fetch(
                domain, ['display_name'], limit=limit,
            )
            return [(driver_id.id, driver_id.display_name) for driver_id in driver_ids]
        return super().name_search(name, domain, operator, limit)

    @api.depends('shipment_ids')
    def _compute_shipments_details(self):
        for record in self:
            if record.shipment_ids:
                total_shipment_ids = record.shipment_ids
                if total_shipment_ids:
                    record.is_shipment_exists = True
                    record.shipment_count = f"{len(total_shipment_ids)}"
                else:
                    record.is_shipment_exists = False
                    record.shipment_count = "0"
            else:
                record.is_shipment_exists = False
                record.shipment_count = "0"

    @api.constrains('truck_no')
    def _check_unique_truck_no(self):
        for rec in self:
            if rec.truck_no and self.search([('truck_no', '=', rec.truck_no), ('id', '!=', rec.id)], limit=1):
                app_language = 'en'
                if request:
                    app_language = request.httprequest.headers.get('lang')
                if app_language == 'es':
                    message = "El número de camión '%s' debe ser único." % rec.truck_no
                else:
                    message = "Truck number '%s' must be unique." % rec.truck_no

                raise ValidationError(message)

    def create(self, vals):
        """Create corresponding user record as Portal user and """
        if isinstance(vals,list):
            for rec in vals:
                user_id = self.env['res.users'].sudo().create({
                    'name': rec.get('driver_name'),
                    'login': rec.get('driver_login'),
                    'groups_id': [(4, self.env.ref('base.group_portal').id, 0),(4, self.env.ref('bista_driver_app.group_shipment_driver_user_access').id,0)],
                    # 'user_type': 'driver_user',
                    # 'standard_template_integration_user_type': 'driver_user',
                    'is_driver': True,
                })
                user_id.partner_id.sudo().write({'phone': rec.get('driver_login')})
                rec.update({'user_id': user_id.id,
                            'phone': rec.get('driver_login')})
                
                # T2745: Enable Setting for New Users to Receive Text Messages
                # if not rec.get('is_skip_sms'):
                # verify_driver_phone(self,rec) #NOTE: Driver app

                # rec.update({
                #     'name': rec.get('driver_name'),
                #     'login': rec.get('driver_login'),
                #     'groups_id': [(4, self.env.ref('base.group_portal').id, 0),(4, self.env.ref('bista_driver_app.group_call_out_readonly_user_access').id,0)],
                #     'user_type': 'driver_user',
                #     'standard_template_integration_user_type': 'driver_user',
                #     'is_driver': True,
                # })
        else:
            user_id = self.env['res.users'].sudo().create({
                'name': vals.get('driver_name'),
                'login': vals.get('driver_login'),
                'groups_id': [(4, self.env.ref('base.group_portal').id, 0),(4, self.env.ref('bista_driver_app.group_shipment_driver_user_access').id,0)],
                # 'user_type': 'driver_user',
                # 'standard_template_integration_user_type': 'driver_user',
                'is_driver': True,
            })
            user_id.partner_id.sudo().write({'phone': vals.get('driver_login')})
            vals.update({'user_id': user_id.id, 
                        'phone': vals.get('driver_login')})
            
            # T2745: Enable Setting for New Users to Receive Text Messages
            # if not vals.get('is_skip_sms'):
            # verify_driver_phone(self, vals) #NOTE: Driver app

            # vals.update({
            #     'name': vals.get('driver_name'),
            #     'login': vals.get('driver_login'),
            #     'groups_id': [(4, self.env.ref('base.group_portal').id, 0),(4, self.env.ref('bista_driver_app.group_call_out_readonly_user_access').id,0)],
            #     'user_type': 'driver_user',
            #     'standard_template_integration_user_type': 'driver_user',
            #     'is_driver': True,
            # })
        res = super().create(vals)
        # update the created corresponding res_partner phone of driver user for twilio sms
        # for rec in res:
        #     rec.partner_id.sudo().write({'phone': rec.driver_login})
        return res

    def write(self, values):
        if values.get('driver_name') or values.get('driver_login') :
            for rec in self:
                if values.get('driver_name'):
                    rec.user_id.name = values.get('driver_name')
                    # values.update({'name': values.get('driver_name')})
                if values.get('driver_login') :
                    rec.user_id.login = values.get('driver_login')
                    # T2493:Update partner phone while changing driver login number.
                    rec.user_id.partner_id.sudo().write({'phone': values.get('driver_login')})

                    # T2745: Enable Setting for New Users to Receive Text Messages
                    # if not rec.is_skip_sms:
                    # Prevent SMS verification for predefined iOS test driver record
                    #NOTE: Driver app
                    # if not self.env.ref('bista_driver_app.ios_test_driver_rec').id == rec.id:
                    #     verify_driver_phone(rec, values)

                    # values.update({'login': values.get('driver_login')})
        # In the generate_driver_otp function the following parameter will be set as ios_test_driver_rec OTP
        # In order to avoid the password policy check for the given user while module upgrade at first the record is updated
        # with the OTP following password rules. Later desired otp is set
        # if self.id == self.env.ref('bista_driver_app.ios_test_driver_rec').id:
        #     ios_test_driver_rec_otp = self.generate_driver_otp()
        #     values.update({'otp': ios_test_driver_rec_otp})
        return super().write(values)

    def unlink(self):
        """
            Prevent iOS test driver unlink.
        """
        for rec in self:
            if rec.id == self.env.ref('bista_driver_app.ios_test_driver_rec').id:
                raise UserError(_("You cannot delete this iOS test driver."))
            # remove corresponding user and partner upon driver deletion:
            user_id = rec.user_id
            partner_id = user_id.partner_id
            super(BistaFleetDriver, rec).unlink()
            if user_id.exists():
                user_id.sudo().unlink()
            partner_id.sudo().unlink()
        return 

    def action_archive(self):
        """
            Prevent iOS test driver user active toggle.
        """
        for rec in self:
            if rec.id == self.env.ref('bista_driver_app.ios_test_driver_rec').id:
                raise UserError(_("You cannot archive this iOS test driver."))
        return super().action_archive()

    def generate_driver_otp(self, phone_number= None):
        """
            Generates an otp from button in form view and api call
        """
        self = self.sudo()
        if self.id == self.env.ref('bista_driver_app.ios_test_driver_rec').id:
            # In the generate_driver_otp function the following parameter will be set as ios_test_driver_rec OTP
            # In order to avoid the password policy check for the given user while module upgrade at first the record is updated
            # with the OTP following password rules. Later desired otp is set
            ios_test_driver_rec_otp =  self.env['ir.config_parameter'].sudo().get_param('bista_driver_app.ios_test_driver_otp')
            self.sudo().env.cr.execute('UPDATE res_users SET password = %s WHERE id=%s', (ios_test_driver_rec_otp, self.user_id.id))
            self.sudo().env.cr.execute('UPDATE fleet_driver SET otp = %s WHERE id=%s', (ios_test_driver_rec_otp, self.id))
            return ios_test_driver_rec_otp
        if not phone_number:
            # phone_number = self.login
            phone_number = self.driver_login
        # NOTE: generate pin if not already set
        # if phone_number and not self.otp:
        if phone_number:
            from_mobile_app = self.env.context.get('from_mobile_app')
            user_id = self.env['res.users'].sudo().search([('login','=',phone_number)])
            # if user_id and user_id.has_group('base.group_portal') and user_id.standard_template_integration_user_type == 'driver_user':
            if user_id and user_id.has_group('base.group_portal') and user_id.has_group('bista_driver_app.group_shipment_driver_user_access') and not user_id.has_group('bista_driver_app.group_shipment_dispatcher_access'):
                digits = "0123456789"
                OTP = ""
                for i in range(5):
                    OTP += digits[int(math.floor(random.random() * 10))]

                self.sudo().env.cr.execute('UPDATE res_users SET password = %s WHERE id=%s', (OTP, user_id.id))
                if from_mobile_app:
                    log_user = user_id.id
                    log_partner_id = user_id.partner_id.id
                else:
                    log_user = self.env.uid
                    log_partner_id = self.env.user.partner_id.id
                # otp_sms_template = self.env.ref('bista_driver_app.driver_fleet_otp_sms_template')
                old_otp = self.otp
                # NOTE: Driver app: remove otp_expiration_time
                self.with_user(log_user).write({'otp': OTP, 'otp_expiration_time': fields.Datetime.now() + timedelta(minutes=5)})

                # Send OTP via Email
                # Check for active outgoing mail server
                mail_server = self.env['ir.mail_server'].sudo().search(
                    [('active', '=', True)], limit=1
                )
                if mail_server and user_id.partner_id.email:
                    mail_values = {
                        'subject': 'Driver OTP Code',
                        'email_from': self.env.company.email,
                        'email_to': user_id.partner_id.email,
                        'body_html': f"""
                            <p>
                                Hello {user_id.partner_id.name},
                                Your OTP is: <b>{OTP}</b><br/>
                                This OTP will expire in 5 minutes.
                            </p>
                        """,
                    }



                    mail = self.env['mail.mail'].sudo().create(mail_values)
                    mail.send()

                # self.with_user(log_user).write({'otp': OTP,})
                # NOTE: Driver app: remove otp generation sms twilio functionality
                # twilio_account_id = self.env['twilio.account'].sudo().search([('state', '=', 'confirm')], limit=1)
                # if twilio_account_id and self.is_valid_phone and not self.is_skip_sms:
                #     otp_sms_id = self.env['twilio.sms'].sudo().create({
                #         'name': 'Driver OTP SMS',
                #         'account_id': twilio_account_id.id,
                #         'receiver_partner_id': self.partner_id.id,
                #         'content': otp_sms_template.content % OTP,
                #         'template_body_id': otp_sms_template.id,
                #         'single_receiver': True,
                #         'driver_id': self.id
                #     })

                #     base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                #     record_url = f"{base_url}/web#id={otp_sms_id.id}&model=twilio.sms&view_type=form"
                #     self.with_user(SUPERUSER_ID).message_post(
                #     body=f"""<a class="sms_link" href="{record_url}" target="_blank">{'Generate and Send Pin: '}</a> A new code has been generated.<br/>&#8226;&nbsp; {old_otp}
                #                                                     <i class="o-mail-Message-trackingSeparator fa fa-long-arrow-right mx-1 text-600"></i>{OTP} """,
                #     body_is_html=True, author_id= log_partner_id,
                #     )

                #     if from_mobile_app:
                #         response = otp_sms_id.with_user(SUPERUSER_ID).action_confirm_sms()
                #     else:
                #         response = otp_sms_id.with_user(SUPERUSER_ID).action_confirm_sms()
                #     if not from_mobile_app:
                #         return response
                # else:
                #     if from_mobile_app:
                #         return True
                #     else:
                #         if not self.is_valid_phone:
                #             message = "Message skipped for invalid phone number"
                #         elif self.is_skip_sms:
                #             message = "Message skipped for this Driver User"
                #         else:
                #             message = "Message failed to send."
                #         return {
                #             'type': 'ir.actions.client',
                #             'tag': 'display_notification',
                #             'params': {
                #                 'message': message,
                #                 'type': 'warning',
                #                 'sticky': False,
                #                 'next': {
                #                     'type': 'ir.actions.act_window_close'
                #                 },
                #             }
                #         }
                return True
            else:
                return False
        return True

    # def action_driver_twilio_sms(self):
    #     """Action for opening the SMS wizard view from driver view"""
    #     twilio_account_id = self.env['twilio.account'].sudo().search([], limit=1)

    #     # For form view, Hide the Driver field.
    #     is_from_form = False
    #     if len(self.ids) == 1:
    #         is_from_form = True

    #     action = {
    #         'type': 'ir.actions.act_window',
    #         'name': _('Message'),
    #         'res_model': 'sms.builder',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_account_id': twilio_account_id.id,
    #             'default_driver_ids': self.ids,
    #             'default_is_from_form_view': is_from_form
    #         },
    #         'views': [[False, 'form']]
    #     }
    #     return action

    def action_open_user(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_res_users")
        action['res_id'] = self.user_id.id
        action['views'] = [[self.env.ref('base.view_users_form').id, 'form']]
        return action


    @api.model
    def _update_driver_partner_phone(self):
        """
            Update the phone number of the driver partner with the login of the user.
        """
        driver_ids = self.sudo().search([])
        driver_phone = False
        for rec in driver_ids:
            if rec.driver_login and rec.user_id and rec.user_id.partner_id:
    #             if not rec.driver_login.strip().startswith("+1"):
    #                 driver_phone = "+1" + rec.driver_login.lstrip("0+")
    #             else:
                driver_phone = rec.driver_login
                rec.user_id.partner_id.write({'phone': driver_phone})

    # def action_driver_app_download_link(self):
    #     otp_sms_template = self.env.ref('bista_driver_app.driver_fleet_app_download_link_sms_template')
    #     twilio_account_id = self.env['twilio.account'].sudo().search([], limit=1)

    #     if twilio_account_id and self.is_valid_phone and not self.is_skip_sms:
    #         self = self.sudo()
    #         app_download_sms_id = self.env['twilio.sms'].sudo().create({
    #             'name': 'Driver App Download link SMS',
    #             'account_id': twilio_account_id.id,
    #             'receiver_partner_id': self.partner_id.id,
    #             'content': otp_sms_template.content,
    #             'template_body_id': otp_sms_template.id,
    #             'single_receiver': True,
    #             'driver_id': self.id,
    #         })
    #         response = app_download_sms_id.action_confirm_sms()
    #         # self.sudo().message_post(
    #         #     body=(otp_sms_template.content)
    #         # )
    #         base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #         record_url = f"{base_url}/web#id={app_download_sms_id.id}&model=twilio.sms&view_type=form"
    #         self.sudo().message_post(
    #                 body=f"""<a class="sms_link" href="{record_url}" target="_blank">{'Send App Donwload Link: '}</a>{otp_sms_template.content} """,
    #                 body_is_html=True
    #             )
    #         return response
    #     else:
    #         if self.is_skip_sms:
    #             message = "Message skipped for this Driver User"
    #         else:
    #             message = "Message failed to send."
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'message': message,
    #                 'type': 'warning',
    #                 'sticky': False,
    #                 'next': {
    #                     'type': 'ir.actions.act_window_close'
    #                 },
    #             }
    #         }
    #NOTE: Driver app
    # @api.model
    # def _verify_driver_phone(self):
    #     driver_ids = self.search([])
    #     for driver in driver_ids:
    #         if not driver.is_skip_sms:
    #             verify_driver_phone(self, driver)

    def action_open_driver_shipments(self):
        return {
            'name': 'Shipments',
            'type': 'ir.actions.act_window',
            'res_model': 'shipment.shipment',
            'view_mode': 'list,form',
            'domain': [('driver_id', '=', self.id)],
            'context': {
                'default_driver_id': self.id,
                'create': False
            }
        }
