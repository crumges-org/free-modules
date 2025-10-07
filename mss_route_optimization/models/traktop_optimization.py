# -*- coding: utf-8 -*-
import pytz
import requests
from odoo import api, fields, models, _, _lt
from odoo.exceptions import ValidationError, UserError
import logging
import json

from datetime import datetime, time, timedelta

from collections import defaultdict
from datetime import datetime, timedelta
from odoo import api, fields, models, _, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, date, time, timedelta, timezone

import math

_logger = logging.getLogger(__name__)

###########################################
# Traktop Model – Using Delivery Order Link
###########################################

class Traktop(models.Model):
    _name = 'traktop'
    _description = 'Traktop'
    _inherit = ['mail.thread']

    active = fields.Boolean(string="Active", default=True)
    
    # ─── New field to store prep/build time ────────────────────────────
    build_time = fields.Integer(
        string="Build Time (min)",
        help="Prep time inherited from the related Sale Order"
    )
    

    # Link to a confirmed delivery order (stock.picking)
    delivery_order_id = fields.Many2one('stock.picking', string="Delivery Order")
    partner_id = fields.Many2one('res.partner', string="Customer")
    delivery_address = fields.Char(string="Delivery Address")
    partner_latitude = fields.Float('Latitude', digits=(10, 7))
    partner_longitude = fields.Float('Longitude', digits=(10, 7))
    delivery_date = fields.Datetime(string='Delivery Date')
    # distance = fields.Float(string="Distance (km)")
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    vehicle_name = fields.Char(string="Vehicle Name")
    display_name = fields.Char(string="Display Name", compute="_compute_display_name")
    vehicle_starting_point = fields.Char(string="Starting Point", compute="_compute_vehicle_address")
    driver_name = fields.Char(string="Driver", compute="_compute_driver_name", store=True)
    sequence = fields.Integer(string="Sequence", default=10)
    # _order = 'sequence'
    route_sequence = fields.Integer("Route Sequence")
    _order = 'route_sequence, id'

    # Fields for distance and travel time
    travel_time = fields.Float(
        string="Drive Time (min)",
        digits=(12, 2),
        help="Accumulated driving minutes up to this stop"
    )
    distance_km = fields.Float(
        string="Distance (km)",
        digits=(12, 2),
        help="Accumulated kilometers up to this stop"
    )

    # Fields for routing
    route_id = fields.Integer("Route ID")
    route_sequence = fields.Integer("Route Sequence")
    step_type = fields.Selection(
        [('start', 'Start'), ('job', 'Job'), ('end', 'End')],
        string="Step Type"
    )
    
    # New field to allow manual override of the assigned vehicle
    manual_vehicle_override = fields.Boolean(string="Manual Vehicle Assignment", default=False)

    info_message = fields.Html(string="Info", compute='_compute_info_message', sanitize=False)

    @api.depends()
    def _compute_info_message(self):
        for rec in self:
            rec.info_message = """
                <div style="padding: 10px; background: #e6f7ff; border-left: 4px solid #1890ff; font-size: 14px;">
                    <strong>Info:</strong> These are filtered delivery orders. Group by <i>Vehicle</i> for better route planning.
                </div>
            """
    usage_display1 = fields.Char(string="Usage", store=False, default="8")

    @api.depends('create_uid')
    def _compute_usage_display(self):
        for record in self:
            registration = self.env['mss_route_optimization.user.registration'].search([
                ('partner_id', '=', record.create_uid.partner_id.id),
                ('company_id', '=', record.env.company.id),
            ], limit=1)
            record.usage_display = registration.usage_display or 'N/A'


    def _compute_usage(self):
        self.env
    def action_view_products(self):
        self.ensure_one()
        # Use your module’s XML‑ID here
        action = self.env.ref('mss_route_optimization.action_traktop_products').sudo().read()[0]
        action.update({
            'domain': [('picking_id', '=', self.delivery_order_id.id)],
            'context': {'default_picking_id': self.delivery_order_id.id},
        })
        return action
    
    @api.model
    def is_admin(self):
        return self.env.user.has_group("base.group_system")
    
    @api.model
    def get_google_map_api_key(self):
        # Use sudo() to bypass access restrictions
        return self.env['ir.config_parameter'].sudo().get_param(
            "address_autocomplete_gmap_widget.google_map_api_key"
        )
    
    def action_view_delivery_order(self):
        """Open the related Delivery Order form view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delivery Order',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.delivery_order_id.id,
            'target': 'current',
        }
    
    @api.depends('vehicle_id')
    def _compute_driver_name(self):
        for record in self:
            record.driver_name = record.vehicle_id.driver_id.name if record.vehicle_id.driver_id else ''
    
    @api.depends('vehicle_id')
    def _compute_vehicle_address(self):
        for record in self:
            record.vehicle_starting_point = record.vehicle_id.address if record.vehicle_id else ''
    
    @api.depends('partner_id', 'delivery_order_id')
    def _compute_display_name(self):
        for record in self:
            partner_name = record.partner_id.name.upper() if record.partner_id else ''
            order_name = record.delivery_order_id.name if record.delivery_order_id else ''
            if order_name:
                # Generate the clickable link to the Sales Order form view
                sales_order_url = "/web#id={}&model=sale.order&view_type=form".format(record.delivery_order_id.sale_id.id)
                record.display_name = f'<a href="{sales_order_url}" target="_blank">{partner_name} - {order_name}</a>'
            else:
                record.display_name = partner_name
    
    def action_view_map(self):
        self.ensure_one()
        map_view_id = self.env.ref('traktop.traktop_map_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Traktop Map View',
            'res_model': 'traktop',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(map_view_id, 'form')],
            'target': 'new',
        }
    
    def get_delivery_locations(self):
        locations = self.search([])
        routes = {}
        for loc in locations:
            if loc.route_id not in routes:
                routes[loc.route_id] = []
            routes[loc.route_id].append({
                "name": loc.display_name,
                "latitude": loc.partner_latitude,
                "longitude": loc.partner_longitude,
                "sequence": loc.route_sequence,
                "type": loc.step_type,
            })
        for route_id in routes:
            routes[route_id].sort(key=lambda x: x["sequence"])
        return {"routes": routes}
 ################################################################################
 
    
    @api.model
    def fetch_vehicle_data(self):
        vehicles = self.env['fleet.vehicle'].sudo().search([])
        vehicle_data = []
        for vehicle in vehicles:
            if vehicle.latitude and vehicle.longitude:
                try:
                    latitude = float(vehicle.latitude)
                    longitude = float(vehicle.longitude)
                    vehicle_data.append({
                        "id": vehicle.id,
                        "vehicle_name": vehicle.name,
                        "start": [longitude, latitude],
                        "end": [longitude, latitude]
                    })
                except ValueError:
                    _logger.error("Invalid location for vehicle %s: %s, %s", vehicle.name, vehicle.latitude, vehicle.longitude)
        return vehicle_data


    #############################################################################
    # ─── Integrate with VROOM API ───────────────────────────────────────────────  
    @api.model
    def integrate_vroom(self):
        vroom_url = "https://route.trakop.com:8100"
        # vroom_url = "http://solver.vroom-project.org"
        vroom_url = "https://optimize.trakop.com/"
        vehicles = self.fetch_vehicle_data()
        jobs = self.fetch_jobs_data()
        
        # Ensure delivery_date is properly serialized if present
        for job in jobs:
            if job.get('delivery_date'):
                job['delivery_date'] = job['delivery_date']
    
        payload = {
            "vehicles": vehicles,
            "jobs": jobs,
            "options": {"g": True},
        }
        apikey = self.env['ir.config_parameter'].sudo().get_param('mss_route_optimization.route_api')
        headers = {
            'Content-Type': 'application/json',
            'apikey': apikey  # or 'Authorization': f'Bearer {api_key}' if required
        }
        _logger.info("Sending headers to Routing API: %s", headers)
        try:
            _logger.info("Sending payload to Routing API: %s", json.dumps(payload, indent=4))
            headers = {
            'Content-Type': 'application/json',
            }
            if apikey:
                headers['apikey'] = apikey
            response = requests.post(vroom_url, json=payload, headers=headers, timeout=30)

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {}
                _logger.warning("VROOM response is not valid JSON")

            # Handle API rate limit
            if response_data.get("message") == "API rate limit exceeded":
                _logger.error("API rate limit exceeded. Request ID: %s", response_data.get("request_id"))
                return {"rate_limited": True}

            # Raise for HTTP errors not caught above
            response.raise_for_status()

            _logger.info("VROOM response: %s", json.dumps(response_data, indent=2))
            return response_data
        
        except requests.exceptions.RequestException as e:
            _logger.error("Error while connecting to Routing API: %s", e)
            _logger.error("Payload sent to Routing API: %s", json.dumps(payload, indent=4))
            if 'response' in locals():
                _logger.error("Response content: %s", response.text)
            raise UserError("Error connecting to Routing API: Either partners or vehicles Latitude and Longitude are missing.")
    
    @api.model
    def action_fetch_delivery_orders(self):
        # For manual/testing – create Traktop records for delivery orders in 'assigned' state
        deliveries = self.env['stock.picking'].sudo().search([
            ('state', '=', 'assigned'),
            ('picking_type_id.code', '=', 'outgoing')
        ])
        _logger.info("action_fetch_delivery_orders: Found %s delivery orders in 'assigned' state", len(deliveries))
        existing_ids = self.search([]).mapped('delivery_order_id.id')
        for picking in deliveries:
            if picking.id not in existing_ids:
                self.create({
                    'delivery_order_id': picking.id,
                    'partner_id':        picking.partner_id.id,
                    'delivery_address':  picking.partner_id.contact_address,
                    'delivery_date':     picking.scheduled_date,
                    'partner_latitude':  picking.partner_id.partner_latitude,
                    'partner_longitude': picking.partner_id.partner_longitude,
                    # ← grab build_time off the related sale.order if any:
                    'build_time':        getattr(picking.sale_id, 'build_time', 0),
                })
                _logger.info("Created Traktop record for delivery: %s", picking.name)
        return True


    def write(self, vals):
        # Check if vehicle_id is being updated manually (without the optimization context)
        if 'vehicle_id' in vals and not self.env.context.get('from_optimization', False):
            vals['manual_vehicle_override'] = True
        return super(Traktop, self).write(vals)
    
######################################################################################
    @api.model
    def fetch_jobs_data(self):
        # ───────────────────────────────────────────────────────────
        # 1) Gather all “assigned” outgoing pickings:
        deliveries = self.env['stock.picking'].sudo().search([
            ('state', '=', 'assigned'),
            ('picking_type_id.code', '=', 'outgoing'),
        ])
        _logger.info("fetch_jobs_data: Found %s delivery orders in 'assigned' state", len(deliveries))

        # ───────────────────────────────────────────────────────────
        # 2) Figure out how many vehicles we have with valid coordinates:
        vehicles = self.fetch_vehicle_data()
        num_vehicles = len(vehicles)
        if num_vehicles == 0:
            _logger.warning("fetch_jobs_data: No vehicles found with valid lat/long")
            return []

        # ───────────────────────────────────────────────────────────
        # 3) Compute total service time for all deliveries (in seconds).
        total_service_secs = 0
        # Store each job’s service time so we don’t recalc in the main loop:
        service_per_pick = {}
        for pick in deliveries:
            so = pick.sale_id
            service_secs = int((so.build_time or 0) * 60)
            total_service_secs += service_secs
            service_per_pick[pick.id] = service_secs

        # Each vehicle has 10 hours = 36 000 seconds per day available (08:00–18:00).
        daily_capacity_secs = 10 * 3600  # 36,000
        # Total daily capacity = num_vehicles * 36,000
        total_daily_capacity = num_vehicles * daily_capacity_secs

        # If total_service_secs = 200 000 and total_daily_capacity = 36 000, then days_needed = ceil(200 000 / 36 000) = 6
        days_needed = int(math.ceil(total_service_secs / total_daily_capacity))
        # At minimum we need at least 1 day in case there is any work at all.
        days_needed = max(days_needed, 1)

        _logger.info(
            "fetch_jobs_data: total_service_secs=%s, num_vehicles=%s, days_needed=%s",
            total_service_secs, num_vehicles, days_needed
        )

        # ───────────────────────────────────────────────────────────
        # 4) Prepare to build each job’s multi-day time_windows
        user_tz_name = self.env.user.tz or 'UTC'
        user_tz = pytz.timezone(user_tz_name)
        utc = pytz.UTC

        job_data = []
        for pick in deliveries:
            so = pick.sale_id
            partner = pick.partner_id
            if not (partner.partner_latitude and partner.partner_longitude):
                # Skip if no valid coordinates
                continue

            # 4.a) Determine that job’s “base date” in user TZ:
            if so.commitment_date:
                # Convert commitment_date (UTC string) → aware UTC → convert to user TZ
                dt_utc = utc.localize(fields.Datetime.from_string(so.commitment_date))
                base_local = dt_utc.astimezone(user_tz)
            else:
                base_local = datetime.now(user_tz)

            # 4.b) Generate an 08:00–18:00 window for each day from 0 to days_needed−1
            time_windows = []
            for day_offset in range(days_needed):
                this_date = base_local.date() + timedelta(days=day_offset)
                local_start = datetime.combine(this_date, time(8, 0))
                local_end   = datetime.combine(this_date, time(18, 0))

                # Localize in user TZ then convert to UTC timestamps
                start_utc = user_tz.localize(local_start).astimezone(utc)
                end_utc   = user_tz.localize(local_end).astimezone(utc)

                time_windows.append([
                    int(start_utc.timestamp()),
                    int(end_utc.timestamp())
                ])

            job_data.append({
                "id":           pick.id,
                "oid":          pick.name,
                "user_id":      str(partner.id),
                "location":     [partner.partner_longitude, partner.partner_latitude],
                "service":      service_per_pick[pick.id],
                "time_windows": time_windows,
            })

        return job_data
    #############################################################################  
    @api.model
    def get_optimized_rec_created(self):
        try:
            _logger.info("VROOM → Entering get_optimized_rec_created()")

            # 1) Call VROOM exactly as before
            vehicles    = self.fetch_vehicle_data()
            job_payload = self.fetch_jobs_data()
            _logger.info("VROOM → sending payload with %d vehicles & %d jobs",
                         len(vehicles), len(job_payload))
            optimized = self.integrate_vroom()
            # Check for API rate limit
            if optimized.get("rate_limited"):
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'api.limit.popup',
                    'view_mode': 'form',
                    'target': 'new',
                    'name': 'API Limit Reached',
                    'view_id': self.env.ref('mss_route_optimization.view_api_limit_popup').id,
                    'views': [(self.env.ref('mss_route_optimization.view_api_limit_popup').id, 'form')],
                }

            routes    = optimized.get("routes", [])
            _logger.info("VROOM → got %d routes back", len(routes))

            # 2) Flatten & sort all job‐steps by arrival, capturing VROOM’s 'distance' & 'duration'
            #    We will use these to compute cumulative travel_time & distance_km.
            job_steps = []
            for route in routes:
                vid = route.get("vehicle")
                for step in route.get("steps", []):
                    if step.get("type") == "job" and "arrival" in step:
                        job_steps.append((vid, step))
            job_steps.sort(key=lambda x: x[1]["arrival"])
            _logger.info("VROOM → total job_steps after sort: %d", len(job_steps))

            # 3) Prepare timezone helpers + per‐vehicle accumulators
            user_tz_name = self.env.user.tz or "UTC"
            user_tz = pytz.timezone(user_tz_name)
            utc = pytz.UTC

            cursors = {}   # next‐available UTC timestamp per vehicle
            accum_secs = {}  # running sum of step["duration"] per vehicle (in seconds)

            # 4) Loop through each job step → schedule + write travel_time/distance_km on existing Traktop rec
            for vehicle_id, step in job_steps:
                pick_id = step["job"]
                picking = self.env["stock.picking"].browse(pick_id)
                if not picking:
                    _logger.warning("VROOM → missing picking %s; skipping", pick_id)
                    continue

                so = picking.sale_id
                service_secs = int((so.build_time or 0) * 60)
                _logger.info(
                    "VROOM → vehicle %s, picking %s, service=%s secs",
                    vehicle_id, picking.name, service_secs
                )

                # ─ initialize cursor & accumulators once per vehicle ───────────
                if vehicle_id not in cursors:
                    today_local = datetime.now(user_tz).date()
                    local_0800  = datetime.combine(today_local, time(8, 0))
                    utc_0800    = user_tz.localize(local_0800).astimezone(utc)
                    cursors[vehicle_id] = int(utc_0800.timestamp())
                    accum_secs[vehicle_id] = 0
                    _logger.info(
                        "VROOM → init cursor for vehicle %s = %s (UTC)",
                        vehicle_id, utc_0800
                    )

                cursor = cursors[vehicle_id]

                # ─ compute this local day’s 08:00–18:00 window in UTC ───────
                local_day   = datetime.fromtimestamp(cursor, tz=utc).astimezone(user_tz).date()
                local_start = datetime.combine(local_day, time(8, 0))
                local_end   = datetime.combine(local_day, time(18, 0))
                win_start_utc = int(user_tz.localize(local_start).astimezone(utc).timestamp())
                win_end_utc   = int(user_tz.localize(local_end).astimezone(utc).timestamp())

                # If before 08:00, jump to 08:00
                if cursor < win_start_utc:
                    cursor = win_start_utc
                # If it won’t fit before 18:00, roll to next day @08:00
                if cursor + service_secs > win_end_utc:
                    tomorrow_local = local_day + timedelta(days=1)
                    tom_0800       = datetime.combine(tomorrow_local, time(8, 0))
                    cursor = int(user_tz.localize(tom_0800).astimezone(utc).timestamp())
                    _logger.info("VROOM → rolling into next day@08:00 local → %s", tom_0800)

                # ─ schedule it at `cursor` (UTC) ────────────────────────────
                date_dt_utc = datetime.fromtimestamp(cursor, tz=utc)
                date_str    = fields.Datetime.to_string(date_dt_utc)
                _logger.info("VROOM → scheduling pick %s at %s UTC", picking.name, date_str)

                # ─ 1) Accumulate driving seconds from step["duration"]
                leg_secs = int(step.get("duration", 0))
                accum_secs[vehicle_id] += leg_secs

                # ─ 2) Read cumulative metres from step["distance"] and convert to km
                job_metres = float(step.get("distance", 0))
                job_km     = job_metres / 1000.0

                # ─ 3) Write back to Picking.scheduled_date and SO.commitment_date
                picking.sudo().write({"scheduled_date": date_str})
                if so:
                    so.sudo().write({"commitment_date": date_str})

                # ─ 4) Update the existing Traktop record with travel_time & distance_km
                tr = self.search([("delivery_order_id", "=", pick_id)], limit=1)
                if tr:
                    tr_vals = {
                        "delivery_date": date_str,
                        "travel_time":   accum_secs[vehicle_id] / 60.0,
                        "distance_km":   job_km,
                    }
                    tr.write(tr_vals)

                # ─ 5) Advance cursor by `service_secs`
                cursors[vehicle_id] = cursor + service_secs
                _logger.info(
                    "VROOM → next cursor for vehicle %s = %s",
                    vehicle_id, cursors[vehicle_id]
                )

            # ───────────────────────────────────────────────────────────────────
            # 5) Purge old auto‐generated Traktop records & rebuild per‐vehicle
            auto = self.search([("manual_vehicle_override", "=", False)])
            _logger.info("VROOM → unlinking %d old Traktop records", len(auto))
            auto.unlink()

            from collections import defaultdict
            steps_by_vehicle = defaultdict(list)
            for route in routes:
                vid = route.get("vehicle")
                if vid:
                    steps_by_vehicle[vid].extend(route.get("steps", []))

            # ─ Recreate each Traktop “step” in order, skipping “break” steps ─────
            for route_idx, (vehicle_id, steps) in enumerate(steps_by_vehicle.items()):
                vehicle   = self.env["fleet.vehicle"].browse(vehicle_id)
                driver_id = vehicle.driver_id.id if vehicle.driver_id else False

                # Re‐initialize a local “running total” for seconds
                # so we can recalc travel_time on each new record exactly as before.
                accum_secs_this_vehicle = 0

                for seq, step in enumerate(steps):
                    # ─ Skip any “break” steps ────────────────
                    if step.get("type") == "break":
                        continue

                    vals = {
                        "vehicle_id":     vehicle.id,
                        "vehicle_name":   vehicle.name,
                        "route_id":       route_idx,
                        "route_sequence": seq,
                        "step_type":      step.get("type"),  # 'start', 'job', or 'end'
                    }

                    # If it's a “start” or “end,” zero out everything:
                    if step["type"] in ("start", "end"):
                        vals.update({
                            "partner_id":        driver_id,
                            "partner_latitude":  float(vehicle.latitude)  or 0.0,
                            "partner_longitude": float(vehicle.longitude) or 0.0,
                            "travel_time":       0.0,
                            "distance_km":       0.0,
                        })

                    else:
                        # It's a “job” step. We can re‐compute the same values:
                        job_id = step.get("job")
                        dp     = self.env["stock.picking"].browse(job_id)
                        if dp:
                            vals.update({
                                "delivery_order_id": dp.id,
                                "partner_id":        dp.partner_id.id,
                                "delivery_address":  dp.partner_id.address,
                                "delivery_date":     dp.scheduled_date,
                                "partner_latitude":  dp.partner_id.partner_latitude,
                                "partner_longitude": dp.partner_id.partner_longitude,
                                "build_time":        dp.sale_id.build_time or 0,
                            })

                        # Re‐accumulate travel_time & distance in the same way:
                        leg_secs = int(step.get("duration", 0))
                        accum_secs_this_vehicle += leg_secs
                        leg_metres = float(step.get("distance", 0))
                        leg_km     = leg_metres / 1000.0

                        vals.update({
                            "travel_time":  accum_secs_this_vehicle / 60.0,
                            "distance_km":  leg_km,
                        })

                        existing = self.search([("delivery_order_id", "=", job_id)], limit=1)
                        if existing:
                            # If user manually overrode “vehicle_id,” just update route_sequence & skip re‐creating
                            if existing.manual_vehicle_override:
                                existing.with_context(from_optimization=True).write({
                                    "route_id":       route_idx,
                                    "route_sequence": seq,
                                })
                                continue
                            else:
                                existing.unlink()

                    # Finally, create a new Traktop record with travel_time & distance_km included
                    self.with_context(from_optimization=True).create(vals)

            # ───────────────────────────────────────────────────────────────────
            # 6) Recompute per‐vehicle route_sequence (exactly as before)
            self.recalculate_route_sequence()
            # ───────────────────────────────────────────────────────────────────
            # 7) Log usage by calling external API
            try:
                registration = self.env['mss_route_optimization.user.registration'].search([], order='create_date desc', limit=1)
                user_email = registration.email
                if user_email:
                    payload = {"email": user_email}
                    usage_resp = requests.post(
                        "https://optimize.trakop.com/route/log-usage",
                        json=payload,
                        timeout=10
                    )
                    if usage_resp.status_code == 200:
                        usage_data = usage_resp.json()
                        usage_display_str= usage_data.get("usage_display")
                        _logger.info("VROOM → Usage logged: %s", usage_display_str)
                        registration.sudo().write({
                            "usage_display": usage_display_str
                        })

                        # Optional: Save or display `usage_display` if needed
                    else:
                        _logger.warning("VROOM → Usage log API failed: %s", usage_resp.text)
            except Exception as e:
                _logger.warning("VROOM → Exception during usage log: %s", str(e))


            return {
                "type": "ir.actions.client",
                "tag":  "display_notification",
                "params": {
                    "title":   _("Success"),
                    "message": _("Routes & dates updated (with rollover)."),
                    "type":    "success",
                    "sticky":  False,
                    "next":    {"type": "ir.actions.client", "tag": "reload"},
                },
            }

        except Exception as e:
            _logger.exception("VROOM → Exception in get_optimized_rec_created")
            raise UserError(_("Error optimizing routes: %s") % e)



               
 ########################################################

    def recalculate_route_sequence(self):
        """
        Recalculate the route sequence per vehicle by calling the VROOM API.
        Now we only consider vehicles that have at least one job record.
        """
        # Only process vehicles that have at least one job step.
        job_vehicle_ids = self.search([('step_type', '=', 'job')]).mapped('vehicle_id.id')
        for vehicle_id in set(job_vehicle_ids):
            vehicle_rec = self.env['fleet.vehicle'].browse(vehicle_id)
            # Gather all Traktop records for this vehicle.
            orders = self.search([('vehicle_id', '=', vehicle_id)])
            # Skip if there are no orders or if there is no valid vehicle coordinate.
            if not orders or not (vehicle_rec.latitude and vehicle_rec.longitude):
                continue
            try:
                lat = float(vehicle_rec.latitude)
                lon = float(vehicle_rec.longitude)
            except ValueError:
                continue

            vehicle_data = {
                "id": vehicle_rec.id,
                "vehicle_name": vehicle_rec.name,
                "start": [lon, lat],
                "end": [lon, lat]
            }
            jobs_data = []
            for order in orders:
                if order.step_type == 'job' and order.delivery_order_id and order.partner_latitude and order.partner_longitude:
                    # compute same 8–18 window on order.delivery_date
                    sched = fields.Datetime.from_string(order.delivery_date)
                    start_dt = datetime.combine(sched.date(), time(8, 0))
                    end_dt   = datetime.combine(sched.date(), time(18, 0))
                    start_ts = int(start_dt.timestamp())
                    end_ts   = int(end_dt.timestamp())

                    # prep time
                    service_secs = int((order.delivery_order_id.sale_id.build_time or 0) * 60)

                    jobs_data.append({
                        "id":               order.delivery_order_id.id,
                        "oid":              order.delivery_order_id.name,
                        "user_id":          str(order.partner_id.id) if order.partner_id else '',
                        "location":         [order.partner_longitude, order.partner_latitude],
                        "service":          service_secs,
                        "time_windows":   [[start_ts, end_ts]],
                        "partner_latitude":  order.partner_latitude,
                        "partner_longitude": order.partner_longitude,
                    })

            # Only call the API if there is at least one job.
            if not jobs_data:
                _logger.info("No job records found for vehicle %s; skipping route sequence recalculation.", vehicle_rec.name)
                continue

            payload = {
                "vehicles": [vehicle_data],
                "jobs": jobs_data,
                "options": {"g": True},
            }
            try:
                _logger.info("Recalculating route sequence for vehicle %s using payload: %s", vehicle_rec.name, json.dumps(payload, indent=4))
                # response = requests.post("https://route.trakop.com:8100", json=payload, timeout=30)
                apikey = self.env['ir.config_parameter'].sudo().get_param('mss_route_optimization.route_api')
                headers = {
                    'Content-Type': 'application/json',
                    'apikey': apikey
                }
                response = requests.post("https://optimize.trakop.com/", json=payload, headers=headers, timeout=30)

                # response = requests.post("http://solver.vroom-project.org", json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                _logger.info("VROOM recalc response: %s", json.dumps(result, indent=2))
                routes = result.get("routes", [])
                if routes:
                    route = routes[0]  # We assume one vehicle per payload.
                    steps = route.get("steps", [])
                    for seq, step in enumerate(steps):
                        if step.get("type") == "job":
                            job_id = step.get("job")
                            # Update the route_sequence for the matching Traktop record.
                            tr_record = self.search([('delivery_order_id', '=', job_id), ('vehicle_id', '=', vehicle_id)], limit=1)
                            if tr_record:
                                tr_record.write({'route_sequence': seq})
                else:
                    _logger.info("No routes returned from VROOM API for vehicle %s.", vehicle_rec.name)
            except Exception as e:
                _logger.error("Error recalculating route sequence for vehicle %s: %s", vehicle_rec.name, str(e))
                raise UserError("Error recalculating route sequence for vehicle %s" % vehicle_rec.name)
            
###########################################
# Extend Sale Order – Create/Update/Delete Traktop via Delivery Orders
###########################################

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    build_time = fields.Integer(
        string="Build Time (min)",
        default=30,
        help="Minutes needed to prepare this order"
    )

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            pickings = order.picking_ids.filtered(
                lambda p: p.picking_type_id.code == 'outgoing' and p.state == 'assigned'
            )
            for picking in pickings:
                existing = self.env['traktop'].search(
                    [('delivery_order_id', '=', picking.id)], limit=1
                )
                if not existing:
                    self.env['traktop'].create({
                        'delivery_order_id': picking.id,
                        'partner_id':         order.partner_shipping_id.id,
                        'delivery_address':   order.partner_shipping_id.contact_address,
                        'delivery_date':      order.commitment_date,
                        'partner_latitude':   order.partner_shipping_id.partner_latitude,
                        'partner_longitude':  order.partner_shipping_id.partner_longitude,
                        # ← propagate build_time here:
                        'build_time':         order.build_time,
                    })
                    _logger.info(
                        "Sale Order %s confirmed: created Traktop record for delivery %s",
                        order.name, picking.name
                    )
        return res


    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('order_line', 'commitment_date')):
            for order in self:
                pickings = order.picking_ids.filtered(
                    lambda p: p.picking_type_id.code == 'outgoing' and p.state == 'assigned'
                )
                for picking in pickings:
                    existing = self.env['traktop'].search(
                        [('delivery_order_id', '=', picking.id)], limit=1
                    )
                    if not existing:
                        self.env['traktop'].create({
                            'delivery_order_id': picking.id,
                            'partner_id':         order.partner_shipping_id.id,
                            'delivery_address':   order.partner_shipping_id.contact_address,
                            'delivery_date':      order.commitment_date,
                            'partner_latitude':   order.partner_shipping_id.partner_latitude,
                            'partner_longitude':  order.partner_shipping_id.partner_longitude,
                            # ← and here too:
                            'build_time':         order.build_time,
                        })
                        _logger.info(
                            "Sale Order %s updated: created Traktop record for delivery %s",
                            order.name, picking.name
                        )
        return res


    def unlink(self):
        for order in self:
            for picking in order.picking_ids:
                traktop_rec = self.env['traktop'].search([('delivery_order_id', '=', picking.id)])
                if traktop_rec:
                    traktop_rec.unlink()
                    _logger.info("Sale Order %s deleted: removed Traktop record for delivery %s", order.name, picking.name)
        return super(SaleOrder, self).unlink()

###########################################
# Extend Stock Picking – Keep Traktop Records in Sync with Picking State
###########################################

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if 'state' in vals:
            for picking in self:
                if picking.picking_type_id.code == 'outgoing':
                    picking_state = picking.state
                    _logger.info("Processing picking %s with new state: %s", picking.name, picking_state)
                    # Use sudo() to ensure we have the necessary rights
                    traktop_records = self.env['traktop'].sudo().search([('delivery_order_id', '=', picking.id)])
                    if picking_state == 'assigned':
                        if not traktop_records:
                            self.env['traktop'].sudo().create({
                                'delivery_order_id': picking.id,
                                'partner_id': picking.partner_id.id,
                                'delivery_address': picking.partner_id.contact_address,
                                'delivery_date': picking.scheduled_date,
                                'partner_latitude': picking.partner_id.partner_latitude,
                                'partner_longitude': picking.partner_id.partner_longitude,
                                'build_time':        getattr(picking.sale_id, 'build_time', 0),
                            })
                            _logger.info("Created Traktop record for picking %s", picking.name)
                    else:
                        if traktop_records:
                            _logger.info("Unlinking %d Traktop record(s) for picking %s", len(traktop_records), picking.name)
                            traktop_records.sudo().unlink()
                            _logger.info("Removed Traktop record for picking %s", picking.name)
        return res

    def action_done(self):
        """Triggered when the picking is validated and moves to 'done'."""
        res = super(StockPicking, self).action_done()
        for picking in self:
            if picking.picking_type_id.code == 'outgoing':
                traktop_rec = self.env['traktop'].sudo().search([
                    ('delivery_order_id', '=', picking.id)
                ])
                if traktop_rec:
                    _logger.info("Removing Traktop record(s) for picking %s as state is now 'done'.", picking.name)
                    traktop_rec.sudo().unlink()
        return res

    def button_validate(self):
        """
        Odoo calls this method when you click Validate on a picking.
        It often calls action_done() internally, but we can ensure the record is removed here as well.
        """
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.picking_type_id.code == 'outgoing' and picking.state == 'done':
                traktop_rec = self.env['traktop'].sudo().search([
                    ('delivery_order_id', '=', picking.id)
                ])
                if traktop_rec:
                    _logger.info("Removing Traktop record(s) for picking %s on button_validate.", picking.name)
                    traktop_rec.sudo().unlink()
            self.env['traktop'].sudo().action_fetch_delivery_orders()
        return res

###########################################
# Other Models (ResPartner, ResConfigSettings, FleetVehicle)
###########################################

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    address = fields.Char(string="Address")
    longitude = fields.Char(string="Longitude")
    latitude = fields.Char(string="Latitude")
    ne_latitude = fields.Char(string="North-East Latitude")
    ne_longitude = fields.Char(string="North-East Longitude")
    sw_latitude = fields.Char(string="South-East Latitude")
    sw_longitude = fields.Char(string="South-East Longitude")
    
    live_latitude = fields.Float(string="Live Latitude", digits=(10, 7))
    live_longitude = fields.Float(string="Live Longitude", digits=(10, 7))
    last_seen = fields.Datetime(string="Last Seen")
    speed = fields.Float(string="Speed")

    @api.model
    def create(self, vals):
        partner = super(ResPartner, self).create(vals)
        if 'latitude' in vals and 'longitude' in vals:
            partner.geo_localize()
        elif any(field in vals for field in ['street', 'city', 'zip', 'state_id', 'country_id']):
            partner.geo_localize()
        return partner

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if 'latitude' in vals and 'longitude' in vals:
            self.geo_localize()
        elif any(field in vals for field in ['street', 'city', 'zip', 'state_id', 'country_id']):
            self.geo_localize()
        return res

    def geo_localize(self):
        for partner in self:
            if partner.latitude and partner.longitude:
                partner.write({
                    'partner_latitude': float(partner.latitude),
                    'partner_longitude': float(partner.longitude),
                })
            else:
                super(ResPartner, partner).geo_localize()

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_map_api_key = fields.Char(string="Google Map API Key", config_parameter="address_autocomplete_gmap_widget.google_map_api_key")

class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    address = fields.Char(string="Address")
    longitude = fields.Char(string="Longitude")
    latitude = fields.Char(string="Latitude")
    ne_latitude = fields.Char(string="North-East Latitude")
    ne_longitude = fields.Char(string="North-East Longitude")
    sw_latitude = fields.Char(string="South-East Latitude")
    sw_longitude = fields.Char(string="South-East Longitude")
    address = fields.Char(string="Address")
    longitude = fields.Char(string="Longitude")
    latitude = fields.Char(string="Latitude")
    ne_latitude = fields.Char(string="North-East Latitude")
    ne_longitude = fields.Char(string="North-East Longitude")
    sw_latitude = fields.Char(string="South-East Latitude")
    sw_longitude = fields.Char(string="South-East Longitude")

class StockMove(models.Model):
    _inherit = 'stock.move'

    picked = fields.Boolean(
        string="Picked",
        default=False,
        help="Check when this product has been physically picked"
    )

class ApiLimitPopup(models.TransientModel):
    _name = 'api.limit.popup'
    _description = 'API Limit Popup'
    
    name = fields.Char(default="API Limit Reached")
    def action_contact(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.mastersoftwaresolutions.com/request-live-preview',
            'target': 'new',
        }

