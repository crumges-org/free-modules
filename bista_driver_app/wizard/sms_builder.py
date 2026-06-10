# NOTE: Driver app

# # -*- coding: utf-8 -*-
# from odoo import _, api, fields, models
# from odoo.addons.bista_driver_app.common import verify_driver_phone
# import logging

# _logger = logging.getLogger(__name__)


# class SmsBuilder(models.TransientModel):
#     _inherit= 'sms.builder'

#     driver_ids = fields.Many2many('fleet.driver', string='Drivers')
#     is_from_form_view = fields.Boolean(default=False)

#     def action_send_text_message(self):
#         driver_ids = self.driver_ids
#         driver_lst = []
#         for driver_id in driver_ids:
#             verify_driver_phone(self, driver_id)
#             is_valid_phone = driver_id.is_valid_phone
#             if self.account_id and is_valid_phone and not driver_id.is_skip_sms:
#                 otp_sms_id = self.env['twilio.sms'].sudo().create({
#                     'name': 'Driver Send Text Message',
#                     'account_id': self.account_id.id,
#                     'receiver_partner_id': driver_id.sudo().user_id.partner_id.id,
#                     'content': self.text_message,
#                     'template_body_id': self.template_id.id  if self.template_id else False,
#                     'single_receiver': True,
#                     'driver_id': driver_id.id
#                 })
#                 response = otp_sms_id.action_confirm_sms()
#                 if otp_sms_id:
#                     base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
#                     record_url = f"{base_url}/web#id={otp_sms_id.id}&model=twilio.sms&view_type=form"

#                     driver_id.sudo().message_post(
#                         body=f"""<a class="sms_link" href="{record_url}" target="_blank">{'Send Text Message:'}</a> {self.text_message} """,
#                         body_is_html=True
#                     )
#                 _logger.info("Message sent to driver %s - %s", driver_id.driver_name, response)
#             else:
#                 _logger.info("Message failed to send to driver %s", driver_id.driver_name)
#                 driver_lst.append(driver_id.driver_name)

#         if driver_lst and len(driver_lst) > 0:
#             return {
#                     'type': 'ir.actions.client',
#                     'tag': 'display_notification',
#                     'params': {
#                         'message': _("Message failed to send to drivers: %s" % driver_lst),
#                         'type': 'warning',
#                         'sticky': False,
#                         'next': {
#                             'type': 'ir.actions.act_window_close'
#                         },
#                     }
#                 }
