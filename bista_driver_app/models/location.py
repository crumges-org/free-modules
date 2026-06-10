# -*- coding: utf-8 -*-
import requests
import json
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.http import request
from odoo.addons.web.controllers.utils import is_user_internal


class ShipmentLocations(models.Model):
    _name = "shipment.location"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Location"
    _order = 'name asc'

    def _get_default_shape_data(self):
        try:
            radius_id = self.env.ref('bista_driver_app.shipment_settings_geofence_radius')
            if radius_id and radius_id.value:
                radius = radius_id.value * 0.3048 if radius_id.unit == 'Feet' else radius_id.value
            else:
                radius = 500  # Fallback radius if value is missing
        except Exception as e:
            radius = 500  # Fallback radius on error

        data = {
            'type': 'circle',
            'center': {"lat": 40.75, "lng": -74.125},
            'radius': radius
        }
        return json.dumps(data)

    name = fields.Char(string="Name", required=True, tracking=True)
    address = fields.Char(string="Address", tracking=True)
    street_1= fields.Char(string="Street 1", tracking=True)
    street_2 = fields.Char(string="Street 2", tracking=True)
    city = fields.Char(string="City", tracking=True)
    zip = fields.Char(string="Zip", tracking=True)

    country_id = fields.Many2one("res.country", string="Country", tracking=True, default=lambda self: self.env.ref('base.us').id)
    state_id = fields.Many2one("res.country.state", string="State", tracking=True, domain="[('country_id', '=', country_id)]")
    county_id = fields.Many2one("res.city", string="County", domain="[('state_id', '=', state_id)]", tracking=True)

    # latitude = fields.Char(string="Latitude", tracking=True, compute='get_lat_lon_from_address', store=True, copy=True)
    # longitude = fields.Char(string="Longitude", tracking=True, compute='get_lat_lon_from_address', store=True, copy=True)
    latitude = fields.Char(string="Latitude", tracking=True, copy=True)
    longitude = fields.Char(string="Longitude", tracking=True, copy=True)

    timezone = fields.Selection([('EST', 'EST'), ('CST', 'CST'), ('MST', 'MST'), ('PST', 'PST'), ], string='Timezone', required=True, tracking=True)
    person_name = fields.Char(string="Contact Name", tracking=True)
    person_phone = fields.Char(string="Contact Phone", tracking=True)
    person_email = fields.Char(string="Contact Email", tracking=True)

    directions = fields.Html(string="Directions")
    notes = fields.Html(string="Notes")
    is_created_by_customer = fields.Boolean(string="Is Created By Customer", tracking=True)
    customer = fields.Many2one("res.company", string="Customer", tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    # well_name = fields.Char(string="Well Name", copy=True)
    latitude_longitude = fields.Char(compute='_compute_coordinates', string="Latitude Longitude", store=True)
    zoom_level = fields.Integer(string="Zoom Level", default=14)
    shape_data = fields.Char(string="Shape Data", default=_get_default_shape_data, store=True)

    @api.constrains('shape_data')
    def _check_shape_data(self):
        for rec in self:
            if not rec.shape_data:
                raise ValidationError(_("Geofence Data is required."))

    @api.depends("latitude", "longitude")
    def _compute_coordinates(self):
        """
        This method is written to pass values to the MAP. It will execute if the user
        enters a value, otherwise, the condition will pass default values.
        """
        for rec in self:
            if rec.latitude and rec.longitude:
                rec.latitude_longitude = {"lat": rec.latitude, "lng": rec.longitude}
                if rec.shape_data:
                    shape_data = json.loads(rec.shape_data)
                    if shape_data['center']['lat'] != rec.latitude and shape_data['center']['lng'] != rec.longitude:
                        shape_data['center']['lat'] = rec.latitude
                        shape_data['center']['lng'] = rec.longitude
                        rec.shape_data = json.dumps(shape_data)
            else:
                rec.latitude_longitude = {"lat": '', "lng": ''}

    def get_map_action(self):
        res_id = self.env['fleet.map'].sudo().create({'name': {"lat": self.latitude, "lng": self.longitude}})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Google Map',
            'res_model': 'fleet.map',
            'res_id': res_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_open_map(self):
        for record in self:
            if record.latitude and record.longitude:
                map_url = f"https://www.google.com/maps?q={record.latitude},{record.longitude}&t=k&z=10"
                return {
                    'type': 'ir.actions.act_url',
                    'url': map_url,
                    'target': 'new',
                }
            else:
                raise UserError(_("Please enter a valid latitude and longitude."))
        return True


    @api.onchange("street_1", "street_2", "city", "zip", "state_id", "country_id")
    def _onchange_location_address_fields(self):
        maps_api_key = self.env['ir.config_parameter'].sudo().get_param('bista_driver_app.shipment_google_map_api_key')
        for record in self:
            street_1 = record.street_1 or ''
            street_2 = record.street_2 or ''
            city = record.city or ''
            state = record.state_id.name if record.state_id else ''
            county = record.county_id.name if record.county_id else ''
            zip_code = record.zip or ''
            country = record.country_id.name if record.country_id else ''

            address = ', '.join(filter(None, [street_1, street_2, city, state, county, zip_code, country]))

            if not maps_api_key or not address:
                record.latitude = ''
                record.longitude = ''
                return

            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {'address': address, 'key': maps_api_key }

            try:
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200 and response.json():
                    data = response.json()
                    if data['results']:
                        location = data['results'][0]['geometry']['location']
                        record.latitude = round(location['lat'], 6)
                        record.longitude = round(location['lng'], 6)
                    else:
                        record.latitude = ''
                        record.longitude = ''
                else:
                    record.latitude = ''
                    record.longitude = ''
            except Exception:
                record.latitude = ''
                record.longitude = ''

    @api.model_create_multi
    def create(self, vals_list):
        if request and request.session.uid and not is_user_internal(request.session.uid):
            self = self.with_user(request.session.uid).sudo()
        return super(ShipmentLocations, self).create(vals_list)

    def write(self, values):
        if values.get('directions'):
            for rec in self:
                rec.message_post(body=f"""<b>Directions Changed</b> :
                    <details>
                        <summary style="color: #017e84; font-weight: bold;">Show More</summary>
                        {rec.directions}
                        <h2><b><i class='fa fa-long-arrow-right'></i></b></h2>
                        {values.get('directions')}
                    </details>""", body_is_html=True)

        if values.get('notes'):
            for rec in self:
                rec.message_post(body=f"""<b>Notes Changed</b> :
                    <details>
                        <summary style="color: #017e84; font-weight: bold;">Show More</summary>
                        {rec.notes}
                        <h2><b><i class='fa fa-long-arrow-right'></i></b></h2>
                        {values.get('notes')}
                    </details>""", body_is_html=True)

        if request and request.session.uid and not is_user_internal(request.session.uid):
            self = self.with_user(request.session.uid).sudo()
        return super(ShipmentLocations, self).write(values)


    # Get the latitude and longitude from the address fields.
    def get_location_coordinates(self):
        self._onchange_location_address_fields()

    def _write(self, vals):
        if request and request.session.uid and not is_user_internal(request.session.uid):
            user = request.env['res.users'].browse(request.session.uid)
        return super(ShipmentLocations, self)._write(vals)