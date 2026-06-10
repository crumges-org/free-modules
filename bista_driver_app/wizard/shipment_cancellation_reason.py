# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class ShipmentCancellationWizard(models.TransientModel):
    _name = 'shipment.cancellation.wizard'
    _description = 'Shipment Cancellation Wizard'

    reason = fields.Text(string='Reason', required=True)

    def cancel_shipment(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        active_records = self.env[active_model].browse(active_ids)
        assigned_status_rec = self.env.ref('bista_driver_app.shipment_status_cancelled')
        for rec in active_records:
            write_vals = {
                        'status_id': assigned_status_rec.id, 
                        'cancel_reason': self.reason,
                        'tracking_status': 'inactive',
                        }
            rec.write(write_vals)
                        
            if rec.driver_id and rec.id == rec.driver_id.current_shipment_id:
                rec.send_shipment_notificaton(special_case= 'shipment_cancelled', driver_id = None)
                rec.driver_id.write({
                        'is_continuous_location_tracking': False,
                        'current_shipment_id': False,
                    })
            rec.create_shipment_timeline(changes= 'shipment_status', value= assigned_status_rec, driver_id= None) # shipment timeline is created from the common function

    def create(self, vals):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        active_records = self.env[active_model].browse(active_ids)
        active_records.write({'cancel_reason': vals.get('reason')})
        return super(ShipmentCancellationWizard, self).create(vals)