# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
# from odoo.addons.bista_driver_base.models.error import MissingRelease
from copy import deepcopy


class CreateShipmentsWizard(models.TransientModel):
    _name = 'shipment.wizard'
    _description = 'Create Shipments'

    pickup_location_id = fields.Many2one('shipment.location', string="Pickup Location", required=True)
    planned_pickup_date = fields.Datetime(string="Planned Pickup Date", required=True)
    pickup_timezone = fields.Selection([('EST', 'EST'), ('CST', 'CST'), ('MST', 'MST'), ('PST', 'PST'), ], string='Pickup Timezone', required=True)
    delivery_location_id = fields.Many2one('shipment.location', string="Delivery Location", required=True)
    planned_delivery_date = fields.Datetime(string="Planned Delivery Date", required=True)
    delivery_timezone = fields.Selection([('EST', 'EST'), ('CST', 'CST'), ('MST', 'MST'), ('PST', 'PST'), ], string='Delivery Timezone', required=True)
    interval = fields.Selection([('00', '00'), ('05', '05'), ('10', '10'), ('15', '15'), ('20', '20'), ('25', '25'), ('30', '30'), ('35', '35'), ('40', '40'), ('45', '45'), ('50', '50'), ('55', '55'), ('60', '60'), ],string="Delivery Interval", required=True)
    no_of_trucks = fields.Integer(string="No of Trucks", required=True)
    add_forklift_shipment = fields.Boolean(string="Add Forklift Shipment")
    release = fields.Char(string="Release/SO #", required=True)
    shipment_notes = fields.Html(string="Shipment Notes")

    @api.constrains('no_of_trucks')
    def _check_no_of_trucks_range(self):
        for record in self:
            if not 1 <= record.no_of_trucks <= 99:
                raise ValidationError(_("No of Trucks should be between 1 to 100."))

    @api.onchange('pickup_location_id')
    def _onchange_pickup_location_id(self):
        if self.pickup_location_id:
            self.pickup_timezone = self.pickup_location_id.timezone if self.pickup_location_id.timezone else False
        else:
            self.pickup_timezone = False

    @api.onchange('delivery_location_id')
    def _onchange_delivery_location_id(self):
        if self.delivery_location_id:
            self.delivery_timezone = self.delivery_location_id.timezone if self.delivery_location_id.timezone else False
        else:
            self.delivery_timezone = False

    def create_shipments(self):
        self.ensure_one()
        active_id = self.env.context.get('active_id')
        # call_out_id = self.env['call.out.request'].browse(active_id)
        pending_state_id = self.env.ref('bista_driver_app.shipment_status_pending')

        # product_items = call_out_id.call_out_request_product_ids.mapped('item_name') if call_out_id.call_out_request_product_ids else []
        # accessories_items = call_out_id.call_out_request_accessories_ids.mapped('accessories_description') if call_out_id.call_out_request_accessories_ids else []
        # all_items = product_items + accessories_items

        stop_lines = []
        if self.pickup_location_id:
            stop_lines.append((0, 0, {
                'name': 'Stop 1',
                'location_id': self.pickup_location_id.id,
                'location_name' : self.pickup_location_id.name,
                'planned_arrival': self.planned_pickup_date,
                'timezone': self.pickup_timezone,
                'street_1': self.pickup_location_id.street_1,
                'street_2': self.pickup_location_id.street_2,
                'city': self.pickup_location_id.city,
                'state_id': self.pickup_location_id.state_id.id,
                'county_id': self.pickup_location_id.county_id.id,
                'country_id': self.pickup_location_id.country_id.id,
                'zip': self.pickup_location_id.zip,
                'address': self.pickup_location_id.address,
                'directions': self.pickup_location_id.directions,
                'notes': self.pickup_location_id.notes,
                'sequence': 1,
                'latitude': self.pickup_location_id.latitude,
                'longitude': self.pickup_location_id.longitude,
                'location_type': 'pickup',
                'shape_data': self.pickup_location_id.shape_data
            }))
        if self.delivery_location_id:
            stop_lines.append((0, 0, {
                'name': 'Stop 2',
                'location_id': self.delivery_location_id.id,
                'location_name' : self.delivery_location_id.name,
                'planned_arrival': self.planned_delivery_date,
                'timezone': self.delivery_timezone,
                'street_1': self.delivery_location_id.street_1,
                'street_2': self.delivery_location_id.street_2,
                'city': self.delivery_location_id.city,
                'state_id': self.delivery_location_id.state_id.id,
                'county_id': self.delivery_location_id.county_id.id,
                'country_id': self.delivery_location_id.country_id.id,
                'latitude': self.delivery_location_id.latitude,
                'longitude': self.delivery_location_id.longitude,
                'zip': self.delivery_location_id.zip,
                'address': self.delivery_location_id.address,
                'directions': self.delivery_location_id.directions,
                'notes': self.delivery_location_id.notes,
                'sequence': 2,
                'location_type': 'delivery',
                'shape_data': self.delivery_location_id.shape_data
            }))

        # Add 1 more if add_forklift_shipment is True
        if self.add_forklift_shipment:
            shipment_id = self.env['shipment.shipment'].sudo().create({
                'pickup_id': self.pickup_location_id.id,
                'delivery_id': self.delivery_location_id.id,
                'pickup_timezone': self.pickup_timezone,
                'delivery_timezone' : self.delivery_timezone,
                'planned_pickup': self.planned_pickup_date,
                'planned_delivery': self.planned_delivery_date,
                'forklift_shipment': self.add_forklift_shipment,
                'notes': self.shipment_notes,
                'sale_order_no' : self.release,
                'status_id' : pending_state_id.id,
                # 'item_ids': [(0, 0, {'name': name}) for name in all_items],
                'stop_ids': stop_lines,
                # 'call_out_id' : call_out_id.id,
                # 'customer_id' : call_out_id.company_id.id
            })
            shipment_id._onchange_pickup_id()
            shipment_id._onchange_delivery_id()

        ship_lst = []
        for i in range(self.no_of_trucks):
            delivery_offset = int(self.interval) * (i + 1) if self.add_forklift_shipment else int(self.interval) * i
            stop_lines_cpy = deepcopy(stop_lines)
            # stop_lines_cpy[0][2]['planned_arrival'] = self.planned_pickup_date
            stop_lines_cpy[1][2]['planned_arrival'] = self.planned_delivery_date + timedelta(minutes=delivery_offset)

            ship_lst.append({
                'pickup_id': self.pickup_location_id.id,
                'delivery_id': self.delivery_location_id.id,
                'pickup_timezone': self.pickup_timezone,
                'delivery_timezone' : self.delivery_timezone,
                'planned_pickup': self.planned_pickup_date,
                # 'planned_delivery': self.planned_delivery_date + (timedelta(minutes=int(self.interval) * (i+1))),
                'planned_delivery': self.planned_delivery_date + timedelta(minutes=delivery_offset),
                'forklift_shipment': False,
                'notes': self.shipment_notes,
                'sale_order_no' : self.release,
                'status_id' : pending_state_id.id,
                # 'item_ids': [(0, 0, {'name': name}) for name in all_items],
                'stop_ids': stop_lines_cpy,
                # 'call_out_id' : call_out_id.id,
                # 'customer_id' : call_out_id.company_id.id
            })

        shipment_ids = self.env['shipment.shipment'].sudo().create(ship_lst)
        shipment_ids._onchange_pickup_id()
        shipment_ids._onchange_delivery_id()

        # Set call out status to pending if call out stage is acknowledged
        # acknowledged_id = self.env.ref('bista_call_out_request.stage_acknowledged_3').id
        # if call_out_id.stage_id.id == acknowledged_id:
        #     call_out_id.sudo().action_set_pending()
