# -*- coding: utf-8 -*-
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID
from odoo.exceptions import UserError

class ShipmentCarriers(models.Model):
    _name = "shipment.carrier"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Carrier"
    _order = 'id desc'

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_carrier_name', 'unique(name)', 'The carrier name must be unique.'),
    ]

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if not self.env.user.has_group(
                'bista_driver_app.group_shipment_dispatcher_access') and not self.env.user.has_group(
                'base.group_system'):
            raise UserError(_('You are not allowed to access this Record'))
        res = super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                          count_limit=count_limit)
        return res
