# -*- coding: utf-8 -*-
import logging
import re
import json
import math
import pytz
import requests
import base64
from datetime import datetime, timedelta
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID, tools
# from odoo.addons.bista_driver_app.push_notification import firebase_send_notification
from odoo.addons.bista_mobile_base.push_notification import firebase_send_notification
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from pytz import timezone, UTC
from odoo.http import serialize_exception as _serialize_exception
from shapely.geometry import Point, Polygon
from typing import Dict, List
from collections import defaultdict

_logger = logging.getLogger(__name__)

TIMEZONE_MAP = {
    'CST': 'America/Chicago',
    'EST': 'America/New_York',
    'PST': 'America/Los_Angeles',
    'MST': 'America/Denver',
    'IST': 'Asia/Kolkata',
}


def safe_get_timezone(tz_name):
    mapped_tz = TIMEZONE_MAP.get(tz_name, tz_name)
    try:
        return pytz.timezone(mapped_tz)
    except pytz.UnknownTimeZoneError:
        return pytz.utc


class Shipments(models.Model):
    _name = "shipment.shipment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Shipment"
    _order = 'id desc'

    name = fields.Char(string="Shipment No", copy=False)
    status_id = fields.Many2one('shipment.status', string="Status", tracking=True,
                                group_expand='_read_group_stage_ids', domain=lambda self: self._get_stage_domain())
    status_sequence = fields.Integer(string="Status Sequence", related='status_id.sequence')
    # call_out_id = fields.Many2one("call.out.request", ondelete='cascade', string="Call Out No", tracking=True, copy=True)
    sale_order_no = fields.Char(string="Release/SO #", tracking=True, copy=True)
    planned_pickup = fields.Datetime(string="Pickup Planned Time", tracking=True, copy=True)
    actual_pickup = fields.Datetime(string="Pickup Actual Arrival Time", tracking=True, copy=True)
    planned_delivery = fields.Datetime(string="Delivery Planned Time", tracking=True, copy=True)
    actual_delivery = fields.Datetime(string="Delivery Actual Arrival Time", tracking=True, copy=True)

    pickup_id = fields.Many2one('shipment.location', string="Pickup Location", tracking=True)
    pickup_street_1 = fields.Char(string="Pickup Street 1", tracking=True)
    pickup_street_2 = fields.Char(string="Pickup Street 2", tracking=True)
    pickup_city = fields.Char(string="Pickup City", tracking=True)
    pickup_country_id = fields.Many2one("res.country", string="Pickup Country", tracking=True,
                                        default=lambda self: self.env.ref('base.us').id)
    pickup_state_id = fields.Many2one("res.country.state", string="Pickup State", tracking=True,
                                      domain="[('country_id', '=', pickup_country_id)]")
    pickup_county_id = fields.Many2one("res.city", string="Pickup County",
                                       domain="[('state_id', '=', pickup_state_id)]", tracking=True)
    pickup_zip = fields.Char(string="Pickup Zip", tracking=True)
    pickup_latitude = fields.Char(string="Pickup Latitude")
    pickup_longitude = fields.Char(string="Pickup Longitude")
    pickup_timezone = fields.Selection([('EST', 'EST'), ('CST', 'CST'), ('MST', 'MST'), ('PST', 'PST'), ],
                                       string='Pickup Timezone')
    pickup_contact_name = fields.Char(string="Pickup Contact Name")
    pickup_contact_phone = fields.Char(string="Pickup Contact Phone")
    pickup_contact_email = fields.Char(string="Pickup Contact Email")
    pickup_directions = fields.Html(string="Pickup Directions")
    pickup_notes = fields.Html(string="Pickup Notes")
    pickup_departure_time = fields.Datetime(string="Pickup Actual Departure Time")

    delivery_id = fields.Many2one('shipment.location', string="Delivery Location", tracking=True)
    delivery_street_1 = fields.Char(string="Delivery Street 1", tracking=True)
    delivery_street_2 = fields.Char(string="Delivery Street 2", tracking=True)
    delivery_city = fields.Char(string="Delivery City", tracking=True)
    delivery_country_id = fields.Many2one("res.country", string="Delivery Country", tracking=True,
                                          default=lambda self: self.env.ref('base.us').id)
    delivery_state_id = fields.Many2one("res.country.state", string="Delivery State", tracking=True,
                                        domain="[('country_id', '=', delivery_country_id)]")
    delivery_county_id = fields.Many2one("res.city", string="Delivery County",
                                         domain="[('state_id', '=', delivery_state_id)]", tracking=True)
    delivery_zip = fields.Char(string="Delivery Zip", tracking=True)
    delivery_latitude = fields.Char(string="Delivery Latitude")
    delivery_longitude = fields.Char(string="Delivery Longitude")
    delivery_timezone = fields.Selection([('EST', 'EST'), ('CST', 'CST'), ('MST', 'MST'), ('PST', 'PST'), ],
                                         string='Delivery Timezone')
    delivery_contact_name = fields.Char(string="Delivery Contact Name")
    delivery_contact_phone = fields.Char(string="Delivery Contact Phone")
    delivery_contact_email = fields.Char(string="Delivery Contact Email")
    delivery_directions = fields.Html(string="Delivery Directions")
    delivery_notes = fields.Html(string="Delivery Notes")
    delivery_departure_time = fields.Datetime(string="Delivery Actual Departure Time")

    display_pickup_address = fields.Char(string="Pickup Address", compute="_compute_display_pickup_address", store=True)
    display_delivery_address = fields.Char(string="Delivery Address", compute="_compute_display_delivery_address",
                                           store=True)

    stop_pickup = fields.Char(string="Pickup Stop", compute="_compute_pickup_delivery_stop", store=True)
    stop_delivery = fields.Char(string="Delivery Stop", compute="_compute_pickup_delivery_stop", store=True)

    latest_latitude = fields.Char(string="Latest Latitude", tracking=False, copy=False)
    latest_longitude = fields.Char(string="Latest Longitude", tracking=False, copy=False)
    remaining_distance = fields.Char(string="Remaining Milage", tracking=False, copy=False)
    remaining_time = fields.Char(string="Remaining Time", tracking=False, copy=False)
    eta = fields.Datetime(string="ETA", tracking=False, copy=False)
    eta_last_updated = fields.Datetime(string="ETA Last Updated", tracking=False, copy=False)

    notes = fields.Html(string="Notes", copy=True)
    notes_binary = fields.Binary(string='Binary Notes',compute="_compute_notes_binary", attachment=True,store=True)
    customer_id = fields.Many2one('res.company', string="Customer", tracking=True, copy=True)
    cancel_reason = fields.Text(string="Reason For Cancellation", tracking=True)
    active = fields.Boolean(default=True, string="Archived", tracking=True)
    driver_id = fields.Many2one("fleet.driver", string="Carrier", tracking=True)
    driver_phone = fields.Char(string="Driver Phone", related="driver_id.phone", store=True, readonly=True, tracking=True)
    truck_number = fields.Char(related="driver_id.truck_no", string="Carrier Truck No", readonly=True, tracking=True)
    carrier_id = fields.Many2one(related="driver_id.carrier_id", string="Carrier Name", readonly=True, tracking=True)
    rig_contact_1 = fields.Many2one("res.partner", string="Rig Contact 1", tracking=True)
    rig_contact_2 = fields.Many2one("res.partner", string="Rig Contact 2", tracking=True)
    forklift_shipment = fields.Boolean(string="Forklift Shipment", copy=True)

    geolocation_history_ids = fields.One2many('geolocation.history', 'shipment_id', string="Geolocation History", copy=False)
    document_ids = fields.One2many('shipment.document', 'shipment_id', string="Documents", tracking=True, copy=False)
    timeline_ids = fields.One2many('shipment.timeline', 'shipment_id', string="Timeline", tracking=False, copy=False)
    stop_ids = fields.One2many('shipment.stop', 'shipment_id', string="Stops", tracking=True, copy=True)
    status_color = fields.Integer(related="status_id.color", string='Color Index')
    fold = fields.Boolean(related='status_id.fold', string='Folded in Kanban')
    item_ids = fields.One2many('shipment.item', 'shipment_id', string='Items', tracking=False, copy=True)

    is_dispatcher = fields.Boolean(string="Is Dispatcher", compute='_compute_is_dispatcher')
    # is_customer_user = fields.Boolean(string="Customer User", compute='_compute_is_customer_user', copy=False)
    is_display = fields.Boolean(string="Is Display", compute='_compute_is_display', copy=False)
    # T2663: default value is removed to make no tracking status for disabled location tracking.
    tracking_status = fields.Selection([('inactive', 'Inactive'), ('active', 'Active'), ('paused', 'Paused')], string="Mobile Tracking Status", tracking=True)
    # eld_tracking_status = fields.Selection([('inactive', 'Inactive'), ('active', 'Active')], string="ELD Tracking Status", tracking=True)
    location_tracking = fields.Selection(related='status_id.location_tracking', string="Location Tracking", store=True, readonly=True)

    # is_eld_tracking = fields.Boolean(string='ElD Tracking')
    twilio_sms_count = fields.Integer(string="Twilio SMS Count", default=0)

    @api.depends('status_id', 'status_id.do_eta_calculation')
    def _compute_is_display(self):
        for rec in self:
            rec.is_display = rec.status_id.do_eta_calculation

    def _compute_is_dispatcher(self):
        for record in self:
            record.is_dispatcher = record.env.user.has_group('bista_driver_app.group_shipment_dispatcher_access')
    
    @api.depends('notes')
    def _compute_notes_binary(self):
        for rec in self:
            if rec.notes:
                generated_note_pdf, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf('bista_driver_app.action_report_shipment_instruction',rec.id,data={'type':"notes"})
                rec.write({'notes_binary': base64.b64encode(generated_note_pdf)})
        return

    @api.model
    def _get_stage_domain(self):
        hide_stage_ids = [
            self.env.ref('bista_driver_app.shipment_status_cancelled').id
        ]
        return [('id', 'not in', hide_stage_ids)]

    # Override the method for Folded shipment stages in Kanban.
    @api.model
    def _read_group_stage_ids(self, stages=None, domain=None, order=None):
        return self.env['shipment.status'].search([])

    # def _compute_is_customer_user(self):
    #     for rec in self:
    #         is_customer_user = False
    #         if self.env.user and self.env.user.user_type == 'customer_user':
    #             is_customer_user = True
    #         rec.is_customer_user = is_customer_user

    @api.depends('stop_ids.location_type', 'stop_ids.location_name')
    def _compute_pickup_delivery_stop(self):
        for rec in self:
            pickup = rec.stop_ids.filtered(lambda s: s.location_type == 'pickup')
            delivery = rec.stop_ids.filtered(lambda s: s.location_type == 'delivery')
            rec.stop_pickup = pickup[0].location_name if pickup else ''
            rec.stop_delivery = delivery[0].location_name if delivery else ''

    @api.model_create_multi
    def create(self, vals_list):
        current_company = self.env.company
        pending_status = self.env.ref('bista_driver_app.shipment_status_pending', raise_if_not_found=False)

        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].sudo().next_by_code("shipment.shipment.seq") or _("New")
            if not vals.get("customer_id"):
                vals["customer_id"] = current_company.id
            if not vals.get("status_id") and pending_status:
                vals["status_id"] = pending_status.id

        res = super(Shipments, self).create(vals_list)

        # Create shipment.timeline records for each new shipment
        source_id = self.env.ref('bista_driver_app.source_manual_update').id  ### (geolocation.source is not Present)
        for shipment in res:
            status = shipment.status_id
            if status:
                self.env['shipment.timeline'].create({
                    'name': f"Shipment Created",
                    'datetime': fields.Datetime.now(),
                    'user_id': self.env.user.id,
                    'user_name': self.env.user.name,
                    'driver_id': shipment.driver_id.id if shipment.driver_id else False,
                    # 'source_id': source_id,
                    'shipment_id': shipment.id,
                })

        # res.update_call_out_status()
        return res

    # def action_call_out(self):
    #     self.ensure_one()
    #     if self.call_out_id:
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': 'Call Out',
    #             'res_model': 'call.out.request',
    #             'view_mode': 'form',
    #             'res_id': self.call_out_id.id,
    #         }
    #     else:
    #         raise UserError(_("No Call Out found for this Shipment"))
    #
    # # update call out status
    # def update_call_out_status(self):
    #     for shipment in self:
    #         if shipment.call_out_id:
    #             delivered_id = self.env.ref('bista_driver_app.shipment_status_delivered').id
    #             cancel_id = self.env.ref('bista_driver_app.shipment_status_cancelled').id
    #             dispatched_id = self.env.ref('bista_driver_app.shipment_status_accepted').id
    #             in_transit_id = self.env.ref('bista_driver_app.shipment_status_in_transit').id
    #             call_out_shipments = shipment.call_out_id.sudo().shipment_ids
    #
    #             if call_out_shipments and all(s.status_id.id == delivered_id for s in call_out_shipments):
    #                 if shipment.call_out_id.sudo().stage_id.id != self.env.ref('bista_call_out_request.stage_delivered_5').id:
    #                     shipment.call_out_id.sudo().action_set_delivered()
    #
    #             elif call_out_shipments and all(s.status_id.id in (delivered_id, cancel_id) for s in call_out_shipments):
    #                 if shipment.call_out_id.sudo().stage_id.id != self.env.ref('bista_call_out_request.stage_delivered_5').id:
    #                     shipment.call_out_id.sudo().action_set_delivered()
    #
    #             elif any(s.status_id.id == delivered_id for s in call_out_shipments) and any(s.status_id.id == dispatched_id for s in call_out_shipments):
    #                 if shipment.call_out_id.sudo().stage_id.id != self.env.ref('bista_call_out_request.stage_in_transit_7').id:
    #                     shipment.call_out_id.sudo().action_set_in_transit()
    #
    #             elif any(s.status_id.id == in_transit_id for s in call_out_shipments):
    #                 if shipment.call_out_id.sudo().stage_id.id != self.env.ref('bista_call_out_request.stage_in_transit_7').id:
    #                     shipment.call_out_id.sudo().action_set_in_transit()
    #
    #             elif any(s.status_id.id == dispatched_id for s in call_out_shipments):
    #                 if shipment.call_out_id.sudo().stage_id.id != self.env.ref('bista_call_out_request.stage_dispatched_4').id:
    #                     shipment.call_out_id.sudo().action_set_dispatched()

    def action_set_pending(self):
        payload_data = []
        for rec in self:
            shipment_status_record = self.env.ref('bista_driver_app.shipment_status_pending')
            rec.status_id = shipment_status_record.id
            self.create_shipment_timeline(changes= 'shipment_status', value= shipment_status_record) #create shipment timeline
            if (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'disabled':
                # T2663:no tracking status for disabled location tracking.
                rec.tracking_status = False
                rec.driver_id.is_continuous_location_tracking = False
            elif (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'enabled':
                rec.tracking_status = 'active'
                rec.driver_id.is_continuous_location_tracking = True
            if rec.driver_id and rec.id == rec.driver_id.current_shipment_id:
                rec.driver_id.current_shipment_id = False

            # T2650: moved from write function to action_set_pending send revoke notifications to previous assigned driver.
            if rec.driver_id:
                # NOTE: Shipment notification functionalities is shifted to send_shipment_notificaton(self, special_case= None)
                # notification_data_list = [{
                #     # 'shipment_id': str(rec.id),  # T2834 - removed shipment_id to solve the reported issue
                #     'body': tools.html2plaintext(f"Your Shipment {rec.name} has been revoked.", ),
                #     'title': "Shipment Revoked",
                #     'topic': f'fleet_{rec.driver_id.user_id.id}_en',
                # }, {
                #     # 'shipment_id': str(rec.id),  # T2834 - removed shipment_id to solve the reported issue
                #     'body': tools.html2plaintext(f"Su envío {rec.name} ha sido revocado.", ),
                #     'title': "Envío Revocado",
                #     'topic': f'fleet_{rec.driver_id.user_id.id}_es',
                # }]
                # payload_data.extend(notification_data_list)
                rec.send_shipment_notificaton(special_case= "shipment_revoked", driver_id= None)
                rec.driver_id = False

        # if payload_data:
        #     response = firebase_send_notification(self.with_context(is_use_fleet_firebase_configuration=True), payload_data)
        #     if response:
        #         _logger.info("Notification send.")

    def action_set_assigned(self):
        for rec in self:
            has_pickup = rec.stop_ids.filtered(lambda s: s.location_type == 'pickup')
            has_delivery = rec.stop_ids.filtered(lambda s: s.location_type == 'delivery')
            has_driver = bool(rec.driver_id)
            rec.driver_id.current_shipment_id = False
            rec.driver_id.is_continuous_location_tracking = False
            assigned_status = self.env.ref('bista_driver_app.shipment_status_assigned')
            rec.status_id = assigned_status.id
            rec.create_shipment_timeline(changes= 'shipment_status', value= assigned_status, driver_id= None)
            if has_driver:
                rec.send_shipment_notificaton(special_case= None, driver_id= None)
            if rec.location_tracking == 'disabled':
                # T2663:no tracking status for disabled location tracking.
                if rec.tracking_status and rec.tracking_status == 'active':
                    rec.tracking_status = 'inactive'

            if has_driver and (not has_pickup or not has_delivery):
                return {
                    'status': 'stops',
                    'message': "You cannot change the status to 'Assigned' because both a Pickup and a Delivery stop are required."
                }
            elif not has_driver and has_pickup and has_delivery:
                return {
                    'status': 'driver',
                    'message': "You cannot change the status to 'Assigned' because a Driver must be assigned."
                }
            elif not has_driver and (not has_pickup or not has_delivery):
                return {
                    'status': 'stops_driver',
                    'message': "You cannot change the status to 'Assigned' because both a Driver and at least one Pickup and Delivery stop are required."
                }
            else:
                return {
                    'status': 'assigned',
                    'message': "Shipment status successfully changed to 'Assigned'."
                }

    def action_set_accepted(self):
        for rec in self:
            if rec.is_valid_status_action():
                assigned_status_rec = self.env.ref('bista_driver_app.shipment_status_accepted')
                rec.create_shipment_timeline(changes= 'shipment_status', value= assigned_status_rec, driver_id= None) # shipment timeline is created from the common function
                rec.status_id = assigned_status_rec.id
                if (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'enabled':
                    rec.tracking_status = 'active'
                    rec.driver_id.is_continuous_location_tracking = True
                elif (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'disabled':
                    # T2663:no tracking status for disabled location tracking.
                    rec.tracking_status = 'inactive'
                    rec.driver_id.is_continuous_location_tracking = False
                rec.driver_id.current_shipment_id = rec.id
                # if rec.driver_id and rec.id == rec.driver_id.current_shipment_id:
                #     rec.driver_id.current_shipment_id = False
                
                # trigger firebase notification
                rec.send_shipment_notificaton(special_case= None, driver_id= None)

    def action_set_at_pickup(self):
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        for rec in self:
            if rec.is_valid_status_action():
                # Convert UTC to Eastern Time
                # tz = pytz.timezone(rec.pickup_timezone)
                tz = safe_get_timezone(rec.pickup_timezone)
                eastern_time = utc_now.astimezone(tz)

                # Update Pickup - Actual Pickup
                rec.actual_pickup = eastern_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

                # Update Actual Arrival if there is a pickup stop
                if rec.stop_ids:
                    pickup_stop = rec.stop_ids.filtered(lambda s: s.location_type == 'pickup')
                    if pickup_stop:
                        pickup_tz = safe_get_timezone(pickup_stop.timezone)
                        pickup_dt = utc_now.astimezone(pickup_tz)
                        pickup_stop.actual_arrival = pickup_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

                # rec.pickup_actual_arrival = eastern_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                assigned_status_rec = self.env.ref('bista_driver_app.shipment_status_at_pickup')
                rec.status_id = assigned_status_rec.id
                rec.create_shipment_timeline(changes= 'shipment_status', value= assigned_status_rec, driver_id= None) # shipment timeline is created from the common function

                if (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'enabled':
                    rec.tracking_status = 'active'
                    rec.driver_id.is_continuous_location_tracking = True
                elif (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'disabled':
                    # T2663:no tracking status for disabled location tracking.
                    rec.tracking_status = False
                    rec.driver_id.is_continuous_location_tracking = False
                # rec.driver_id.is_continuous_location_tracking = True
                rec.driver_id.current_shipment_id = rec.id

                # trigger firebase notification
                rec.send_shipment_notificaton(special_case= None, driver_id= None)

    def action_set_in_transit(self):
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        for rec in self:
            if self.is_valid_status_action():
                tz = safe_get_timezone(rec.pickup_timezone)
                eastern_time = utc_now.astimezone(tz)
                # Update Actual Departure if there is a pickup stop
                if rec.stop_ids:
                    pickup_stop = rec.stop_ids.filtered(lambda s: s.location_type == 'pickup')
                    if pickup_stop:
                        pickup_tz = safe_get_timezone(pickup_stop.timezone)
                        pickup_dt = utc_now.astimezone(pickup_tz)
                        pickup_stop.departure_time = pickup_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

                rec.pickup_departure_time = eastern_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                # rec.status_id = self.env.ref('bista_driver_app.shipment_status_in_transit').id
                assigned_status_rec = self.env.ref('bista_driver_app.shipment_status_in_transit')
                rec.status_id = assigned_status_rec.id
                rec.create_shipment_timeline(changes= 'shipment_status', value= assigned_status_rec, driver_id= None) # shipment timeline is created from the common function

                if (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'enabled':
                    rec.tracking_status = 'active'
                    rec.driver_id.is_continuous_location_tracking = True
                elif (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'disabled':
                    # T2663:no tracking status for disabled location tracking.
                    rec.tracking_status = False
                    rec.driver_id.is_continuous_location_tracking = False
                rec.driver_id.current_shipment_id = rec.id

                # trigger firebase notification
                rec.send_shipment_notificaton(special_case= None, driver_id= None)

    def action_set_at_delivery(self):
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        for rec in self:
            if self.is_valid_status_action():
                # Convert UTC to Eastern Time
                tz = safe_get_timezone(rec.delivery_timezone)
                eastern_time = utc_now.astimezone(tz)

                # Update Delivery - Actual Delivery
                rec.actual_delivery = eastern_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

                # Update Actual Arrival if there is a delivery stop
                if rec.stop_ids:
                    delivery_stop = rec.stop_ids.filtered(lambda s: s.location_type == 'delivery')
                    if delivery_stop:
                        delivery_tz = safe_get_timezone(delivery_stop.timezone)
                        delivery_dt = utc_now.astimezone(delivery_tz)
                        delivery_stop.actual_arrival = delivery_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

                # rec.delivery_actual_arrival = eastern_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                # rec.status_id = self.env.ref('bista_driver_app.shipment_status_at_delivery').id
                assigned_status_rec = self.env.ref('bista_driver_app.shipment_status_at_delivery')
                rec.status_id = assigned_status_rec.id
                rec.create_shipment_timeline(changes= 'shipment_status', value= assigned_status_rec, driver_id= None) # shipment timeline is created from the common function

                if (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'enabled':
                    rec.tracking_status = 'active'
                    rec.driver_id.is_continuous_location_tracking = True
                elif (rec.tracking_status and rec.tracking_status != 'paused') or not rec.tracking_status and rec.location_tracking == 'disabled':
                    # T2663:no tracking status for disabled location tracking.
                    rec.tracking_status = False
                    rec.driver_id.is_continuous_location_tracking = False
                rec.driver_id.current_shipment_id = rec.id

                # trigger firebase notification
                rec.send_shipment_notificaton(special_case= None, driver_id= None)

    def action_set_delivered(self):
        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        for rec in self:
            if rec.is_valid_status_action():
                if not rec.document_ids:
                    raise UserError(_("Upload the mandatory document for your shipment to complete Delivery."))

                tz = safe_get_timezone(rec.delivery_timezone)
                eastern_time = utc_now.astimezone(tz)

                # Update Actual Departure if there is a delivery stop
                if rec.stop_ids:
                    delivery_stop = rec.stop_ids.filtered(lambda s: s.location_type == 'delivery')
                    if delivery_stop:
                        delivery_tz = safe_get_timezone(delivery_stop.timezone)
                        delivery_dt = utc_now.astimezone(delivery_tz)
                        delivery_stop.departure_time = delivery_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

                rec.delivery_departure_time = eastern_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                # rec.status_id = self.env.ref('bista_driver_app.shipment_status_delivered').id
                assigned_status_rec = self.env.ref('bista_driver_app.shipment_status_delivered')
                rec.create_shipment_timeline(changes= 'shipment_status', value= assigned_status_rec, driver_id= None) # shipment timeline is created from the common function
                rec.status_id = assigned_status_rec.id

                # T2663:no tracking status for disabled location tracking.
                rec.tracking_status = 'inactive'
                rec.driver_id.is_continuous_location_tracking = False
                rec.driver_id.current_shipment_id = False

                
                # trigger firebase notification
                rec.send_shipment_notificaton(special_case= None, driver_id= None)

    def action_set_cancelled(self):
        # T2663:no tracking status for disabled location tracking.
        # NOTE: shifted the following codes to cancel_shipment() function of shipment.cancellation.wizard
            # as these fields values were updated before confirming cancellation, it was causing data mismatch
                # if the Cancellation is not confirmed after triggering the wizard.
        # self.tracking_status = False
        # if self.driver_id and self.id == self.driver_id.current_shipment_id:
            # self.driver_id.is_continuous_location_tracking = False
            # self.driver_id.current_shipment_id = False
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancel Shipment',
            'res_model': 'shipment.cancellation.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'force_save': True}
        }

    def action_get_cancelled(self):
        return {
            'res_model': 'shipment.cancellation.wizard',
            'context': {'active_ids': [self.id], 'active_model': 'shipment.shipment'},
            'form_id': self.env.ref('bista_driver_app.shipment_cancellation_reason_wizard_form_1').id
        }

    def is_valid_status_action(self):
        if self.driver_id and self.driver_id.current_shipment_id:
            if self.id == self.driver_id.current_shipment_id:
                return True
            else:
                raise ValidationError("You cannot change the status of other shipments while an active shipment is in progress.")
        else:
            return True

    def action_assign_driver(self):
        for rec in self:
            has_pickup = rec.stop_ids.filtered(lambda s: s.location_type == 'pickup')
            has_delivery = rec.stop_ids.filtered(lambda s: s.location_type == 'delivery')
            if rec.status_id.id in [2, 3, 4, 5, 6]:
                raise UserError(
                    "You cannot assign the driver while shipment is active. Please set the status as 'Pending' before assigning a new driver. .")
            elif not has_pickup and not has_delivery:
                raise UserError(
                    "You cannot assign the driver because both a Pickup and a Delivery stop are required.")
            elif has_pickup and not has_delivery:
                raise UserError(
                    "You cannot assign the driver because a Delivery stop is required.")
            elif not has_pickup and has_delivery:
                raise UserError(
                    "You cannot assign the driver because a Pickup stop is required.")
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Assign Driver',
                    'res_model': 'assign.driver',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'views': [(False, 'form')],
                    'target': 'new',
                }

    @api.onchange('pickup_id')
    def _onchange_pickup_id(self):
        if self.pickup_id:
            self.pickup_street_1 = self.pickup_id.street_1
            self.pickup_street_2 = self.pickup_id.street_2
            self.pickup_city = self.pickup_id.city
            self.pickup_state_id = self.pickup_id.state_id
            self.pickup_county_id = self.pickup_id.county_id
            self.pickup_country_id = self.pickup_id.country_id
            self.pickup_zip = self.pickup_id.zip
            self.pickup_latitude = self.pickup_id.latitude
            self.pickup_longitude = self.pickup_id.longitude
            self.pickup_timezone = self.pickup_id.timezone
            self.pickup_contact_name = self.pickup_id.person_name
            self.pickup_contact_phone = self.pickup_id.person_phone
            self.pickup_contact_email = self.pickup_id.person_email
            self.pickup_directions = self.pickup_id.directions
            self.pickup_notes = self.pickup_id.notes

        else:
            self.pickup_street_1 = ''
            self.pickup_street_2 = ''
            self.pickup_city = ''
            self.pickup_state_id = False
            self.pickup_county_id = False
            self.pickup_country_id = False
            self.pickup_zip = ''
            self.pickup_latitude = ''
            self.pickup_longitude = ''
            self.pickup_timezone = ''
            self.pickup_contact_name = ''
            self.pickup_contact_phone = ''
            self.pickup_contact_email = ''
            self.pickup_directions = ''
            self.pickup_notes = ''

    @api.onchange('delivery_id')
    def _onchange_delivery_id(self):
        if self.delivery_id:
            self.delivery_street_1 = self.delivery_id.street_1
            self.delivery_street_2 = self.delivery_id.street_2
            self.delivery_city = self.delivery_id.city
            self.delivery_state_id = self.delivery_id.state_id
            self.delivery_county_id = self.delivery_id.county_id
            self.delivery_country_id = self.delivery_id.country_id
            self.delivery_zip = self.delivery_id.zip

            self.delivery_latitude = self.delivery_id.latitude
            self.delivery_longitude = self.delivery_id.longitude
            self.delivery_timezone = self.delivery_id.timezone
            self.delivery_contact_name = self.delivery_id.person_name
            self.delivery_contact_phone = self.delivery_id.person_phone
            self.delivery_contact_email = self.delivery_id.person_email
            self.delivery_directions = self.delivery_id.directions
            self.delivery_notes = self.delivery_id.notes
        else:
            self.delivery_street_1 = ''
            self.delivery_street_2 = ''
            self.delivery_city = ''
            self.delivery_state_id = False
            self.delivery_county_id = False
            self.delivery_country_id = False
            self.delivery_zip = ''
            self.delivery_latitude = ''
            self.delivery_longitude = ''
            self.delivery_timezone = ''
            self.delivery_contact_name = ''
            self.delivery_contact_phone = ''
            self.delivery_contact_email = ''
            self.delivery_directions = ''
            self.delivery_notes = ''

    def get_pickup_fields(self):
        return ['pickup_street_1', 'pickup_street_2', 'pickup_city', 'pickup_state_id',
                'pickup_county_id', 'pickup_country_id', 'pickup_zip']

    def get_delivery_fields(self):
        return ['delivery_street_1', 'delivery_street_2', 'delivery_city', 'delivery_state_id', 'delivery_county_id',
                ' delivery_country_id', 'delivery_zip', ]

    def send_shipment_notificaton(self, special_case= None, driver_id = None):
        """
            -This function is used to handle the shipment notifications.
            -In special_case parameter is used for Pending, Assigned and Cancel status, and other cases if required.
            -driver_id parameter is only used for Assigned status. as this function is triggerd from write function. 
                # TODO: when a driver is assigned, trigger the Assigned status action function and call this function
                from there instead of calling from the write function.
        """
        _logger.info(f'Notificaion is being triggered from send_shipment_notificaton() function for {self.name}')
        payload_data = []
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        server_env = IrConfigParameter.get_param('bista_driver_app.server_env')
        if special_case == 'shipment_revoked':
            notification_data_list = [{
                    'body': tools.html2plaintext(f"Your Shipment {self.name} has been revoked.", ),
                    'title': "Shipment Revoked",
                    'topic': f'{server_env}_topic_id_fleet_{self.driver_id.user_id.id}_en',
                }, {
                    'body': tools.html2plaintext(f"Su envío {self.name} ha sido revocado.", ),
                    'title': "Envío Revocado",
                    'topic': f'{server_env}_topic_id_fleet_{self.driver_id.user_id.id}_es',
                }]
            payload_data.extend(notification_data_list)
        
        elif special_case == 'shipment_assigned':
            planned_pickup_date = self.planned_pickup.date().strftime("%-m/%-d/%Y")
            planned_pickup_time = self.planned_pickup.time().strftime("%I:%M %p")
            planned_delivery_date = self.planned_delivery.date().strftime("%-m/%-d/%Y")
            planned_delivery_time = self.planned_delivery.time().strftime("%I:%M %p")
            assigned_driver_rec = self.env['fleet.driver'].browse(driver_id)
            notification_data_list = [{
                'shipment_id': str(self.id),
                'body': tools.html2plaintext(
                    f"Shipment {self.name} has been assigned to you.\n"
                    f"Pickup: {self.pickup_id.name} - {planned_pickup_date} at {planned_pickup_time} {self.pickup_timezone}.\n"
                    f"Delivery: {self.delivery_id.name} - {planned_delivery_date} at {planned_delivery_time} {self.delivery_timezone}.", ),
                'title': "New Shipment Assigned",
                'topic': f'{server_env}_topic_id_fleet_{assigned_driver_rec.user_id.id}_en',
            }, {
                'shipment_id': str(self.id),
                'body': tools.html2plaintext(
                    f"Se le ha asignado el envío {self.name}.\n"
                    f"Recogida: {self.pickup_id.name} - {planned_pickup_date} a las {planned_pickup_time} {self.pickup_timezone}.\n"
                    f"Entrega: {self.delivery_id.name} - {planned_delivery_date} a las {planned_delivery_time} {self.delivery_timezone}.", ),
                'title': "Nuevo envío asignado",
                'topic': f'{server_env}_topic_id_fleet_{assigned_driver_rec.user_id.id}_es',
            }]
            payload_data.extend(notification_data_list)
        
        elif special_case == 'shipment_cancelled':
            notification_data_list = [{
                'shipment_id': str(self.id),
                'body': tools.html2plaintext(f"Your Shipment {self.name} has been cancelled.", ),
                'title': "Shipment Cancelled",
                'topic': f'{server_env}_topic_id_fleet_{self.driver_id.user_id.id}_en',
            }, {
                'shipment_id': str(self.id),
                'body': tools.html2plaintext(f"Su envío {self.name} ha sido cancelado.", ),
                'title': "Envío cancelado",
                'topic': f'{server_env}_topic_id_fleet_{self.driver_id.user_id.id}_es',
            }]
            payload_data.extend(notification_data_list)

        elif not self._context.get('from_mobile_app'):
            notification_data_list = [{
                'shipment_id': str(self.id),
                'body': tools.html2plaintext(f"Your shipment {self.name} has been changed.", ),
                'title': "Change Made",
                'topic': f'{server_env}_topic_id_fleet_{self.driver_id.user_id.id}_en',
            }, {
                'shipment_id': str(self.id),
                'body': tools.html2plaintext(f"Su envío {self.name} ha sido modificado.", ),
                'title': "Cambio realizado",
                'topic': f'{server_env}_topic_id_fleet_{self.driver_id.user_id.id}_es',
            }]
            payload_data.extend(notification_data_list)

        if payload_data:
                response = firebase_send_notification(self.with_context(is_use_fleet_firebase_configuration=True), payload_data)
                if response:
                    _logger.info("Notification send.")

        return True
    
    def create_shipment_timeline(self, changes= None, value=None, driver_id= None):
        """
            -shipment_status
        """

        source_id = self.env.ref('bista_driver_app.source_manual_update').id
        if self.env.context.get('from_mobile_app'):
            source_id = self.env.ref('bista_driver_app.source_driver_phone').id

        
        if self.driver_id:
                driver_id = self.driver_id.id

        if changes == 'shipment_status':
            status_name = value.name
                
            self.env['shipment.timeline'].create({
                'name': f"Shipment status changed to {status_name}",
                # 'datetime': fields.Datetime.now() , #T2842: this difference is added to maintain order of shipment timeline
                'datetime': fields.Datetime.now() + timedelta(seconds= 0.5), #T2842: this difference is added to maintain order of shipment timeline
                'user_id': self.env.user.id,
                'user_name': self.env.user.name,
                'driver_id': driver_id if driver_id else False,
                'source_id': source_id,
                'shipment_id': self.id,
            })
        
        if changes == 'mobile_tracking_status':
            self.env['shipment.timeline'].create({
                'name': f"Mobile Tracking status changed to {value}",
                'datetime': fields.Datetime.now(),
                'user_id': self.env.user.id,
                'user_name': self.env.user.name,
                'driver_id': driver_id if driver_id else False,
                'source_id': source_id,
                'shipment_id': self.id,
            })
        

        # if changes == 'eld_tracking_start_end':
        #     self.env['shipment.timeline'].create({
        #                 'name': value,
        #                 'datetime': fields.Datetime.now(),
        #                 'user_id': self.env.user.id,
        #                 'user_name': self.env.user.name,
        #                 'driver_id': driver_id if driver_id else False,
        #                 'source_id': source_id,
        #                 'shipment_id': self.id,
        #             })
        return
    def write(self, values):
        # NOTE: Shipment notification functionalities is shifted to send_shipment_notificaton(self, special_case= None)
        # payload_data = []
        # T2650: moved to action_set_pending to send revoke notifications.
        
        # same set of status_id is being used multiple time. so status_ref{} is declared beforehand 
        status_refs = {
            'accepted': self.env.ref('bista_driver_app.shipment_status_accepted').id,
            'in_transit': self.env.ref('bista_driver_app.shipment_status_in_transit').id,
            'at_pickup': self.env.ref('bista_driver_app.shipment_status_at_pickup').id,
            'at_delivery': self.env.ref('bista_driver_app.shipment_status_at_delivery').id,
        }
        
        # Assign driver to Shipment and set status is assigned
        if values.get('latest_latitude') and values.get('latest_longitude'):
                if self.status_id.id in status_refs.values():
                    #T2851: reset twilio_sms_count when shipment is in active status and location is updated from mobile app.
                    self.twilio_sms_count = 0
                    # Comment Out Because of Geofence Work is Off for now
                    # self.check_geofence_status()

        assigned_status = self.env.ref('bista_driver_app.shipment_status_assigned')
        if 'driver_id' in values and values.get('driver_id'):
            values['status_id'] = assigned_status.id
            self.create_shipment_timeline(changes= 'shipment_status',value= assigned_status,driver_id= values.get('driver_id'))

        # Update Tracking Status
        if 'driver_id' in values and values.get('driver_id') or 'status_id' in values and values['status_id'] == assigned_status.id:
            if (self.tracking_status and self.tracking_status != 'inactive') or self.tracking_status =='active' and assigned_status.location_tracking == 'disabled':
                # T2663:no tracking status for disabled location tracking.
                values['tracking_status'] = 'inactive'
                self.driver_id['is_continuous_location_tracking'] = False
            elif self.tracking_status and self.tracking_status != 'paused' and assigned_status.location_tracking == 'enabled':
                values['tracking_status'] = 'active'
                self.driver_id['is_continuous_location_tracking'] = True

        # NOTE: T2842 code restructure: To fix the shipment timeline order issue, geofence status and stops status
        #       is being checked before the shipment status update. 
        

        if values and values.get('status_id'):
            # For pending status is being updated in the action call from js
            # if values.get('status_id') == self.env.ref('bista_driver_app.shipment_status_pending').id:
            #     values['driver_id'] = False

            # Reset ETA when status is not in transit
            if values.get('status_id') != self.env.ref('bista_driver_app.shipment_status_in_transit').id:
                values.update({'eta': False, 'eta_last_updated': False, 'remaining_time': '', 'remaining_distance': ''})

            # Reset Latitude and Longitude
            if values.get('status_id') not in status_refs.values():
                # status_refs is decleared beforehand as same status ids are being compared in multiple places
                values.update({'latest_latitude': '', 'latest_longitude': ''})

            # Update Shipment Timeline, when status is changed
            # # shipment timeline is created from common function: create_shipment_timeline(self, changes= None, value=None, driver_id= None)
            # if values['status_id'] != self.status_id.id:
            #     status_id = self.env['shipment.status'].browse(values['status_id'])
            #     if status_id:
            #         if self.env.context.get('is_from_geofencing'):
            #             if self.env.context.get('from_mobile_app'):
            #                 source_id = self.env.ref('bista_driver_app.source_driver_phone').id
            #             # elif self.env.context.get('is_from_eld_device'):
            #             #     source_id = self.env.ref('bista_driver_app.samsara_gps_tracker').id
            #         else:
            #             source_id = self.env.ref('bista_driver_app.source_manual_update').id
            #         self.env['shipment.timeline'].create({
            #             'name': f"Shipment status changed to {status_id.name}",
            #             'datetime': fields.Datetime.now() + timedelta(seconds= 0.5), #T2842: this difference is added to maintain order of shipment timeline
            #             'user_id': self.env.user.id,
            #             'user_name': self.env.user.name,
            #             'driver_id': self.driver_id.id if self.driver_id else False,
            #             'source_id': source_id,
            #             'shipment_id': self.id,
            #         })

        # Create timeline when mobile tracking_status changes
        # if 'tracking_status' in values and self.tracking_status != values['tracking_status'] and self.env.context.get('from_mobile_app'):
        # T2896 as per the ticket requirement self.env.context.get('from_mobile_app') is removed. Tracking timeline is created for any of the source
        if 'tracking_status' in values and self.tracking_status != values['tracking_status'] :
            status_label = dict(self._fields['tracking_status'].selection).get(values['tracking_status'])
            if status_label:
                self.create_shipment_timeline(changes= 'mobile_tracking_status', value=status_label, driver_id= None) # shipment timeline is created from the common function
            #     self.env['shipment.timeline'].create({
            #         'name': f"Mobile Tracking status changed to {status_label}",
            #         'datetime': fields.Datetime.now(),
            #     'user_id': self.env.user.id,
            #     'user_name': self.env.user.name,
            #     'driver_id': self.driver_id.id if self.driver_id else False,
            #     'source_id': self.sudo().env.ref('bista_driver_app.source_manual_update').id,
            #     'shipment_id': self.id,
            # })

        # NOTE: T2842 Code restructure: For timeline order fix super call is being done at the end of the function
        # res = super().write(values)


        # same status ids are being compared in multiple places, thus status_refs in declared beforehand
        # status_refs = {
        #     'accepted': self.env.ref('bista_driver_app.shipment_status_accepted').id,
        #     'in_transit': self.env.ref('bista_driver_app.shipment_status_in_transit').id,
        #     'at_pickup': self.env.ref('bista_driver_app.shipment_status_at_pickup').id,
        #     'at_delivery': self.env.ref('bista_driver_app.shipment_status_at_delivery').id,
        # }
        for rec in self:
            message = False
            if message:
                rec.create_shipment_timeline(changes='eld_tracking_start_end', value=message,
                                              driver_id=None)  # shipment timeline is created from the common function


            skip_change_mode = rec.env.context.get('skip_change_mode',True)
            # rec.update_call_out_status()
            # NOTE: T2842 code restructure: to maintain the Timeline order, geofence check is being done before the shipment status update
            # if values.get('latest_latitude') and values.get('latest_longitude'):
            #     if rec.status_id.id in status_refs.values():
            #         rec.check_geofence_status()

            if values and values.get('latest_latitude') and values.get(
                    'latest_longitude') and rec.status_id.do_eta_calculation:
                rec.update_eta_time()
            elif values and values.get('status_id') and rec.status_id.do_eta_calculation:
                rec.update_eta_time()
            else:
                if rec.eta and rec.eta_last_updated and rec.remaining_time and rec.remaining_distance and not rec.status_id.do_eta_calculation:
                    rec.write({
                        'eta': False,
                        'eta_last_updated': False,
                        'remaining_time': '',
                        'remaining_distance': '',
                    })

            if values and values.get('driver_id'):
                # NOTE: Shipment notification functionalities is shifted to send_shipment_notificaton(self, special_case= None)
                
                rec.send_shipment_notificaton(special_case= 'shipment_assigned', driver_id= values.get('driver_id'))

            # Change Made notification:
            # Previous coondition for change made
            # if values.get('stop_ids') or values.get('status_id') and not skip_change_mode and values.get('status_id') not in [
            #     self.env.ref('bista_driver_app.shipment_status_cancelled').id,
            #     self.env.ref('bista_driver_app.shipment_status_pending').id]:
            # T2650: Change Made notification
            
            # NOTE: Shipment notification functionalities is shifted to send_shipment_notificaton(self, special_case= None)
                        
            # shifted to _compute_notes_binary method
            # if values.get('notes'):
            #     generated_note_pdf, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf('bista_driver_app.action_report_shipment_instruction',self.id,data={'type':"notes"})
            #     values.update({'notes_binary': base64.b64encode(generated_note_pdf)}) #FIX: avoiding multiple write function call within the write function 
            # if payload_data:
            #     response = firebase_send_notification(self.with_context(is_use_fleet_firebase_configuration=True), payload_data)
            #     if response:
            #         _logger.info("Notification send.")
            # if self.status_id.id == self.env.ref('bista_driver_app.shipment_status_pending').id or self.status_id.id  == self.env.ref('bista_driver_app.shipment_status_assigned').id or self.status_id.id  == self.env.ref('bista_driver_app.shipment_status_cancelled').id or self.status_id.id  == self.env.ref('bista_driver_app.shipment_status_delivered').id:
            self.env['bus.bus']._sendone(f"map_refresh#{str(self.env.user.id)}", "render", {
                'message': "message",
            })

        res = super().write(values)
        return res

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
        d_phi = math.radians(float(lat2) - float(lat1))
        d_lambda = math.radians(float(lon2) - float(lon1))

        a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def is_point_inside_shape(self, shape_data_str, lat, lng):
        try:
            shape_data = json.loads(shape_data_str)
            point = Point(lng, lat)

            if shape_data['type'] == 'circle':
                center_lat = shape_data['center']['lat']
                center_lng = shape_data['center']['lng']
                radius_m = shape_data['radius']
                distance = self.haversine_distance(lat, lng, center_lat, center_lng)
                return distance <= radius_m

            elif shape_data['type'] == 'rectangle':
                sw = shape_data['bounds']['sw']
                ne = shape_data['bounds']['ne']
                min_lat = min(sw['lat'], ne['lat'])
                max_lat = max(sw['lat'], ne['lat'])
                min_lng = min(sw['lng'], ne['lng'])
                max_lng = max(sw['lng'], ne['lng'])
                return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng

            elif shape_data['type'] == 'polygon':
                path = shape_data.get('path', [])
                if len(path) < 3:
                    return False
                polygon = Polygon([(p['lng'], p['lat']) for p in path])
                return polygon.contains(point)

        except Exception as e:
            _logger.warning(f"Shape parse error: {e}")
        return False

    def check_geofence_status(self):
        status_refs = {
            'accepted': self.env.ref('bista_driver_app.shipment_status_accepted').id,
            'in_transit': self.env.ref('bista_driver_app.shipment_status_in_transit').id,
            'at_pickup': self.env.ref('bista_driver_app.shipment_status_at_pickup').id,
            'at_delivery': self.env.ref('bista_driver_app.shipment_status_at_delivery').id,
        }
        stop_status_refs = {
            'at_location': self.env.ref('bista_driver_app.stop_status_at_location').id,
            'departed': self.env.ref('bista_driver_app.stop_status_departed').id,
        }

        for shipment in self:
            lat = shipment.latest_latitude
            lng = shipment.latest_longitude
            status_id = shipment.status_id.id

            pickup = shipment.stop_ids.filtered(lambda s: s.location_type == 'pickup' and s.shape_data)
            delivery = shipment.stop_ids.filtered(lambda s: s.location_type == 'delivery' and s.shape_data)

            # Pickup Check
            if pickup and (status_id in [status_refs['accepted'], status_refs['at_pickup']]):
                inside_pickup = self.is_point_inside_shape(pickup.shape_data, lat, lng)
                if status_id == status_refs['accepted'] and inside_pickup:
                    pickup.with_context(is_from_geofencing=True).write({'stop_status_id': stop_status_refs['at_location']})
                    # pickup.stop_status_id = stop_status_refs['at_location']
                elif status_id == status_refs['at_pickup'] and not inside_pickup:
                    pickup.with_context(is_from_geofencing=True).write({'stop_status_id': stop_status_refs['departed']})
                    # pickup.stop_status_id = stop_status_refs['departed']

            # Delivery Check
            if delivery and (status_id in [status_refs['in_transit'], status_refs['at_delivery']]):
                inside_delivery = self.is_point_inside_shape(delivery.shape_data, lat, lng)
                if status_id == status_refs['in_transit'] and inside_delivery:
                    delivery.with_context(is_from_geofencing=True).write({'stop_status_id': stop_status_refs['at_location']})
                    # delivery.stop_status_id = stop_status_refs['at_location']
                elif status_id == status_refs['at_delivery'] and not inside_delivery:
                    delivery.with_context(is_from_geofencing=True).write({'stop_status_id': stop_status_refs['departed']})
                    # delivery.stop_status_id = stop_status_refs['departed']

    def get_map_api_key(self, key):
        return self.env['ir.config_parameter'].sudo().get_param(key)

    def update_eta_time(self):
        if self.stop_ids:
            delivery_id = self.stop_ids.filtered(lambda s: s.location_type == 'delivery')
            google_map_api_key = self.get_map_api_key('bista_driver_app.shipment_google_map_api_key')
            if delivery_id and self.latest_latitude and self.latest_longitude:
                # Prepare Google Maps API request
                params = {
                    "origin": f"{self.latest_latitude},{self.latest_longitude}",
                    "destination": f"{delivery_id.latitude},{delivery_id.longitude}",
                    "mode": "driving",
                    "key": google_map_api_key
                }
                try:
                    gmaps_url = "https://maps.googleapis.com/maps/api/directions/json"
                    gmaps_response = requests.get(gmaps_url, params=params, timeout=5)
                    gmaps_data = gmaps_response.json()
                    if gmaps_data["status"] == "OK":
                        distance_text = gmaps_data["routes"][0]["legs"][0]["distance"]["text"]
                        duration_text = gmaps_data["routes"][0]["legs"][0]["duration"]["text"]
                        # estimated_minutes = int(duration_text.split()[0])  # Extract integer minutes
                    else:
                        if self.env.context.get('from_mobile_app'):
                             _logger.error(f"Google Maps API Error: {gmaps_data}")
                             return
                        else:
                            raise ValidationError(f"Google Maps API Error: {gmaps_data}")

                    # Determine timezone from the last stop
                    target_timezone = pytz.timezone('UTC')
                    if delivery_id.timezone:
                        # target_timezone = pytz.timezone(delivery_id.timezone)
                        # NOTE: this line is updated to solve the issue: pytz.exceptions.UnknownTimeZoneError: 'CST'
                        target_timezone = safe_get_timezone(delivery_id.timezone)

                    # Extract hours and minutes using regex
                    match = re.findall(r'(\d+)\s*(hour|hours|mins|min)', duration_text)

                    # Initialize hours and minutes
                    hours = 0
                    minutes = 0

                    # Parse extracted values
                    for value, unit in match:
                        if "hour" in unit:
                            hours = int(value)
                        elif "min" in unit:
                            minutes = int(value)

                    # Compute estimated arrival time
                    current_time = datetime.now()
                    arrival_time = current_time + timedelta(hours=hours, minutes=minutes)

                    # # Apply a 4-minute buffer adjustment
                    # arrival_time_minus_minutes = arrival_time - timedelta(minutes=4)
                    # if arrival_time_minus_minutes < current_time:
                    #     new_arrival_time = current_time + timedelta(minutes=5)
                    # else:
                    #     new_arrival_time = arrival_time_minus_minutes

                    # Apply a 5-minute buffer adjustment
                    if arrival_time < current_time:
                        new_arrival_time = current_time + timedelta(minutes=5)
                    else:
                        new_arrival_time = arrival_time

                    # Convert to target timezone and remove timezone info for database storage
                    final_eta = new_arrival_time.astimezone(target_timezone)
                    final_eta_dt = final_eta.replace(tzinfo=None)
                    current_time_eta = current_time.astimezone(target_timezone)
                    current_time_eta_dt = current_time_eta.replace(tzinfo=None)

                    # Update the shipment record
                    self.write({
                        'eta': final_eta_dt,
                        'eta_last_updated': current_time_eta_dt,
                        'remaining_time': duration_text,
                        'remaining_distance': distance_text
                    })
                    _logger.info(f"Duration ->{duration_text} Distance -> {distance_text}")
                    _logger.info(f"Current time -> {current_time} Arrival time -> {arrival_time}")
                    _logger.info(f"ETA -> {final_eta_dt} ETA Last Updated -> {current_time_eta_dt}")

                except requests.RequestException as e:
                    if self.env.context.get('from_mobile_app'):
                        err = _serialize_exception(e)
                        error_msg = err.get('message',False)
                        if error_msg:
                            _logger.exception(error_msg)
                    else:
                        raise ValidationError(f"Error fetching ETA from Google Maps: {e}")

    ### Map Fetch Related Work ###
    # def get_lat_lon(self):
    #     for record in self:
    #         if not record.stop_ids:
    #             return {}
    #
    #         pickup = record.stop_ids.filtered(lambda s: s.location_type == 'pickup')
    #         delivery = record.stop_ids.filtered(lambda s: s.location_type == 'delivery')
    #
    #         if not (
    #                 pickup and pickup.latitude and pickup.longitude and delivery and delivery.latitude and delivery.longitude):
    #             return {}
    #
    #         is_display_waypoints = False
    #         is_display_routes_from_truck_to_destination = False
    #
    #         if record.status_id.name in ['Dispatched', 'At Pickup', 'In Transit', 'At Delivery']:
    #             is_display_waypoints = True
    #         if record.status_id.name in ['Dispatched', 'At Pickup']:
    #             is_display_routes_from_truck_to_destination = True
    #
    #         lat_long_data = {
    #             'origin': {
    #                 'lat': pickup.latitude,
    #                 'lng': pickup.longitude,
    #                 'location_name': record.stop_pickup,
    #                 'address': record.display_pickup_address,
    #                 'planned_pickup': self.get_local_formatted_datetime(record.planned_pickup,
    #                                                                     user_tz='UTC') if record.planned_pickup else '',
    #                 'actual_pickup': self.get_local_formatted_datetime(record.actual_pickup,
    #                                                                    user_tz='UTC') if record.actual_pickup else '',
    #                 'timezone': record.pickup_timezone or '',
    #                 'shape_data': pickup.shape_data or ''
    #             },
    #             'destination': {
    #                 'lat': delivery.latitude,
    #                 'lng': delivery.longitude,
    #                 'location_name': record.stop_delivery,
    #                 'address': record.display_delivery_address,
    #                 'planned_delivery': self.get_local_formatted_datetime(record.planned_delivery,
    #                                                                       user_tz='UTC') if record.planned_delivery else '',
    #                 'actual_delivery': self.get_local_formatted_datetime(record.actual_delivery,
    #                                                                      user_tz='UTC') if record.actual_delivery else '',
    #                 'timezone': record.delivery_timezone or '',
    #                 'shape_data': delivery.shape_data or ''
    #             },
    #             'stage': record.status_id.do_eta_calculation,
    #             'stage_name': record.status_id.name,
    #             'is_display_waypoints': is_display_waypoints,
    #             'is_display_routes_from_truck_to_destination': is_display_routes_from_truck_to_destination,
    #         }
    #
    #
    #         history_data = []
    #         eld_source_id =  self.env.ref('bista_driver_app.samsara_gps_tracker')
    #
    #         for history in record.geolocation_history_ids:
    #             date_recorded = self.get_local_formatted_datetime(history.date_recorded, user_tz=self.env.user.tz)
    #             full_timestamp = f"{date_recorded} {history.timezone}" if history.timezone else date_recorded
    #             # device_type = 'eld' if history.source_name == 'ELD' else 'mobile'
    #             device_type = 'mobile'
    #
    #             eld_waypoint = False
    #             if history.latest and record.status_id.name not in ['Pending', 'Assigned', 'Delivered', 'Cancelled']:
    #                 # Check if it's ELD source
    #                 if history.source_id.id == eld_source_id.id:
    #                     eld_waypoint = True
    #
    #                 lat_long_data['waypoints'] = {
    #                     'lat': history.asset_latitude,
    #                     'lng': history.asset_longitude,
    #                     'date_recorded': full_timestamp,
    #                     'device_type': device_type,
    #                     'connectivity_status': dict(history._fields['connectivity_status'].selection).get(
    #                         history.connectivity_status),
    #                     'driver_name': history.carrier_id.driver_name,
    #                     'source': history.source_name,
    #                     'carrier_name': history.carrier_id.carrier_id.name,
    #                     'truck_number': history.carrier_id.truck_no,
    #                     'eld_waypoint': eld_waypoint
    #                 }
    #             else:
    #                 history_data.append({
    #                     'lat': history.asset_latitude,
    #                     'lng': history.asset_longitude,
    #                     'date_recorded': full_timestamp,
    #                     'device_type': device_type,
    #                     'connectivity_status': dict(history._fields['connectivity_status'].selection).get(
    #                         history.connectivity_status),
    #                     'driver_name': history.carrier_id.driver_name,
    #                     'source': history.source_name,
    #                     'carrier_name': history.carrier_id.carrier_id.name,
    #                     'truck_number': history.carrier_id.truck_no
    #                 })
    #
    #         if history_data:
    #             lat_long_data['geolocation_history'] = history_data
    #         return lat_long_data
    #
    #     return {}

    def get_local_formatted_datetime(self, dt_utc, user_tz=None):
        """Convert UTC datetime to user timezone and format like '06/11/2025 02:53:44 PM'"""
        if not dt_utc:
            return ''
        if user_tz is None:
            user_tz = self.env.user.tz
            if not user_tz:
                user_tz = 'UTC'
        user_tz = timezone(user_tz)
        dt_local = UTC.localize(dt_utc).astimezone(user_tz)
        return dt_local.strftime('%m/%d/%Y %I:%M:%S %p')

    @api.depends(
        'stop_ids.street_1', 'stop_ids.street_2', 'stop_ids.city', 'stop_ids.county_id',
        'stop_ids.state_id', 'stop_ids.zip', 'stop_ids.country_id',
    )
    def _compute_display_pickup_address(self):
        for rec in self:
            pickup_id = rec.stop_ids.filtered(lambda s: s.location_type == 'pickup')
            if pickup_id:
                pickup_id = pickup_id[0]
                parts = filter(None, [
                    pickup_id.street_1,
                    pickup_id.street_2,
                    pickup_id.city,
                    pickup_id.county_id.name if pickup_id.county_id else None,
                    pickup_id.state_id.name if pickup_id.state_id else None,
                    pickup_id.zip,
                    pickup_id.country_id.name if pickup_id.country_id else None,
                ])
                rec.display_pickup_address = ', '.join(parts)
            else:
                rec.display_pickup_address = ''

    @api.depends(
        'stop_ids.street_1', 'stop_ids.street_2', 'stop_ids.city', 'stop_ids.county_id',
        'stop_ids.state_id', 'stop_ids.zip', 'stop_ids.country_id',
    )
    def _compute_display_delivery_address(self):
        for rec in self:
            delivery_id = rec.stop_ids.filtered(lambda s: s.location_type == 'delivery')
            if delivery_id:
                delivery_id = delivery_id[0]
                parts = filter(None, [
                    delivery_id.street_1,
                    delivery_id.street_2,
                    delivery_id.city,
                    delivery_id.county_id.name if delivery_id.county_id else None,
                    delivery_id.state_id.name if delivery_id.state_id else None,
                    delivery_id.zip,
                    delivery_id.country_id.name if delivery_id.country_id else None,
                ])
                rec.display_delivery_address = ', '.join(parts)
            else:
                rec.display_delivery_address = ''

    def action_view_remaining_milage(self):
        return True

    def action_open_shipment_record(self):
        action = self.env.ref('bista_driver_app.action_all_shipments').sudo().read()[0]
        action['views'] = [(self.env.ref('bista_driver_app.shipment_form_view').sudo().id, 'form')]
        action['res_id'] = self.sudo().id
        return action

    def action_open_location(self):
        # Check if there is a location
        if self.env.context and self.env.context.get('delivery_location') or self.env.context.get('pickup_location'):
            if self.env.context.get('delivery_location'):
                stop_id = self.stop_ids.filtered(lambda s: s.location_type == 'delivery')
            if self.env.context.get('pickup_location'):
                stop_id = self.stop_ids.filtered(lambda s: s.location_type == 'pickup')
        if not stop_id:
            return False

        action = self.env.ref('bista_driver_app.action_shipment_stop').sudo().read()[0]
        action['views'] = [(self.env.ref('bista_driver_app.view_shipment_stop_form').id, 'form')]
        action['target'] = 'new'
        action['res_id'] = stop_id.id
        return action

    def update_stop_sequences(self):
        for shipment in self:
            stops = shipment.stop_ids.sorted('id')
            pickup_stop = stops.filtered(lambda s: s.location_type == 'pickup')
            delivery_stop = stops.filtered(lambda s: s.location_type == 'delivery')
            middle_stops = stops.filtered(lambda s: s.location_type == 'empty')

            sequence = 1

            # Pickup Stop
            if pickup_stop:
                pickup_stop.sequence = sequence
                sequence += 1

            # Intermediate Stops
            for stop in middle_stops:
                stop.sequence = sequence
                sequence += 1

            # Delivery Stop
            if delivery_stop:
                delivery_stop.sequence = sequence

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        """
            In the geolocation history map view show only the latest records, if history records of multiple
            serial number/asset tracker exists
        """
        if self.env.context.get('view_mode') == 'pass_delivered_shipments':
            domain += [('status_id', '=', self.env.ref('bista_driver_app.shipment_status_in_transit').id)]
        res = super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                      count_limit=count_limit)
        return res


    def web_save(self, vals, specification: Dict[str, Dict], next_id=None) -> List[Dict]:
        if self and 'skip_change_mode' not in self.env.context:
            self = self.with_context(skip_change_mode=False,from_shipment=True)
            if 'status_id' not in vals:
                vals.update({'status_id':self.status_id.id})

        return super(Shipments,self).web_save(vals, specification, next_id=next_id)

    # def cron_send_location_not_detected_sms(self):
    #     shipments_ids = self.env['shipment.shipment'].sudo().search([('tracking_status', '!=', 'paused'), ('location_tracking', '=', 'enabled')])
    #     shipments_ids = shipments_ids.filtered(lambda s: s.geolocation_history_ids)
    #
    #     now_utc = datetime.utcnow()
    #     sms_template = self.env.ref('bista_driver_app.driver_app_location_not_detected_sms_template')
    #     shipment_setting = self.env.ref('bista_driver_app.shipment_settings_location_timeout_threshold')
    #     minutes_config = shipment_setting.value if shipment_setting else 30
    #     twilio_account_id = self.env['twilio.account'].sudo().search([('state', '=', 'confirm')], limit=1)
    #
    #     if twilio_account_id:
    #         for shipment in shipments_ids:
    #             # T2851: SMS frequency for location timeout
    #             timeout_freq = self.env.ref('bista_driver_app.shipment_settings_location_time_out_sms_frequency')
    #             if timeout_freq.value < shipment.twilio_sms_count:
    #                 shipment.twilio_sms_count = timeout_freq.value
    #             if shipment.driver_id and shipment.twilio_sms_count < timeout_freq.value:
    #                 latest_geo_history = shipment.geolocation_history_ids.sorted('create_date', reverse=True)[0]
    #                 create_date_utc = latest_geo_history.create_date
    #
    #                 time_diff = now_utc - create_date_utc
    #                 if time_diff >= timedelta(minutes=minutes_config):
    #                     # Get Latest 'Location Not Detected' SMS and check the time difference
    #                     last_sms_id = self.env['twilio.sms'].sudo().search([('shipment_id', '=', shipment.id), ('template_body_id', '=', sms_template.id)], order='create_date desc', limit=1)
    #                     last_sms_time = last_sms_id.create_date if last_sms_id else False
    #                     is_send_sms = False
    #
    #                     if not last_sms_time:
    #                         is_send_sms = True
    #                     else:
    #                         sms_time_diff = now_utc - last_sms_time
    #                         if sms_time_diff >= timedelta(minutes=minutes_config):
    #                             is_send_sms = True
    #
    #                     # Send SMS
    #                     if is_send_sms:
    #                         partner = shipment.driver_id.user_id.partner_id
    #                         if twilio_account_id and shipment.driver_id.is_valid_phone and not shipment.driver_id.is_skip_sms:
    #                             # T2726: server environment add to sms template
    #                             base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #                             current_env = False
    #                             if "driver" in base_url:
    #                                 current_env = ""
    #                             elif "360staging" in base_url:
    #                                 current_env = '(Staging)'
    #                             elif "driverdev" in base_url:
    #                                 current_env = '(Dev)'
    #                             else:
    #                                 current_env = '(Local)'
    #                             sms_id = self.env['twilio.sms'].sudo().create({
    #                                 'name': 'Location Not Detected',
    #                                 'account_id': twilio_account_id.id,
    #                                 'receiver_partner_id': partner.id,
    #                                 'content': sms_template.content % (shipment.name,current_env) if shipment.driver_id.user_id.fleet_lang == 'en_US' else sms_template.content_es % (shipment.name,current_env),
    #                                 'template_body_id': sms_template.id,
    #                                 'single_receiver': True,
    #                                 'shipment_id': shipment.id,
    #                             })
    #                             response = sms_id.action_confirm_sms()
    #                             # T2851: SMS frequency for location timeout
    #                             shipment.twilio_sms_count += 1
    #                             # SMS response stored
    #                             if response.get('params') and response.get('params').get('message'):
    #                                 sms_id.response = response.get('params').get('message')
    #                             logging.info('%s - Location Not Detected SMS Response: %s | SMS Count: %s', shipment, response,shipment.twilio_sms_count)


    # Set status to 'Pending' and driver to False.
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default['status_id'] = self.env.ref('bista_driver_app.shipment_status_pending').id
        default['driver_id'] = False
        return super(Shipments, self).copy(default=default)


    test_counter = fields.Integer(string="Counter", default= 0) # NOTE: this field is used in following test schedule action function

    def cron_update_shipment_tracking_status(self):
        """
            T2663: Scheduled action to update the tracking status of shipments where location tracking is disabled.
        """
        disabled_shipment_ids = self.sudo().search([('location_tracking', '=', 'disabled')])
        if disabled_shipment_ids:
            for shipment_id in disabled_shipment_ids:
                shipment_id.tracking_status =False


    ### Call FRom ELD Related Code ###
    # def fetch_vehicle_history_data(self, start_time, end_time, asset_id):
    #     auth_token = self.env.ref('bista_driver_app.terratech_eld_integration')
    #     if not auth_token:
    #         raise ValidationError('There is no auth token defined.')
    #     headers = {
    #         'Authorization': f'Bearer {auth_token.token}'
    #     }
    #     url = "https://api.samsara.com/fleet/vehicles/stats/history"
    #
    #     if start_time.tzinfo is None:
    #         start_time = start_time.replace(tzinfo=pytz.utc)
    #
    #     if end_time.tzinfo is None:
    #         end_time = end_time.replace(tzinfo=pytz.utc)
    #
    #     start_time = start_time.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    #     end_time = end_time.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    #
    #     _logger.info(f"Calling History Stats API for asset: {asset_id} from: {start_time} to: {end_time}")
    #
    #     params = {
    #         "startTime": start_time,
    #         "endTime": end_time,
    #         "vehicleIds": asset_id,
    #         "types": "gps",
    #     }
    #     try:
    #         response = requests.get(url, params=params, headers=headers)
    #         response.raise_for_status()  # Raise exception for HTTP errors (4xx or 5xx)
    #         return response.json()
    #     except requests.exceptions.RequestException as e:
    #         _logger.warning(f"Error making request for location of asset-{asset_id} : {e}")

### ELD CODE Server Action ###
    # def action_update_eld_location_history(self):
    #     """
    #         Server Action: Update ELD Location History
    #         NOTE: This server action is to fix SH000106.
    #         Using Stats snapshot API to create geolocation history of ELD in shipments.
    #         For this shipment this API returns same lat/long value for multiple history recrods. As a result the tracking map shows no middle route data.
    #         So replacing the location history values with stats history API data which returns all lat/long correctly.
    #     """
    #
    #     for shipment_id in self:
    #         eld_location_history_ids = shipment_id.geolocation_history_ids.filtered(lambda l: l.source_id == self.env.ref('bista_driver_app.samsara_gps_tracker')).sorted('date_recorded')
    #
    #         if eld_location_history_ids:
    #             end_time = self.env['geolocation.history'].sudo().browse(eld_location_history_ids.ids[0]).date_recorded
    #             start_points = shipment_id.timeline_ids.filtered(lambda l: l.name == "Mobile Tracking status changed to Active" and l.datetime < end_time).sorted('datetime')
    #             if start_points:
    #                 start_time = self.env['shipment.timeline'].sudo().browse(start_points.ids[-1]).datetime
    #                 shipment_id.update_location_history(start_time, end_time)
    #             else:
    #                 _logger.info("No end time found")
    #
    #         # NOTE: fillup middle gaps
    #         if len(eld_location_history_ids.ids) > 1:
    #             start_time = eld_location_history_ids[0].date_recorded
    #
    #             for history_id in eld_location_history_ids[1:]:
    #                 end_time = history_id.date_recorded
    #
    #                 shipment_id.update_location_history(start_time, end_time)
    #                 start_time = history_id.date_recorded
    #         else:
    #             _logger.info("Not enoungh value")
    #
    #         if shipment_id.location_tracking == 'enabled':
    #             _logger.info(f"location_tracking is enabled")
    #
    #             eld_location_history_ids = shipment_id.geolocation_history_ids.filtered(lambda l: l.source_id == self.env.ref('bista_driver_app.samsara_gps_tracker')).sorted('date_recorded')
    #             if eld_location_history_ids:
    #                 start_time = self.env['geolocation.history'].sudo().browse(eld_location_history_ids.ids[-1]).date_recorded
    #                 end_time = fields.Datetime.now()
    #                 shipment_id.update_location_history(start_time, end_time)
    #             else:
    #                 _logger.info("No ELD history record found")
    #
    #         elif shipment_id.location_tracking == 'disabled':
    #             _logger.info(f"location_tracking is disabled")
    #
    #             eld_location_history_ids = shipment_id.geolocation_history_ids.filtered(lambda l: l.source_id == self.env.ref('bista_driver_app.samsara_gps_tracker')).sorted('date_recorded')
    #             if eld_location_history_ids:
    #                 start_time = self.env['geolocation.history'].sudo().browse(eld_location_history_ids.ids[-1]).date_recorded
    #                 endpoints = shipment_id.timeline_ids.filtered(lambda l: l.name == "Mobile Tracking status changed to None" and l.datetime > start_time).sorted('datetime')
    #
    #                 if endpoints:
    #                     end_time = self.env['shipment.timeline'].sudo().browse(endpoints.ids[0]).datetime
    #                     shipment_id.update_location_history(start_time, end_time)
    #                 else:
    #                     _logger.info("No end time found")
    #             else:
    #                 _logger.info("No ELD history record found")
    #
    # def update_location_history(self, start_time, end_time):
    #     eld_frequency = self.env.ref("bista_driver_app.shipment_settings_location_reporting_frequency").value
    #     if (end_time - start_time).total_seconds() / 60 > eld_frequency+1:
    #         date_recorded_list = self.geolocation_history_ids.filtered(lambda l: l.source_id == self.env.ref('bista_driver_app.samsara_gps_tracker')).mapped('date_recorded')
    #         samsara_eld_asset_id = self.samsara_eld_asset_id
    #
    #         response = self.fetch_vehicle_history_data(start_time, end_time, self.samsara_eld_asset_id.eld_asset_id)
    #         create_time = start_time + timedelta(minutes=eld_frequency)
    #
    #         if response and response.get('data') and response.get('data')[0].get('gps'):
    #             _logger.info("Data Found")
    #             # _logger.info(f"response: {response}")
    #             gps = response.get('data')[0].get('gps')
    #
    #             for history_data in gps:
    #                 date_string = history_data.get('time')
    #                 date_recorded = datetime.fromisoformat(date_string.replace('Z', '+00:00')).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #                 dt = fields.Datetime.from_string(date_recorded)
    #                 if dt >= create_time:
    #                     if dt not in date_recorded_list:
    #                         new_his_id = self.create_geolocation_history(history_data, date_recorded, samsara_eld_asset_id, create_time)
    #                         _logger.info(f"==>Created geolocation history {new_his_id.id}")
    #                     else:
    #                         _logger.info(f"==>skipped Creating geolocation history as date_recorded value already exists")
    #                     create_time = dt + timedelta(minutes=eld_frequency)
    #             self.update_latest()
    #         else:
    #             _logger.info("No Data Found")
    #
    # def update_latest(self):
    #     prev_latest_history_id = self.geolocation_history_ids.filtered(lambda l: l.latest == True)
    #     if prev_latest_history_id:
    #         prev_latest_history_id.latest  = False
    #     geolocation_history_ids = self.geolocation_history_ids.sorted('date_recorded')
    #     self.env['geolocation.history'].sudo().browse(geolocation_history_ids.ids[-1]).latest = True
    #
    # def create_geolocation_history(self, gps, date_recorded, samsara_eld_asset_id, create_time):
    #     geolocation_history_create_data= {
    #         'source_id': self.env.ref('bista_driver_app.samsara_gps_tracker').id,
    #         'asset_latitude': gps.get('latitude'),
    #         'asset_longitude': gps.get('longitude'),
    #         'speed':  gps.get('speedMilesPerHour')*1.46667 if gps.get('speedMilesPerHour') else 0.0,
    #         'date_recorded': date_recorded,
    #         'samsara_eld_asset_id': samsara_eld_asset_id.id,
    #         'device_unique_id': samsara_eld_asset_id.serial_number,
    #         'connectivity_status': 'online',
    #         'device_info': {
    #             'eld_name':samsara_eld_asset_id.name,
    #         },
    #         'reference': f'shipment.shipment,{self.id}',
    #         'shipment_id': self.id,
    #         'company_id': self.customer_id.id if self.customer_id else False,
    #         'carrier_id': self.driver_id.id if self.driver_id else False,
    #     }
    #     _logger.info(f'geolocation history create data: {geolocation_history_create_data}')
    #     history_id = self.env['geolocation.history'].sudo().create(geolocation_history_create_data)
    #     return history_id

    # T2785:schedule action to update notes and directions into binary format
    def _update_shipment_and_stops_notes_directions(self):
        cancel_status = self.env.ref('bista_driver_app.shipment_status_cancelled').id
        shipment_ids = self.sudo().search([('notes',"!=",False),('status_id','!=',cancel_status)])
        stop_ids = self.env['shipment.stop'].sudo().search([])
        for rec in shipment_ids:
            generated_note_pdf, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'bista_driver_app.action_report_shipment_instruction', rec.id, data={'type': 'notes'})
            rec.notes_binary = base64.b64encode(generated_note_pdf)
        for rec in stop_ids:
            if rec.notes and not rec.notes_binary:
                generated_note_pdf, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                    'bista_driver_app.action_report_shipment_stop_instruction', rec.id,data={'type': 'notes'})
                rec.notes_binary = base64.b64encode(generated_note_pdf)
            if rec.directions and not rec.directions_binary:
                generated_note_pdf, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                    'bista_driver_app.action_report_shipment_stop_instruction', rec.id,data={'type': 'directions'})
                rec.directions_binary = base64.b64encode(generated_note_pdf)

        # TODO: create geolocation_history with sql query to update create_date field
        # query = """
        #     INSERT INTO geolocation_history 
        #     (source_id, asset_latitude, asset_longitude, speed, date_recorded, samsara_eld_asset_id, 
        #     device_unique_id, connectivity_status, device_info, reference, shipment_id) 
        #     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        # """

        # params = (
        #     self.env.ref('bista_driver_app.samsara_gps_tracker').id,
        #     gps.get('latitude'),
        #     gps.get('longitude'),
        #     gps.get('speedMilesPerHour')*1.46667 if gps.get('speedMilesPerHour') else 0.0,
        #     date_recorded,
        #     samsara_eld_asset_id.id,
        #     samsara_eld_asset_id.serial_number,
        #     'online',
        #     {
        #         'eld_name':samsara_eld_asset_id.name, 
        #     },
        #     f'shipment.shipment,{self.id}',
        #     self.id,
        # )
        # self.env.cr.execute(query, params)
