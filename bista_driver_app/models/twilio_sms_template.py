# -*- coding: utf-8 -*-
from odoo import api, fields, models,_
from odoo.exceptions import UserError


class TwilioSmsTemplate(models.Model):
    _inherit = 'twilio.sms.template'


    def unlink(self):
        """Override unlink method to prevent deletion of SMS templates
        that are in use"""
        for template in self:
            if template.id == self.env.ref('bista_driver_app.driver_fleet_otp_sms_template').id:
                raise ValueError("Cannot delete this SMS template that is in use.")
        return super(TwilioSmsTemplate, self).unlink()

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if not self.env.user.has_group(
                'bista_driver_app.group_shipment_dispatcher_access') and not self.env.user.has_group(
            'base.group_system'):
            raise UserError(_('You are not allowed to access this Record'))
        res = super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                      count_limit=count_limit)
        return res
