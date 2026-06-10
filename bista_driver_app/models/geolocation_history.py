# -*- coding: utf-8 -*-
from odoo import fields, models, api, _, SUPERUSER_ID
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class GeolocationHistory(models.Model):
    _name = 'geolocation.history'
    _order = 'date_recorded desc'

    shipment_id = fields.Many2one('shipment.shipment', string="Shipment")
    carrier_id = fields.Many2one('fleet.driver', string="Carrier", tracking=True)
    device_unique_id = fields.Char(string="Device ID")
    device_info = fields.Json(string="Device Name") #device_brand, device_model, device_os, eld_name
    device_name = fields.Char(String="Device Name", compute="_compute_device_name")

    # From Inventory geolocation
    lot_id = fields.Many2one('stock.lot',string="Serial #")
    # product_id = fields.Many2one('product.product', string="Product", related='lot_id.product_id')
    timestamp = fields.Float(digits=(16, 0), tracking=True)
    # assets_id = fields.Many2one('samsara.assets', string="Asset Tracker")
    location_name = fields.Char(string="Location Name")

    def action_open_reference(self):
        """ Open the form view of the move's reference document, if one exists, otherwise open form view of self
        """
        self.ensure_one()
        if not self.reference:
            lot_id = self.lot_id
            if lot_id:
                return {
                    'res_model': lot_id._name,
                    'type': 'ir.actions.act_window',
                    'views': [[False, "form"]],
                    'res_id': lot_id.id,
                }
        return super(GeolocationHistory, self).action_open_reference()

    def create(self, vals):
        """
            In the geolocation history map view to show only the latest records, latest field is taken to keep track
            of the latest records of same serial/asset tracker.
        """
        try:
            if self._context.get('location_update_res_model', False) == "samsara.assets":
                vals.update({
                    'speed': self._context['speed_miles_per_hour'] * 1.46667 if self._context.get(
                        'speed_miles_per_hour', False) else 0,
                    'date_recorded': datetime.fromtimestamp(
                        self._context.get('timestamp') / 1000.0) if self._context.get('timestamp',
                                                                                      False) else fields.Datetime.now(),
                    'timestamp': self._context.get('timestamp', False),
                })
            if not vals.get('date_recorded', False):
                vals.update({'date_recorded': fields.Datetime.now()})

            if vals.get('lot_id') and not vals.get('reference'):
                latest_record = self.sudo().search([('lot_id', '=', vals.get('lot_id')), ('latest', '=', True)],
                                                   order='id desc', limit=1)
                if latest_record:
                    if not latest_record.date_recorded:
                        latest_record.date_recorded = latest_record.create_date

                    if latest_record.date_recorded < vals.get('date_recorded'):
                        vals.update({'latest': True})
                        latest_record.latest = False
                else:
                    vals.update({'latest': True})
            # vals.update({'latest': True})
            return super().create(vals)
        except:
            return super().create(vals)

    ### From Inventory geolocation END


    @api.depends('device_info')
    def _compute_device_name(self):
        for rec in self:
            info = rec.device_info or {}
            eld_name = info.get('eld_name', '')
            brand = info.get('device_brand', '')
            model = f"-{info.get('device_model', '')}" if info.get('device_model', '') else ''
            os = f"-{info.get('device_os', '')}" if info.get('device_os', '') else ''
            rec.device_name = f"{eld_name}{brand}{model}{os}"

    def _compute_display_name(self):
        """
            Display name for left section in the map view
        """
        super()._compute_display_name()
        for rec in self:
            if rec.reference:
                rec.display_name = str(rec.reference.name)

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    source = fields.Selection([
        ('manual_update', 'Manual Update'),
        ('use_my_location_button', 'Use My Location Button'),
        ('driver_phone', 'Driver Phone'),
    ], string="Source(old)")
    source_id = fields.Many2one('geolocation.source', string="Source")
    source_name = fields.Char(compute="_compute_source_name", string="Source Name", readonly=True, store=True)
    reference = fields.Reference(string="Reference",
                                 compute_sudo=False, readonly=False,
                                 selection='_selection_target_model',
                                 store=True
                                 )
    asset_latitude = fields.Float(string="Latitude", digits=(16, 7), group_operator=False)
    asset_longitude = fields.Float(string="Longitude", digits=(16, 7), group_operator=False)
    company_id = fields.Many2one('res.company', string="Company")
    latest = fields.Boolean(string="Latest")
    approximate_location = fields.Float(string="Approximate Location (ft)", digit=(16, 6), group_operator=False)
    speed = fields.Float(string="Speed (ft/s)", group_operator=False)

    # T2492 Add fields to Geolocation History Master Table
    date_recorded = fields.Datetime(string="Date")
    # carrier_name = fields.Char(string="Carrier")
    connectivity_status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline')
    ], string="Connectivity")
    timezone = fields.Char(string="Timezone")

    # T2564 Geolocation History List – Detail View with Map
    latitude_longitude = fields.Char(compute='_compute_coordinates', string="Latitude Longitude", store=True)

    # T2564 Geolocation History List – Detail View with Map
    @api.depends("asset_latitude", "asset_longitude")
    def _compute_coordinates(self):
        """
        This method is written to pass values to the MAP. It will execute if the user
        enters a value, otherwise, the condition will pass default values.
        """
        for rec in self:
            if rec.asset_latitude and rec.asset_longitude:
                rec.latitude_longitude = {"lat": rec.asset_latitude, "lng": rec.asset_longitude}

    @api.constrains('source_id')
    def _compute_source_name(self):
        for rec in self:
            if rec.source_id:
                rec.source_name = rec.source_id.name

    def action_open_reference(self):
        """ Open the form view of the move's reference document, if one exists, otherwise open form view of self
        """
        self.ensure_one()
        source = self.reference
        if source:
            return {
                'res_model': source._name,
                'type': 'ir.actions.act_window',
                'views': [[False, "form"]],
                'res_id': source.id,
            }
        return False

    def create(self, vals):
        """
            In the geolocation history map view to show only the latest records, latest field is taken to keep track
            of the latest records of same serial/asset tracker.
        """
        try:
            if vals.get('reference'):
                if not vals.get('date_recorded', False):
                    vals.update({'date_recorded': fields.Datetime.now()})
                latest_record = self.sudo().search([('reference', '=', vals.get('reference')), ('latest', '=', True)],
                                                   order='id desc', limit=1)
                if latest_record:
                    if not latest_record.date_recorded:
                        latest_record.date_recorded = latest_record.create_date
                    # from app the date_recorded is being processed as string
                    new_date_recorded = vals.get('date_recorded')
                    if type(vals.get('date_recorded')) == str:
                        new_date_recorded = datetime.strptime(vals.get('date_recorded'), '%Y-%m-%d %H:%M:%S')

                    if latest_record.date_recorded < new_date_recorded:
                        vals.update({'latest': True})
                        latest_record.latest = False
                else:
                    vals.update({'latest': True})
            # T2493: Convert accuracy and speed unit from meter to feet
            if vals.get('approximate_location') and vals['approximate_location']:
                vals['approximate_location'] = vals['approximate_location'] * 3.28084  # Convert meter to feet
            if vals.get('speed') and vals['speed']:
                vals['speed'] = vals['speed'] * 3.28084  # Convert meter to feet

            return super().create(vals)
        except:
            return super().create(vals)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        """
            In the geolocation history map view show only the latest records, if history records of multiple
            serial number/asset tracker exists
        """
        if self.env.context.get('view_mode') == 'geolocation_history':
            domain += [('latest', '=', True)]
        res = super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                      count_limit=count_limit)

        return res

    # T2493: Convert accuracy and speed unit from meter to feet
    @api.model
    def _convert_accuracy_speed_unit(self):
        """
        Convert accuracy and speed unit from meter to feet in geolocation history records.
        """
        geolocation_history = self.env['geolocation.history'].search([])
        for rec in geolocation_history:
            if rec.approximate_location:
                rec.approximate_location = rec.approximate_location * 3.28084  # Convert meter to feet
            if rec.speed:
                rec.speed = rec.speed * 3.28084

    @api.model
    def _populate_timezone_from_lat_lng(self):
        """
            Scheduled Action: Driver\System\Geolocation History: Populate timezone from latitude and longitude
        """
        geolocation_history_ids = self.sudo().search([
            ('date_recorded', '!=', False),
            ('reference', 'ilike', 'shipment.shipment,'),
        ])

        for history_id in geolocation_history_ids:
            lat = history_id.asset_latitude
            lng = history_id.asset_longitude
            date_recorded = history_id.date_recorded

            if lat and lng:
                _logger.info(
                    f"Scheduled Action - Populate timezone is Running for geolocaiton_history_id: {history_id.id}")

                zone_name = TimezoneFinder().timezone_at(lat=lat, lng=lng)
                history_id.timezone = datetime.fromtimestamp(date_recorded.timestamp(), ZoneInfo(zone_name)).strftime(
                    "%Z")

    def action_update_geolocation_history_latest_attribute(self):
        """shcedule action to update the date_recorded field and latest field of geolocation.history"""

        geolocation_history_records = self.env['geolocation.history'].with_user(SUPERUSER_ID).search([])
        for rec in geolocation_history_records:
            if not rec.date_recorded:
                rec.date_recorded = rec.create_date
            domain = [('latest', '=', True)]
            if rec.reference:
                domain += [('reference', '=', f'{rec.reference._name},{rec.reference.id}')]
            elif rec.lot_id:
                domain += [('lot_id', '=', rec.lot_id.id)]
            elif rec.samsara_eld_asset_id:
                domain += [('samsara_eld_asset_id', '=', rec.samsara_eld_asset_id.id)]
            current_latest_record = self.sudo().search(domain, limit=1)

            if not current_latest_record.date_recorded:
                current_latest_record.date_recorded = current_latest_record.create_date
            if rec.exists() and current_latest_record.exists():
                if rec.date_recorded > current_latest_record.date_recorded:
                    rec.latest = True
                    current_latest_record.latest = False
        return