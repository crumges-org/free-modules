# -*- coding: utf-8 -*-
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from typing import Dict, List
import requests
import json
import base64

class ShipmentStops(models.Model):
    _name = "shipment.stop"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Stops"



    name = fields.Char(string="Stop", required=True, tracking=True)
    # name = fields.Char(string='Stop', compute='_compute_name', store=True)
    shipment_id = fields.Many2one("shipment.shipment", string="Shipment", tracking=True)
    location_id = fields.Many2one("shipment.location", string="Location Name")
    location_name = fields.Char(string="Name", copy=True, required=True, tracking=True)
    stop_status_id = fields.Many2one("stop.status", string="Stop Status", tracking=True,
                        default=lambda self: self.env.ref('bista_driver_app.stop_status_not_arrived').id )
    address = fields.Char(string="Address", tracking=True)
    street_1= fields.Char(string="Street 1", tracking=True)
    street_2 = fields.Char(string="Street 2", tracking=True)
    city = fields.Char(string="City", tracking=True)
    state_id = fields.Many2one("res.country.state", string="State", domain="[('country_id', '=', country_id)]", tracking=True)
    county_id = fields.Many2one("res.city", string="County", domain="[('state_id', '=', state_id)]", tracking=True)
    country_id = fields.Many2one("res.country", string="Country", default=lambda self: self.env.ref('base.us').id,
                                 domain="[('code', '=', 'US')]", tracking=True)
    zip = fields.Char(string="Zip", tracking=True)

    # latitude = fields.Char(string="Latitude", compute='get_stops_lat_lon_from_address', store=True)
    # longitude = fields.Char(string="Longitude", compute='get_stops_lat_lon_from_address', store=True)
    latitude = fields.Char(string="Latitude", copy=True, tracking=True)
    longitude = fields.Char(string="Longitude", copy=True, tracking=True)

    timezone = fields.Selection([('EST', 'EST'), ('CST', 'CST'), ('MST', 'MST'), ('PST', 'PST'), ], string='Timezone', required=True, tracking=True)
    contact_name = fields.Char(string="Contact Name", tracking=True)
    contact_phone = fields.Char(string="Contact Phone", tracking=True)
    contact_email = fields.Char(string="Contact Email", tracking=True)
    directions = fields.Html(string="Directions")
    notes = fields.Html(string="Notes")
    notes_binary = fields.Binary(string='Binary Notes',compute='_compute_notes_binary',attachment=True,store=True)
    directions_binary = fields.Binary(string='Binary Directions',compute='_compute_directions_binary',attachment=True,store=True)
    planned_arrival = fields.Datetime(string="Planned Time", tracking=True)
    actual_arrival = fields.Datetime(string="Actual Arrival Time", tracking=True)
    departure_time = fields.Datetime(string="Actual Departure Time", tracking=True)
    is_eta_status_chage = fields.Boolean(string="Is ETA Status Change")
    location_type = fields.Selection([('pickup', 'Pickup Location'), ('empty', 'Other Location'), ('delivery', 'Delivery Location')], string="Location Type", required=True, tracking=True)
    # well_name = fields.Char(string="Well Name", copy=True)
    sequence = fields.Integer(string='Sequence', copy=False)
    formatted_address = fields.Char(string='Full Address', compute='_compute_formatted_address', store=True,)
    latitude_longitude = fields.Char(compute='_compute_coordinates', string="Latitude Longitude", store=True)
    zoom_level = fields.Integer(string="Zoom Level", default=14)
    shape_data = fields.Char(string="Shape Data")

    is_dispatcher = fields.Boolean(string="Is Dispatcher", compute='_compute_is_dispatcher')
    is_show_stops_icon = fields.Boolean(compute='_compute_is_show_stops_icon')


    def _compute_is_dispatcher(self):
        for record in self:
            record.is_dispatcher = record.env.user.has_group('bista_driver_app.group_shipment_dispatcher_access')

    def _compute_is_show_stops_icon(self):
        for rec in self:
            rec.is_show_stops_icon = self.env.context.get('is_from_shipment_mst', False)

    @api.onchange('shipment_id')
    def _onchange_set_stop_name(self):
        if self.shipment_id:
            existing_stops = self.shipment_id.stop_ids
            self.name = f"Stop {len(existing_stops)}"

    @api.depends('notes')
    def _compute_notes_binary(self):
        for rec in self:
            # T2785: notes binary field
            if rec.notes:
                generated_note_pdf, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf('bista_driver_app.action_report_shipment_stop_instruction',rec.id,data={'type':'notes'})
                rec.write({'notes_binary': base64.b64encode(generated_note_pdf)})
        return
    
    @api.depends('directions')
    def _compute_directions_binary(self):
        for rec in self:
            # T2785: directions binary field
            if rec.directions:
                generated_note_pdf, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf('bista_driver_app.action_report_shipment_stop_instruction',rec.id,data={'type':'directions'})
                rec.write({'directions_binary': base64.b64encode(generated_note_pdf)})
        return
    # @api.depends('shipment_id.stop_ids.location_type')
    # def _compute_name(self):
    #     for stop in self:
    #         if not stop.shipment_id:
    #             stop.name = 'Stop '
    #             continue

    #         stops = stop.shipment_id.stop_ids.sorted(key=lambda s: (s.location_type != 'pickup', s.location_type == 'delivery', s.id or 0))
    #         pickup_index = None
    #         delivery_index = None
    #         others = []

    #         for i, s in enumerate(stops):
    #             if s.location_type == 'pickup' and pickup_index is None:
    #                 pickup_index = i
    #                 s.name = 'Stop 1'
    #             elif s.location_type == 'delivery':
    #                 delivery_index = i
    #                 # Temporarily set; will correct after full loop
    #                 s.name = ''
    #             else:
    #                 others.append(s)

    #         # Assign stop names to intermediate stops
    #         count = 2
    #         for s in others:
    #             s.name = f"Stop {count}"
    #             count += 1

    #         # Assign Delivery stop name as last
    #         if delivery_index is not None:
    #             stops[delivery_index].name = f"Stop {count}"


    # @api.model
    # def default_get(self, fields_list):
    #     res = super().default_get(fields_list)
    #     ctx_params = self._context.get('params', {})
    #     if ctx_params and ctx_params.get('id') and ctx_params.get('model') == 'shipment.shipment':
    #         shipment = self.env['shipment.shipment'].browse(ctx_params.get('id'))
    #         if shipment:
    #             res['name'] = f"Stop {len(shipment.stop_ids) + 1}"
    #     return res

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
                    shape_data['center']['lat'] = rec.latitude
                    shape_data['center']['lng'] = rec.longitude
                    rec.shape_data = json.dumps(shape_data)
            else:
                rec.latitude_longitude = {"lat": '', "lng": ''}

    @api.constrains('location_type', 'shipment_id')
    def _check_unique_pickup_delivery(self):
        for stop in self:
            if not stop.shipment_id:
                continue

            # Pickup check
            if stop.location_type == 'pickup':
                existing_pickups = stop.shipment_id.stop_ids.filtered(lambda s: s.location_type == 'pickup' and s.id != stop.id)
                if existing_pickups:
                    raise ValidationError("Only one Pickup Location is allowed per shipment.")

            # Delivery check
            if stop.location_type == 'delivery':
                existing_deliveries = stop.shipment_id.stop_ids.filtered(lambda s: s.location_type == 'delivery' and s.id != stop.id)
                if existing_deliveries:
                    raise ValidationError("Only one Delivery Location is allowed per shipment.")


    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            if self.location_id:
                if self.shipment_id:
                    if self.location_type == 'pickup':
                        self.shipment_id.pickup_id = self.location_id.id
                    elif self.location_type == 'delivery':
                        self.shipment_id.delivery_id = self.location_id.id
            self.street_1 = self.location_id.street_1
            self.street_2 = self.location_id.street_2
            self.city = self.location_id.city
            self.state_id = self.location_id.state_id
            self.county_id = self.location_id.county_id
            self.country_id = self.location_id.country_id
            self.zip = self.location_id.zip
            self.latitude = self.location_id.latitude
            self.longitude = self.location_id.longitude
            self.timezone = self.location_id.timezone
            self.directions = self.location_id.directions
            self.notes = self.location_id.notes
            self.shape_data = self.location_id.shape_data
            self.location_name = self.location_id.name
        else:
            self.street_1 = ''
            self.street_2 = ''
            self.city = ''
            self.state_id = False
            self.county_id = False
            # self.country_id = False
            self.zip = ''
            self.latitude = ''
            self.longitude = ''
            self.timezone = ''
            self.directions = ''
            self.notes = ''
            self.shape_data = ''

    @api.model
    def create(self, vals):
        records = super().create(vals)

        # Update stop sequence
        if vals.get('shipment_id'):
            records.shipment_id.update_stop_sequences()

        for res in records:
            if res.shipment_id:
                if not res.shipment_id.pickup_id and res.location_type == 'pickup':
                    res.shipment_id.write({'pickup_id': res.location_id.id,
                                           'pickup_street_1': res.street_1,
                                           'pickup_street_2': res.street_2,
                                           'pickup_city': res.city,
                                           'pickup_state_id': res.state_id,
                                           'pickup_county_id': res.county_id,
                                           'pickup_country_id': res.country_id,
                                           'pickup_zip': res.zip,
                                           'pickup_latitude': res.latitude,
                                           'pickup_longitude': res.longitude,
                                           'pickup_timezone': res.timezone,
                                           'pickup_contact_name': res.contact_name,
                                           'pickup_contact_phone': res.contact_phone,
                                           'pickup_contact_email': res.contact_email,
                                           'pickup_directions': res.directions,
                                           'pickup_notes': res.notes})
                elif not res.shipment_id.delivery_id and res.location_type == 'delivery':
                    res.shipment_id.write({'delivery_id': res.location_id.id,
                                           'delivery_street_1': res.street_1,
                                           'delivery_street_2': res.street_2,
                                           'delivery_city': res.city,
                                           'delivery_state_id': res.state_id,
                                           'delivery_county_id': res.county_id,
                                           'delivery_country_id': res.country_id,
                                           'delivery_zip': res.zip,
                                           'delivery_latitude': res.latitude,
                                           'delivery_longitude': res.longitude,
                                           'delivery_timezone': res.timezone,
                                           'delivery_contact_name': res.contact_name,
                                           'delivery_contact_phone': res.contact_phone,
                                           'delivery_contact_email': res.contact_email,
                                           'delivery_directions': res.directions,
                                           'delivery_notes': res.notes})
        return records

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



    @api.depends('street_1', 'street_2', 'city', 'zip', 'state_id', 'county_id', 'country_id')
    def _compute_formatted_address(self):
        """
            this compute function prepares Address for mobile app
        """
        for rec in self:
            address_parts = []
            if rec.street_1:
                address_parts.append(rec.street_1)
            if rec.street_2:
                address_parts.append(rec.street_2)
            if rec.city:
                address_parts.append(rec.city)
            if rec.county_id:
                address_parts.append(rec.county_id.name)
            if rec.state_id:
                address_parts.append(rec.state_id.name)
            if rec.zip:
                address_parts.append(rec.zip)
            if rec.country_id:
                address_parts.append(rec.country_id.name)
            rec.formatted_address = ', '.join(filter(None, address_parts))

    def write(self, values):
        old_stop_status_id = self.stop_status_id.id

        if values.get('directions'):
            for rec in self:
                rec.message_post(body=f"""<b>Directions Changed</b> :
                    <details>
                        <summary style="color: #017e84; font-weight: bold;">Show More</summary>
                        {rec.directions}
                        <h2><b><i class='fa fa-long-arrow-right'></i></b></h2>
                        {values.get('directions')}
                    </details>""", body_is_html=True)
                # T2785: directions binary field
                # shifted to _compute_directions_binary method
                # generated_note_pdf, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf('bista_driver_app.action_report_shipment_stop_instruction',rec.id,data={'type':'directions'})
                # rec.directions_binary = base64.b64encode(generated_note_pdf)

        if values.get('notes'):
            for rec in self:
                rec.message_post(body=f"""<b>Notes Changed</b> :
                    <details>
                        <summary style="color: #017e84; font-weight: bold;">Show More</summary>
                        {rec.notes}
                        <h2><b><i class='fa fa-long-arrow-right'></i></b></h2>
                        {values.get('notes')}
                    </details>""", body_is_html=True)
                # T2785: notes binary field
                # shifted to _compute_notes_binary method
                # generated_note_pdf, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf('bista_driver_app.action_report_shipment_stop_instruction',rec.id,data={'type':'notes'})
                # rec.notes_binary = base64.b64encode(generated_note_pdf)

        res = super().write(values)

        # Update stop sequence
        if 'shipment_id' in values or 'location_type' in values:
            for stop in self:
                stop.shipment_id.update_stop_sequences()

        # Update Shipment Status, if stop status is changed
        if 'stop_status_id' in values:
            if values['stop_status_id'] != old_stop_status_id:

                status_at_location = self.env.ref('bista_driver_app.stop_status_at_location')
                status_departed = self.env.ref('bista_driver_app.stop_status_departed')
                for stop in self:
                    # Stop status change to shipment.timeline.
                    if stop.shipment_id:
                        if self.env.context.get('is_from_geofencing') and self.env.context.get('from_mobile_app'):
                            source_id = self.env.ref('bista_driver_app.mobile_geofence_breach').id
                        else:
                            source_id = self.env.ref('bista_driver_geolocation_history.source_manual_update').id
                        self.env['shipment.timeline'].create({
                            'name': f"Stop status changed to {stop.stop_status_id.name} ({stop.name})",
                            'datetime': fields.Datetime.now(),
                            'user_id': self.env.user.id,
                            'user_name': self.env.user.name,
                            'driver_id': stop.shipment_id.driver_id.id if stop.shipment_id.driver_id else False,
                            'source_id': source_id ,
                            'shipment_id': stop.shipment_id.id,
                        })

                    if not stop.shipment_id or not stop.stop_status_id:
                        continue
                    if stop.location_type == 'pickup':
                        if stop.stop_status_id.id == status_at_location.id:
                            stop.shipment_id.action_set_at_pickup()
                        if stop.stop_status_id.id == status_departed.id:
                            stop.shipment_id.action_set_in_transit()
                    elif stop.location_type == 'delivery':
                        if stop.stop_status_id.id == status_at_location.id:
                            stop.shipment_id.action_set_at_delivery()
                        if stop.stop_status_id.id == status_departed.id:
                            stop.shipment_id.action_set_delivered()


        address_fields = [
            'street_1', 'street_2', 'city',
            'state_id', 'county_id', 'country_id', 'zip'
        ]

        contact_fields = [
            'latitude', 'longitude', 'timezone',
            'contact_name', 'contact_phone', 'contact_email',
            'directions', 'notes', 'planned_arrival'
        ]

        for stop in self:
            if not stop.shipment_id:
                continue

            update_vals = {}

            prefix = ''
            if stop.location_type == 'pickup':
                prefix = 'pickup_'
            elif stop.location_type == 'delivery':
                prefix = 'delivery_'

            if not prefix:
                continue

            # Address fields (sync both ways)
            for field in address_fields:
                if field in values:
                    update_vals[f'{prefix}{field}'] = values[field]

            # fields (stop → shipment only)
            for field in contact_fields:
                if field in values:
                    name = f'{prefix}{field}'
                    if field == 'planned_arrival' and stop.planned_arrival:
                        if stop.location_type == 'pickup':
                            update_vals['planned_pickup'] = stop.planned_arrival
                            update_vals['pickup_timezone'] = stop.timezone
                        elif stop.location_type == 'delivery':
                            update_vals['planned_delivery'] = stop.planned_arrival
                            update_vals['delivery_timezone'] = stop.timezone
                    else:
                        update_vals[name] = values[field]

            if update_vals:
                # T2650: Change Made notification
                if 'skip_change_mode' in self.env.context and 'from_shipment' not in self.env.context:
                    update_vals.update({'status_id': self.shipment_id.status_id.id})
                stop.shipment_id.with_context(sync_from_stop=True).write(update_vals)

        return res
    # T2650: Change Made notification
    def web_save(self, vals, specification: Dict[str, Dict], next_id=None) -> List[Dict]:
        if self and 'skip_change_mode' not in self.env.context:
            self = self.with_context(skip_change_mode=False)
        return super(ShipmentStops,self).web_save(vals, specification, next_id=next_id)

    def action_open_stop_location_map(self):
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

    def unlink(self):
        # Update stop sequence
        shipment = self.mapped('shipment_id')
        res = super().unlink()
        shipment.update_stop_sequences()
        return res

    @api.onchange("street_1", "street_2", "city", "zip", "state_id", "country_id")
    def _onchange_stops_address_fields(self):
        if not self.env.context.get('update_address'):
            return
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
            except Exception as e:
                record.latitude = ''
                record.longitude = ''

    def action_open_stops(self):
        self.ensure_one()
        ctx = {'default_shipment_id': self.shipment_id.id, 'is_from_shipment_mst': False}
        return {
            'name': _("Stops"),
            'view_mode': 'form',
            'views': [[False, 'form']],
            'res_model': 'shipment.stop',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': ctx,
        }


class StopStatus(models.Model):
    _name = 'stop.status'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'
    _description = 'Stop Status'

    name = fields.Char(string='Status', required=True)
    sequence = fields.Integer(string="Sequence")
    active = fields.Boolean('Active', default=True)
