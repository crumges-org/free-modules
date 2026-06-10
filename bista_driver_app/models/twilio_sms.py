# -*- coding: utf-8 -*-
from odoo import api, fields, models,_
from odoo.exceptions import UserError


class TwilioSms(models.Model):
    _inherit = 'twilio.sms'

    shipment_id = fields.Many2one('shipment.shipment', string='Shipment')
    driver_id = fields.Many2one('fleet.driver', string='Driver')
    response = fields.Text(string='Response', help='Response from Twilio API')

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if not self.env.user.has_group(
                'bista_driver_app.group_shipment_dispatcher_access') and not self.env.user.has_group(
            'base.group_system'):
            raise UserError(_('You are not allowed to access this Record'))
        res = super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                      count_limit=count_limit)
        return res


class TwilioSmsTemplate(models.Model):
    _inherit = 'twilio.sms.template'

    content = fields.Text(string='Content (EN)', help='Content (EN) of the Template')
    content_es = fields.Text(string='Content (ES)', help='Content (ES) of the Template')
