# -*- coding: utf-8 -*-
import logging
import json
from odoo import http
from odoo.exceptions import AccessDenied, AccessError, ValidationError
from odoo.http import request, content_disposition, serialize_exception as _serialize_exception
from odoo.addons.bista_driver_app.common import invalid_response, valid_response, convert_data_str
from odoo.addons.web.controllers.binary import Binary
import datetime
from pytz import timezone
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.addons.bista_driver_app.controllers.fleet_api import BistaFleetApi
# from odoo.addons.bista_driver_app.controllers.fleet_api import validate_fleet_token
from odoo.addons.bista_mobile_base.common import validate_token


_logger = logging.getLogger(__name__)

status_color_codes = ['a2a2a2','ee2d2d','dc8534','e8bb1d','5794dd','9f628f','db8865',
                                                '41a9a2', '304be0', 'ee2f8a', '61c36e', '9872e6']

# # TODO:make global variable for from_fleet_v2
# Fleetv2 = {'from_fleet_v2': True}

class BistaFleetApiV2(BistaFleetApi):

    #######################################
    # GET APIs
    #######################################

    # @staticmethod
    def update_context(self):
        context = request.env.context.copy()
        context.update({'from_fleet_v2': True})
        request.env.context = context

    # @staticmethod
    def filter_by_last_sync_time(self,payload_data, domain):
        last_sync_timestamp = payload_data.get('last_sync_timestamp') if payload_data.get('last_sync_timestamp') else False
        if last_sync_timestamp:
            sync_datetime = datetime.datetime.fromtimestamp(int(last_sync_timestamp)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            domain += ['|', ("create_date", ">=", sync_datetime), ("write_date", ">=", sync_datetime)]

    @staticmethod
    def sort_shipment_list(data):
        """
            Sort the shipment order in Fleet app list view. Sorting rules:
            Active shipments ['Dispatched', 'At Pickup', 'In Transit', 'At Delivery'] come first.
            'Assigned' shipments are next — sorted by how close their planned_pickup time is to the current time (smaller time difference first).
            'Delivered' shipments come next — sorted by most recent actual_delivery
            'Cancelled'  shipments follow — sorted by most recent create_date.
        """
        priority_order = [3, 4, 5, 6]
        date = data.get('create_date',False)
        if date:
            print(data)
            date = datetime.datetime.strptime(date, "%m/%d/%Y %I:%M %p")
        now = datetime.datetime.now()
        if data:
            status_sequence = data.get('status_sequence',False)
            if status_sequence and status_sequence in priority_order:
                return 1, priority_order.index(status_sequence), None
            elif status_sequence and status_sequence == 2:
                # return 2, data['create_date']
                planned_pickup = datetime.datetime.strptime(data.get('planned_pickup'), "%m/%d/%Y %I:%M %p")
                return 2, abs((planned_pickup - now).total_seconds())
            elif status_sequence and status_sequence == 1:
                return 3, data.get('create_date')
            elif status_sequence and status_sequence == 7:
                if data.get('actual_delivery'):
                    actual_delivery = datetime.datetime.strptime(data.get('actual_delivery'), "%m/%d/%Y %I:%M %p")
                    return 4, -actual_delivery.timestamp()
                else:
                    return 4, -date.timestamp()
            elif status_sequence and status_sequence == 8:
                return 5, -date.timestamp()
            else:
                return 6, None
        else:
            return 6, None

    @validate_token
    @http.route(["/api/v2/fleet/get_shipment_details_list","/api/v1/fleet/get_shipment_details_list"], methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_details_list(self, **payload):
        _logger.info("/api/v2/fleet/get_shipment_details_list: %s", payload)
        try:
            payload_data = payload
            processed_list = []
            shipment_id = payload_data.get('shipment_id') if payload_data.get('shipment_id') else False
            last_sync_timestamp = payload_data.get('last_sync_timestamp') if payload_data.get(
                'last_sync_timestamp') else False
            field_list = ['id','name','status_id','driver_id','stop_ids','document_ids','sale_order_no','customer_id',
                          'create_date','item_ids','notes','tracking_status', 'pickup_id', 'delivery_id',
                          'planned_pickup', 'planned_delivery', 'actual_delivery','pickup_timezone','delivery_timezone',
                          ]
            # 'samsara_eld_asset_id','call_out_id',

            #domain prepare
            current_driver_id = self._get_current_driver_id()
            domain = [('driver_id','=',current_driver_id)]
            if shipment_id:
                domain += [('id','=', int(shipment_id))]
            self.filter_by_last_sync_time(payload_data,domain)
            self.update_context()

            response_data = self._get_shipment_detail_data(domain,field_list)
            if last_sync_timestamp:
                current_driver_id = self._get_current_driver_id()
                domain = [('driver_id', '!=', current_driver_id)]
                if shipment_id:
                    domain += [('id', '=', int(shipment_id))]
                self.filter_by_last_sync_time(payload_data, domain)
                self.update_context()
                revoked_response_data = self._get_shipment_detail_data(domain, ['id'])
                if isinstance(revoked_response_data,list) and len(revoked_response_data) > 0:
                    processed_list = [{'id': rec['id'], 'revoked': True} for rec in revoked_response_data]
            if isinstance(response_data, list) and len(response_data) > 0 and isinstance(processed_list,list) and len(processed_list) > 0:
                response_data = response_data + processed_list
                response_data = sorted(response_data, key=self.sort_shipment_list)
                return valid_response(response_data)
            elif isinstance(processed_list,list) and len(processed_list) > 0:
                processed_list = sorted(processed_list, key=self.sort_shipment_list)
                return valid_response(processed_list)
            elif isinstance(response_data, list) and len(response_data) > 0:
                response_data = sorted(response_data, key=self.sort_shipment_list)
                return valid_response(response_data)
            else :
                return invalid_response(response_data['response'], response_data['message'], response_data.get('status') or 204)
        except Exception as e:
            _logger.exception("Error while getting Shipment Detail data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting Shipment Detail data.'
            return invalid_response('bad_request', error_msg, 200)


    @validate_token
    @http.route(["/api/v2/fleet/get_stop_details_list","/api/v1/fleet/get_stop_details_list"], methods=["GET"], type="http", auth="none", csrf=False)
    def get_stop_details_list(self, **payload):
        _logger.info("/api/v2/fleet/get_stop_details_list: %s", payload)
        try:
            payload_data = payload
            shipment_stop = request.env['shipment.stop'].sudo()
            stop_ids = list(map(int, payload_data['stop_ids'].split("-"))) if payload_data.get('stop_ids') else False
            shipment_id = payload_data.get('shipment_id') if payload_data.get('shipment_id') else False
            field_list = ['id', 'shipment_id', 'name', 'location_type', 'location_name','planned_arrival','formatted_address', 'contact_name', 'contact_phone', 'sequence',
                          'directions', 'notes', 'latitude', 'longitude']

            #domain prepare
            current_driver_id = self._get_current_driver_id()
            domain = [('shipment_id.driver_id','=',current_driver_id)]
            if stop_ids:
                domain +=[('id','in', stop_ids)]
            if shipment_id:
                domain += [('shipment_id', '=', int(shipment_id))]
            self.filter_by_last_sync_time(payload_data,domain)
            self.update_context()

            stop_data = shipment_stop.search_read(domain, field_list)
            response_data = self._prepare_response_data(shipment_stop, field_list, stop_data)
            for rec in response_data:
                rec['name'] = rec.pop('location_name')
            if len(response_data) > 0:
                return valid_response(response_data)
            else :
                return invalid_response('not_found', 'No record found with the given id',  204)
        except Exception as e:
            _logger.exception("Error while getting Stop Detail data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting Stop Detail data.'
            return invalid_response('bad_request', error_msg, 200)


    @validate_token
    @http.route(["/api/v2/fleet/get_shipment_status_lists","/api/v1/fleet/get_shipment_status_lists"], methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_status_lists(self, **payload):
        _logger.info("/api/v2/fleet/get_shipment_status_lists: %s", payload)

        try:
            payload_data = payload
            status_ids = list(map(int, payload_data['status_ids'].split("-"))) if payload_data.get('status_ids') else False
            app_language = request.httprequest.headers.get('lang')
            # domain = [('is_driver_can_choose','=', True)]
            domain = []
            field_list = ["id", "name", "name_es", "is_driver_can_choose", "location_tracking",
                          "status_action", "is_completed", "is_cancelled", "button_name_en",
                          "button_name_es",'color', 'sequence']

            if status_ids:
                domain +=[('id','in', status_ids)]
            self.filter_by_last_sync_time(payload_data, domain)
            self.update_context()

            response_data = self._get_shipment_status_list_data(domain, field_list, app_language)
            if isinstance(response_data, list) and len(response_data) > 0:
                for rec in response_data:
                    rec.update({
                        "button_hide": True if rec.get('id') == request.env.ref(
                            'bista_driver_app.shipment_status_pending').id else False,
                        "status_color_code": status_color_codes[rec.pop('color')] if rec.get('color') else 'a2a2a2'
                    })

            if isinstance(response_data, list):
                return valid_response(response_data)
            else:
                return invalid_response(response_data['response'], response_data['message'],response_data['status'])
        except Exception as e:
            _logger.exception("Error while getting Shipment Status data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting Shipment Status data.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route(["/api/v2/fleet/get_shipment_document_detail_list","/api/v1/fleet/get_shipment_document_detail_list"], methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_document_detail_list(self, **payload):
        _logger.info("/api/v2/fleet/get_shipment_document_detail_list: %s", payload)
        try:
            payload_data = payload
            document_ids = list(map(int, payload_data['document_ids'].split("-"))) if payload_data.get('document_ids') else False
            shipment_id = payload_data.get('shipment_id') if payload_data.get('shipment_id') else False
            field_list = ['id','filename', 'shipment_id', 'document_type_id', 'description','date', 'write_date','is_signature', 'signed_by']

            #domain prepare
            current_driver_id = self._get_current_driver_id()
            domain = [('shipment_id.driver_id','=',current_driver_id)]
            if document_ids:
                domain += [('id', 'in', document_ids)]
            if shipment_id:
                domain += [('shipment_id', '=', int(shipment_id))]
            self.filter_by_last_sync_time(payload_data, domain)
            self.update_context()

            response_data = self._get_shipment_document_detail_data(domain, field_list)
            if isinstance(response_data, list):
                # T2858 to show document last updated time (write_date) is added in the response
                # For avoiding instant update in fleet app 'date' key is kept same in the response for the time being 
                # but updated with the 'write_date'. Later should be updated in the app with 'write_date' key.
                for data in response_data:
                    data['date'] = data.get('write_date')
                return valid_response(response_data)
            else:
                return invalid_response(response_data['response'], response_data['message'], 204)
        except Exception as e:
            _logger.exception("Error while getting Shipment Document Detail data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting Shipment Document Detail data.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route(["/api/v2/fleet/get_document_type_lists","/api/v1/fleet/get_document_type_lists"], methods=["GET"], type="http", auth="none", csrf=False)
    def get_document_type_lists(self, **payload):
        _logger.info("/api/v2/fleet/get_document_type_lists: %s", payload)
        try:
            payload_data = payload
            document_type_ids = list(map(int, payload_data['type_ids'].split("-"))) if payload_data.get('type_ids') else False
            domain = []
            field_list = ['id', 'type_name', 'is_default_shipment_document']

            if document_type_ids:
                domain +=[('id','in', document_type_ids)]
            self.filter_by_last_sync_time(payload_data, domain)
            self.update_context()

            response_data = self._get_document_type_list_data(domain, field_list)
            if isinstance(response_data, list):
                return valid_response(response_data)
            else :
                return invalid_response(response_data['response'], response_data['message'], response_data.get('status') or 204)
        except Exception as e:
            _logger.exception("Error while getting Document Type data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting Document Type data.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route(["/api/v2/fleet/get_file_url_list","/api/v1/fleet/get_file_url_list"], methods=["GET"], type="http", auth="none", csrf=False)
    def get_file_url_list(self, **payload):
        _logger.info("/api/v2/fleet/get_file_url_list: %s", payload)
        try:
            payload_data = payload
            record_ids = list(map(int, payload_data['id'].split("-"))) if payload_data.get('id') else False
            record_obj = False
            field_list = []
            response_data = []
            types_refs ={
                'shipment_note':'shipment.shipment',
                'shipment_stop_note':'shipment.stop',
                'shipment_stop_direction': 'shipment.stop',
                'shipment_direction': 'shipment.shipment',
                'shipment_document': 'shipment.document',
                'shipment_document_sign': 'shipment.document',
            }
            current_driver_id = self._get_current_driver_id()
            domain = [('driver_id', '=', current_driver_id)]
            if payload_data.get('type'):
                field_name = False
                if payload_data['type'].endswith("note"):
                    field_list = ['id', 'notes','notes_binary']
                    field_name = 'notes_binary'
                elif payload_data['type'].endswith("direction"):
                    field_list = ['id', 'directions','directions_binary']
                    field_name = 'directions_binary'
                if 'stop' in payload_data['type']:
                    field_list += ['shipment_id']
                    domain = [('shipment_id','!=',False),('shipment_id.driver_id', '=', current_driver_id)]
                if payload_data['type'] == 'shipment_document':
                    field_list += ['id', 'shipment_id', 'filename']
                    field_name = 'file'
                    domain = [('shipment_id.driver_id', '=', current_driver_id)]
                if payload_data['type'] == 'shipment_document_sign':
                    field_list += ['id', 'shipment_id', 'signed_by']
                    field_name = 'document_signature'
                    domain = [('shipment_id.driver_id', '=', current_driver_id)]

                if record_ids:
                    domain += [('id', 'in', record_ids)]
                self.filter_by_last_sync_time(payload_data, domain)
                record_obj = request.env[types_refs.get(payload_data['type'])].sudo().search_read(domain,field_list)
                for rec in record_obj:
                    if rec.get('filename') or rec.get('notes_binary') or rec.get('directions_binary') or rec.get('signed_by'):
                        file_name = rec.get('filename', False)
                        if not file_name:
                            file_name = f"{payload_data['type']}_{rec['id']}.pdf"
                        response_dict = {
                            'id': rec['id'],
                            'type': payload_data['type'],
                            'file_name':file_name,
                            'url': f"?model={types_refs.get(payload_data['type'])}&download=true&field={field_name}&filename={file_name}&id={rec['id']}",
                            'shipment_id': rec['shipment_id'][0] if rec.get('shipment_id') else False,
                        }
                        if rec.get('signed_by'):
                            #for document signature data signature related data are updated in the response
                            response_dict.update({'signed_by': rec.get('signed_by'),
                                                  'file_name':f"{payload_data['type']}_{rec['id']}.png",})
                        response_data.append(response_dict)
            else:
                self.filter_by_last_sync_time(payload_data, domain)
                shipment_ids = request.env['shipment.shipment'].sudo().search_read(domain, ['id', 'notes','notes_binary'])
                domain = [('shipment_id','!=',False),('shipment_id.driver_id', '=', current_driver_id)]
                self.filter_by_last_sync_time(payload_data, domain)
                stops_ids = request.env['shipment.stop'].sudo().search_read(domain, ['id', 'shipment_id', 'notes','notes_binary','directions','directions_binary'])
                shipment_document_ids = request.env['shipment.document'].sudo().search_read(domain, ['id', 'shipment_id', 'filename','signed_by'])
                for rec in shipment_ids:
                    if rec.get('notes_binary'):
                        file_name = f"shipment_note_{rec['id']}.pdf"
                        response_data.append({
                            'id': rec['id'],
                            'type': 'shipment_note',
                            'file_name': file_name,
                            'url': f"?model=shipment.shipment&download=true&field=notes_binary&filename={file_name}&id={rec['id']}",
                            'shipment_id': rec['id'],
                        })
                for rec in stops_ids:
                    if rec.get('notes_binary'):
                        file_name = f"shipment_stop_notes_{rec['id']}.pdf"
                        response_data.append({
                            'id': rec['id'],
                            'type': 'shipment_stop_note',
                            'file_name': file_name,
                            'url': f"?model=shipment.stop&download=true&field=notes_binary&filename={file_name}&id={rec['id']}",
                            'shipment_id': rec['shipment_id'][0] if rec.get('shipment_id') else False,
                        })
                    if rec.get('directions_binary'):
                        file_name = f"shipment_stop_directions_{rec['id']}.pdf"
                        response_data.append({
                            'id': rec['id'],
                            'type': 'shipment_stop_direction',
                            'file_name': file_name,
                            'url': f"?model=shipment.stop&download=true&field=directions_binary&filename={file_name}&id={rec['id']}",
                            'shipment_id': rec['shipment_id'][0] if rec.get('shipment_id') else False,
                        })
                for rec in shipment_document_ids:
                    file_name = rec.get('filename')
                    if file_name:
                        document_response_dict = {
                            'id': rec['id'],
                            'type': 'shipment_document',
                            'file_name': file_name,
                            'url': f"?model=shipment.document&download=true&field=file&filename={file_name}&id={rec['id']}",
                            'shipment_id': rec['shipment_id'][0] if rec.get('shipment_id') else False,
                        }
                        response_data.append(document_response_dict)
                        if rec.get('signed_by'):
                            #for document signature data signature related data are updated in the response
                            sign_response_dict = document_response_dict.copy()
                            document_response_dict.update({
                                'type': 'shipment_document_sign',
                                'file_name': f"shipment_document_sign_{rec['id']}.png",
                                'url': f"?model=shipment.document&download=true&field=document_signature&filename={file_name}&id={rec['id']}",
                                'signed_by': rec.get('signed_by'),
                            })
                            response_data.append(sign_response_dict)
                    else:
                         _logger.warning("Skipped shipment document %s due to missing filename===================================================", rec.get('id'))


            if len(response_data) > 0:
                return valid_response(response_data)
            else:
                return invalid_response('not_found', 'No record found with the given id', 204)
        except Exception as e:
            _logger.exception("Error while getting File URL data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting File URL data.'
            return invalid_response('bad_request', error_msg, 200)


    #######################################
    # POST APIs
    #######################################


    @validate_token
    @http.route(["/api/v2/fleet/post_shipment_details","/api/v1/fleet/post_shipment_details"], methods=["POST"], type="http", auth="none", csrf=False)
    def post_shipment_details(self, **payload):
        _logger.info("/api/v2/fleet/post_shipment_details: %s", payload)
        try:
            payload_data = json.loads(request.httprequest.data.decode())
            if len(payload_data) > 0:
                sorted_shipment_data = sorted(payload_data, key=lambda x: x["timestamp"])
                status_id = request.env['shipment.status'].sudo()
                geolocation_history = request.env['shipment.geolocation.history'].sudo()
                shipment = request.env['shipment.shipment'].sudo()
                status_seq = {
                    '2':'action_set_assigned',
                    '3':'action_set_accepted',
                    '4':'action_set_at_pickup',
                    '5':'action_set_in_transit',
                    '6':'action_set_at_delivery',
                    '7':'action_set_delivered',
                }
                for shipment_data in sorted_shipment_data:
                    if shipment_data.get('status_id') and shipment_data.get('status_id_change') and shipment_data.get('shipment_id'):
                        status_rec = status_id.browse(int(shipment_data.get('status_id')))
                        shipment_id = shipment.browse(int(shipment_data.get('shipment_id')))
                        if status_rec and shipment_id and hasattr(shipment_id, status_seq.get(str(status_rec.sequence))):
                            action = getattr(shipment, status_seq.get(str(status_rec.sequence)))
                            if callable(action):
                                action()
                    ### Comment For Removing geolocation_history model ###
                    elif shipment_data.get('latitude') and shipment_data.get('longitude') and shipment_data.get('shipment_id'):
                        shipment_id = shipment.browse(int(shipment_data.get('shipment_id')))
                        if shipment_id.exists():
                            zone_name = self.get_timezone_from_lat_lng(shipment_data.get('latitude'),shipment_data.get('longitude'))
                            timezone = datetime.datetime.fromtimestamp(shipment_data.get('timestamp'), ZoneInfo(zone_name)).strftime("%Z")

                            geolocation_history_rec = geolocation_history.create({
                                'source_id': request.env.ref('bista_driver_app.source_driver_phone').id,
                                'reference': f'shipment.shipment,{int(shipment_data.get("shipment_id"))}',
                                'asset_latitude': shipment_data.get('latitude'),
                                'asset_longitude': shipment_data.get('longitude'),
                                'shipment_id': int(shipment_data.get("shipment_id")),
                                'approximate_location': shipment_data.get('accuracy', ""),
                                'speed': shipment_data.get('speed', ""),
                                'date_recorded': datetime.datetime.fromtimestamp(int(shipment_data['timestamp'])).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                'connectivity_status': shipment_data.get('connectivity_status', ""),
                                'company_id': shipment_id.company_id.id if shipment_id.company_id else False,
                                'carrier_id': shipment_id.carrier_id.id if shipment_id.carrier_id else False,
                                'timezone': timezone,
                                'device_unique_id': shipment_data.get('device_unique_id', ""),
                                'device_info': {
                                    'device_brand': shipment_data.get('device_brand', ""),
                                    'device_model': shipment_data.get('device_model', ""),
                                    'device_os': shipment_data.get('device_os', ""),
                                }
                            })
        except Exception as e:
            _logger.exception("Error while updating Shipment Detail data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while updating Shipment Detail data.'
            return invalid_response('bad_request', error_msg, 200)

    #TODO: Not finished yet.Don't call this location api.Need to change.
    @validate_token
    @http.route(["/api/v2/fleet/post_shipment_live_location_update", "/api/v1/fleet/post_shipment_live_location_update"],methods=["POST"], type="http", auth="none", csrf=False)
    def post_shipment_live_location_update(self, **payload):
        _logger.info("/api/v2/fleet/post_shipment_live_location_update: %s", payload)
        try:
            payload_data = json.loads(request.httprequest.data.decode())
            if len(payload_data) > 0:
                sorted_location_data = sorted(payload_data, key=lambda x: x["timestamp"])
                geolocation_history = request.env['geolocation.history'].sudo()
                shipment = request.env['shipment.shipment'].sudo()
                for location_data in sorted_location_data:
                    if location_data.get('latitude') and location_data.get('longitude') and location_data.get('shipment_id'):
                        shipment_id = shipment.browse(int(location_data.get('shipment_id')))
                        if shipment_id.exists():
                            zone_name = self.get_timezone_from_lat_lng(location_data.get('latitude'),location_data.get('longitude'))
                            timezone = datetime.datetime.fromtimestamp(location_data.get('timestamp'), ZoneInfo(zone_name)).strftime("%Z")

                            geolocation_history_rec = geolocation_history.create({
                                'source_id': request.env.ref('bista_driver_app.source_driver_phone').id,
                                'reference': f'shipment.shipment,{int(location_data.get("shipment_id"))}',
                                'asset_latitude': location_data.get('latitude'),
                                'asset_longitude': location_data.get('longitude'),
                                'shipment_id': int(location_data.get("shipment_id")),
                                'approximate_location': location_data.get('accuracy', ""),
                                'speed': location_data.get('speed', ""),
                                'date_recorded': datetime.datetime.fromtimestamp(int(location_data['timestamp'])).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                'connectivity_status': location_data.get('connectivity_status', ""),
                                # 'company_id': shipment_id.company_id.id if shipment_id.company_id else False,
                                'company_id': request.env.company.id,
                                'carrier_id': shipment_id.carrier_id.id if shipment_id.carrier_id else False,
                                'timezone': timezone,
                                'device_unique_id': location_data.get('device_unique_id', ""),
                                'device_info': {
                                    'device_brand': location_data.get('device_brand', ""),
                                    'device_model': location_data.get('device_model', ""),
                                    'device_os': location_data.get('device_os', ""),
                                }
                            })
                            _logger.info(f"Shipment:{shipment_id.name} location updated of timestamp:{location_data.get('timestamp')}")
                return valid_response({'message': "Shipment Live Location updated"})
            else:
                return invalid_response('bad_request', 'No data found in the payload', 200)
        except Exception as e:
            _logger.exception("Error while updating Shipment Live Location data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while updating Shipment Live Location data.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route(["/api/v2/fleet/post_shipment_status_update","/api/v1/fleet/post_shipment_status_update"], methods=["POST"], type="http", auth="none", csrf=False)
    def post_shipment_status_change(self, **payload):
        _logger.info("/api/v2/fleet/post_shipment_status_update: %s", payload)
        try:
            payload_data = json.loads(request.httprequest.data.decode())
            if len(payload_data) > 0:
                error_data = []
                sorted_status_data = sorted(payload_data, key=lambda x: x["timestamp"])
                shipment = request.env['shipment.shipment'].sudo()
                status_ref ={
                    str(request.env.ref('bista_driver_app.shipment_status_accepted').id): 'action_set_accepted',
                    str(request.env.ref('bista_driver_app.shipment_status_at_pickup').id): 'action_set_at_pickup',
                    str(request.env.ref('bista_driver_app.shipment_status_in_transit').id): 'action_set_in_transit',
                    str(request.env.ref('bista_driver_app.shipment_status_at_delivery').id): 'action_set_at_delivery',
                    str(request.env.ref('bista_driver_app.shipment_status_delivered').id): 'action_set_delivered',
                }
                for status_data in sorted_status_data:
                    if status_data.get('status_id') and status_data.get('shipment_id'):
                        # status_rec = status_id.browse(int(status.get('status_id')))
                        shipment_id = shipment.browse(int(status_data.get('shipment_id')))
                        # if shipment_id.exists():
                        try:
                            if shipment_id.exists() and hasattr(shipment_id,status_ref.get(str(status_data['status_id']))):
                                action = getattr(shipment_id, status_ref.get(str(status_data['status_id'])))
                                if callable(action):
                                    action()
                                    _logger.info(f"Shipment:{shipment_id.name} status updated to {shipment_id.status_id.name} in {status_data.get('mode')} mode")
                                # if request.env.ref('bista_driver_app.shipment_status_at_pickup').id == int(status_data['status_id']):
                                #     shipment_id.action_set_at_pickup()
                                # elif request.env.ref('bista_driver_app.shipment_status_in_transit').id == int(status_data['status_id']):
                                #     shipment_id.action_set_in_transit()
                                # elif request.env.ref('bista_driver_app.shipment_status_at_delivery').id == int(status_data['status_id']):
                                #     shipment_id.action_set_at_delivery()
                                # elif request.env.ref('bista_driver_app.shipment_status_delivered').id == int(status_data['status_id']):
                                #     shipment_id.action_set_delivered()
                                # elif request.env.ref('bista_driver_app.shipment_status_accepted').id == int(status_data['status_id']):
                                #     shipment_id.action_set_accepted()
                        except Exception as e:
                            error_data.append({
                                'shipment_id': status_data.get('shipment_id'),
                                'status_id': status_data.get('status_id'),
                                'timestamp': status_data.get('timestamp'),
                                'error': str(e)
                            })
                if len(error_data) > 0:
                    return valid_response(error_data, False)
                return valid_response({'message': "Shipment Status updated"})
            else:
                return invalid_response('bad_request', 'No data found in the payload', 200)
        except Exception as e:
            _logger.exception("Error while updating Shipment Status data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while updating Shipment Status data.'
            return invalid_response('bad_request', error_msg, 200)