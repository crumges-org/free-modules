# -*- coding: utf-8 -*-
from odoo import fields, models


class ShipmentTimeline(models.Model):
    _name = "shipment.timeline"
    _description = 'Shipment Timeline'
    _order = 'id desc'

    name = fields.Char(string="Action", required=True)
    shipment_id = fields.Many2one('shipment.shipment', string='Shipment', required=True, ondelete='cascade')
    datetime = fields.Datetime(string='Date Time', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    user_name = fields.Char(string="User Name", required=True)
    source = fields.Char(string='Source Text')
    source_id = fields.Many2one('geolocation.source', string='Source')
    condition = fields.Char(string='Condition')
    driver_coords = fields.Char(string='Driver Coordinates')
    location_coords = fields.Char(string='Location Coordinates')
    truck_number = fields.Char(string="Truck No")
    driver_id = fields.Many2one("fleet.driver", string="Carrier")
    active = fields.Boolean(default=True, tracking=True)
