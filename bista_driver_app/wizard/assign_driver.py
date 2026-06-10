# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class AssignDriverWizard(models.TransientModel):
    _name = 'assign.driver'
    _description = 'Assign Driver'

    driver_id = fields.Many2one('fleet.driver', string='Driver')

    def assign_driver(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            for rec in self.env['shipment.shipment'].browse(active_ids):
                rec.driver_id = self.driver_id.id
                rec.status_id = self.env.ref('bista_driver_app.shipment_status_assigned').id
                return {
                    'type': 'ir.actions.client',
                    'tag': 'shipment_notification',
                    'params': {
                        'type': 'success',
                        'title': _('New Driver Assigned'),
                        'message': rec.name,
                        'next': {'type': 'ir.actions.act_window_close'},
                    },
                }
