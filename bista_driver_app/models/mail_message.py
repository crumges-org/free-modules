# -*- coding: utf-8 -*-
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID


class MailMessage(models.Model):
    _inherit = "mail.message"

    # Message Format Overwrite
    def _message_format(self, fnames, format_reply=True):
        vals_list = super()._message_format(fnames=fnames, format_reply=format_reply)
        for vals in vals_list:
            if 'model' in vals and  vals.get('model') and vals.get('model') == "shipment.shipment":
                user = vals.get('author').get('user').get('id')
                user_id = self.env.user.browse(user)

                # if user_id and user_id.has_group('base.group_portal') and user_id.standard_template_integration_user_type == 'driver_user' and user_id.is_driver == True:
                # if user_id and user_id.standard_template_integration_user_type == 'driver_user':
                if user_id and user_id.has_group('bista_driver_app.group_shipment_driver_user_access') and not user_id.has_group('bista_driver_app.group_shipment_dispatcher_access'):
                    fleet_driver = self.env['fleet.driver'].sudo().search([('user_id','=',user_id.id)], limit=1)
                    if fleet_driver:
                        vals['driver_name'] = fleet_driver.display_name

                if 'trackingValues' in vals and vals.get('trackingValues'):
                    for trackingValue in vals.get('trackingValues'):
                        if trackingValue.get('fieldType') == 'datetime' and trackingValue.get('fieldName') in ['actual_pickup', 'actual_delivery', 'planned_pickup', 'planned_delivery']:
                            trackingValue['newValue']['isUtc'] = True
                            trackingValue['oldValue']['isUtc'] = True

        return vals_list
