# -*- coding: utf-8 -*-
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID
from odoo.exceptions import UserError

class ShipmentStatus(models.Model):
    _name = "shipment.status"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'
    _description = "Stage"

    name = fields.Char(string="Name (EN)")
    name_es = fields.Char(string="Name (ES)")
    sequence = fields.Integer(string="Sequence")
    color = fields.Integer('Color Index', default=0)
    fold = fields.Boolean('Folded in Kanban')
    active = fields.Boolean(default=True, tracking=True)
    # mobile app fields
    button_name_en = fields.Char(string="Button Name (EN)")
    button_name_es = fields.Char(string="Button Name (ES)")
    is_driver_can_choose = fields.Boolean(string="Driver Can Choose", default=False)
    location_tracking = fields.Selection([('disabled','Disabled'),
                                         ('enabled','Enabled'),
                                         ], string="Location Tracking")
    status_action = fields.Char(string="Next Action")
    is_completed = fields.Boolean("Is Completed")  
    is_cancelled = fields.Boolean("Is Cancelled")
    do_eta_calculation = fields.Boolean(string="ETA Calculation", default=False)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if not self.env.user.has_group(
                'bista_driver_app.group_shipment_dispatcher_access') and not self.env.user.has_group(
            'base.group_system'):
            raise UserError(_('You are not allowed to access this Record'))
        res = super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                      count_limit=count_limit)
        return res