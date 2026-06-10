# -*- coding: utf-8 -*-
import json
import logging
import functools
import base64
from collections import defaultdict
import re
from markupsafe import Markup

from odoo import http
from odoo.exceptions import AccessDenied, AccessError, ValidationError
from odoo.http import request, content_disposition, serialize_exception as _serialize_exception, Response

from odoo.addons.bista_mobile_base.controllers.main import BistaBaseApi
from odoo.addons.bista_mobile_base.common import invalid_response, valid_response

from odoo.addons.web.controllers.binary import Binary
from datetime import datetime, timezone
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo import api, fields, models, _, SUPERUSER_ID
import werkzeug.wrappers
from werkzeug.urls import url_encode, url_decode, iri_to_uri
from odoo.exceptions import UserError
import math
import random
import re
from pytz import timezone
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
from werkzeug.utils import redirect
from odoo.tools.pdf import PdfFileReader, PdfFileWriter
import io
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import os 
from reportlab.lib.pagesizes import A4
from odoo.addons.bista_mobile_base.common import validate_token


_logger = logging.getLogger(__name__)

status_color_codes = ['a2a2a2','ee2d2d','dc8534','e8bb1d','5794dd','9f628f','db8865',
                                                '41a9a2', '304be0', 'ee2f8a', '61c36e', '9872e6']
lang_code = {'es':'es_ES', 'en':'en_US'}


# def validate_fleet_token(func):
#     """."""
#     def update_user_lang(user_id):
#         # T2493: Language check from api header on each api call to translate data accordingly
#         lang = request.httprequest.headers.get('lang', False)
#         user_id.fleet_lang = lang_code.get(lang) if lang and not user_id.fleet_lang.startswith(lang) else user_id.fleet_lang
#
#
#     @functools.wraps(func)
#     def wrap(self, *args, **kwargs):
#         """."""
#         access_token = request.httprequest.headers.get("access_token") or kwargs.get('access_token')
#         if not access_token:
#             return invalid_response("access_token_not_found", "missing access token in request header", 401)
#         access_token_data = (
#             request.env["fleet.api.access_token"].sudo().search([("access_token", "=", access_token)], order="id DESC",
#                                                                 limit=1)
#         )
#         if access_token_data:
#             if datetime.now() > access_token_data.access_token_expires:
#                 return invalid_response("access_token_expired", "token seems to have expired", 401)
#         else:
#             return invalid_response("invalid_token", "invalid access token", 401)
#
#         user = access_token_data.user_id
#         request.session.update(user=access_token_data.user_id.id)
#         request.update_env(user=access_token_data.user_id.id)
#         # update_user_lang(access_token_data.user_id)
#         _logger.info(f"In validate_fleet_token: \n user: id:{user.id}, name: {user.name} ")
#         return func(self, *args, **kwargs)
#
#     return wrap


# class BistaFleetApi(http.Controller):
class BistaFleetApi(BistaBaseApi):
    @http.route(
        ["/api/v1/auth/login", "/api/v1/fleet/auth/login"],
        methods=["POST"],
        type="json",
        auth="none",
        csrf=False,
    )
    def auth_login(self, **post):
        params = ["db", "login", "password", "scope", "policy_ts"]
        req_data = json.loads(request.httprequest.data.decode())
        req_params = {key: req_data.get(key) for key in params if req_data.get(key)}
        username = req_params.get("login")
        scope = req_params.get("scope")
        if scope and scope == "driver":
            driver_id = request.env['fleet.driver'].sudo().search([('driver_login', '=', username)])
            if driver_id and driver_id.otp_expiration_time and driver_id.otp_expiration_time < datetime.now():
                return invalid_response("otp_expired", "Your PIN has expired. Kindly request a new PIN to proceed.")

        response = super().auth_login(**post)
        scope = req_params.get("scope")
        # 🔴 IMPORTANT: Convert response → dict
        response_data = json.loads(response.get_data(as_text=True))

        params = ["db", "login", "password", "scope", "policy_ts"]
        req_data = json.loads(request.httprequest.data.decode())
        req_params = {key: req_data.get(key) for key in params if req_data.get(key)}
        uid = request.session.uid
        scope = req_params.get("scope")
        if scope and scope == "driver":
            if not uid:
                info = "authentication failed"
                error = "authentication failed"
                _logger.error(info)
                return invalid_response(status=200, code="login_error", typ=error, message=info)

            server_env = request.env['ir.config_parameter'].sudo().get_param('bista_driver_app.server_env')
            response_data["topic"] = f"{server_env}_topic_id_fleet_{uid}"
            #         "topic": f'{server_env}_topic_id_fleet_{user_id.id}',

            driver_id = request.env['fleet.driver'].sudo().search([('driver_login', '=', username)])
            if req_params.get("policy_ts"):
                driver_id.sudo().with_user(uid).write({"policy_accepted_on": datetime.fromtimestamp(
                    int(req_params.get("policy_ts"))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(response_data),
        )
    # @http.route("/api/v1/fleet/auth/login", methods=["POST"], type="json", auth="none", csrf=False)
    # def fleet_auth_login(self, **post):
    #     """The token URL to be used for getting the access_token and refresh token.
    #
    #     str post[db]: db of the system, in which the user logs in to.
    #
    #     str post[login]: username of the user
    #
    #     str post[password]: password of the user
    #
    #     :param list[str] str post: **post must contain db, login and password.
    #     :returns: https response
    #         if failed error message in the body in json format and
    #         if successful user's details with the access_token.
    #     """
    #     fleet_token = request.env["fleet.api.access_token"]
    #     # T2808: update key value for policy accepted time during login
    #     params = ["db", "login", "password","policy_ts"]
    #     req_data = json.loads(request.httprequest.data.decode())  # convert the bytes format to dict format
    #     req_params = {key: req_data.get(key) for key in params if req_data.get(key)}
    #     db, username, password = (
    #         req_params.get("db") if req_params.get("db") else request.env.cr.dbname,
    #         req_params.get("login"),
    #         req_params.get("password"),
    #     )
    #     _credentials_includes_in_body = all([db, username, password])
    #     if not _credentials_includes_in_body:
    #         # The request post body is empty the credentials maybe passed via the headers.
    #         headers = request.httprequest.headers
    #         db = headers.get("db") if headers.get("db") else request.env.cr.dbname
    #         username = headers.get("login")
    #         password = headers.get("password")
    #         _credentials_includes_in_headers = all([db, username, password])
    #         if not _credentials_includes_in_headers:
    #             # Empty 'db' or 'username' or 'password:
    #             return invalid_response(
    #                 "missing error", "Either of the following are missing [db, username,password]", 200,
    #             )
    #     # Login in odoo database:
    #     session_info = []
    #     driver_id = False
    #     try:
    #         # T2493: OTP expiration check for driver login
    #         driver_id = request.env['fleet.driver'].sudo().search([('driver_login', '=', username)])
    #         # NOTE: Driver app: remove otp_expiration_time
    #         if driver_id and driver_id.otp_expiration_time and driver_id.otp_expiration_time < datetime.now():
    #             return invalid_response("otp_expired", "Your PIN has expired. Kindly request a new PIN to proceed.")
    #         else:
    #             # request.session.authenticate(db, username, password)
    #             credentials = {
    #                 "login": username,
    #                 "password": password,
    #                 "type": "password",
    #             }
    #             request.session.authenticate(db, credentials)
    #         # session_info = request.env['ir.http'].session_info().get('server_version_info', [])
    #     except AccessError as aee:
    #         return invalid_response("access_error", "Error: %s" % aee.name)
    #     except AccessDenied as ade:
    #         return invalid_response("access_denied", "Login, password or db invalid")
    #     except Exception as e:
    #         # Invalid database:
    #         info = "The database name is not valid {}".format(e)
    #         error = "invalid_database"
    #         _logger.error(info)
    #         return invalid_response(typ=error, message=info, status=200)
    #
    #     uid = request.session.uid
    #     # odoo login failed:
    #     if not uid:
    #         info = "authentication failed"
    #         error = "authentication failed"
    #         _logger.error(info)
    #         return invalid_response(status=200, code="login_error", typ=error, message=info)
    #     # T2808:update policy accepted time during login
    #     if req_params.get("policy_ts"):
    #         driver_id.sudo().with_user(uid).write({"policy_accepted_on": datetime.fromtimestamp(int(req_params.get("policy_ts"))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    #     # Generate tokens
    #     access_token, refresh_token = fleet_token.find_one_or_create_fleet_token(user_id=uid, create=True,
    #                                                                          refresh_token_obj=False)
    #     user_id = request.env.user
    #     server_env = request.env['ir.config_parameter'].sudo().get_param('bista_driver_app.server_env')
    #     data = {
    #         "access_token": access_token,
    #         "refresh_token": refresh_token,
    #         "user_id": {
    #             'id': user_id.id,
    #             'name': user_id.name,
    #         },
    #         "topic": f'{server_env}_topic_id_fleet_{user_id.id}',
    #     }
    #     # NOTE: Topic will always be in the format of `staging_topic_id_fleet_2` format.
    #     # Mobile app will concatenate & subscribe to the topic with the user's lang code (e.g. `en`/`es`).
    #     # Example topic: `staging_topic_id_fleet_2_en` & `staging_topic_id_fleet_2_es`
    #
    #     # response_data = self.auth_login_response_data(data)
    #     response_data = {
    #         **{
    #             "status": True,
    #             "count": len(data) if not isinstance(data, str) else 1,
    #         },
    #         **data
    #     }
    #
    #     return werkzeug.wrappers.Response(
    #         status=200,
    #         content_type="application/json; charset=utf-8",
    #         headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
    #         response=json.dumps(response_data)
    #     )

    @http.route("/api/v1/fleet/get_access_token", type="http", auth="none", methods=["GET"], csrf=False)
    def get_access_token(self, **payload):
        """
            Gets  refresh token from request and
            returns corresponding access token .
        """
        _logger.info("/api/v1/get_access_token payload: %s", payload)

        try:
            payload_data = payload
            # fleet_token = request.env["fleet.api.access_token"].sudo()
            fleet_token = request.env["api.access_token"].sudo()
            if 'refresh_token' in payload_data and payload_data['refresh_token']:
                token_id = fleet_token.search([("refresh_token", "=", payload['refresh_token'])])
                if token_id:
                    if datetime.now() > fields.Datetime.from_string(token_id.refresh_token_expires):
                        return invalid_response('data_expires', "refresh token expires", 401)
                    elif not token_id.access_token or datetime.now() > fields.Datetime.from_string(
                            token_id.access_token_expires):
                        uid = request.session.uid
                        # access_token, refresh_token = fleet_token.find_one_or_create_fleet_token(user_id=uid, create=True, refresh_token_obj=token_id)
                        access_token, refresh_token = fleet_token._find_one_or_create_token(user_id=uid, create=True, refresh_token_obj=token_id)
                        # TODO: response data structure need to be updated to dict only for next apk release
                        return valid_response({'access_token': access_token})
                    else:
                        return valid_response({'access_token': token_id.access_token})
                else:
                    return invalid_response('not_found', 'No refresh token found.', 401)
            else:
                return invalid_response('not_found', 'No refresh token found.', 401)
        except Exception as e:
            _logger.exception("Error while getting access_token for payload: %s", payload)
            error_msg = 'Error while getting access_token.'
            return invalid_response('bad_request', error_msg, 401)

    @http.route("/api/v1/fleet/generate_driver_otp", methods=["POST"], type="json", auth="none", csrf=False)
    def post_generate_driver_otp(self, **payload):
        _logger.info("/api/v1/fleet/generate_driver_otp: %s", payload)
        try:
            req_data = json.loads(request.httprequest.data.decode())
            phone_number = req_data.get('phone_number')
            res = False
            if phone_number:
                driver_id = request.env['fleet.driver'].sudo().search([('driver_login','=',phone_number)])
                if driver_id:
                    res = driver_id.with_context(from_mobile_app = True).sudo().generate_driver_otp(phone_number)
                if res:
                    return valid_response("OTP generated.")
                else:
                    return invalid_response("invalid_number", "Invalid phone number.", 200)
            else:
                return invalid_response("invalid_number", "Enter your phone number.", 200)
        except Exception as e:
            _logger.exception("Error while generating otp for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while generating otp.'
            return invalid_response('bad_request', error_msg, 200)

    #######################################
    # GET APIs
    #######################################
    def _get_current_driver_id(self):
        """
            returns the current fleet.driver user record id.
        """
        current_driver_id = request.env['fleet.driver'].search_read([('user_id','=',request.session.user)],['id'])
        if current_driver_id:
            current_driver_id = current_driver_id[0].get('id')
        return current_driver_id

    def _convert_to_local_timezone(self, utc_date):
        """Convert UTC date to user's local timezone"""
        try:
            user_tz = request.env.user.tz or 'UTC'
            utc_tz = timezone('UTC')
            user_tz = timezone(user_tz)
            localized_date = utc_tz.localize(utc_date).astimezone(user_tz)
            return localized_date.strftime('%-m/%-d/%Y %I:%M %p')
        except Exception as e:
            return {'error': str(e)}
    # def _format_time(self, time_str):
    #     return time_str.strftime('%-m/%-d/%Y %I:%M %p')

    def _prepare_list_response_data(self, Model, field_list, datas):
        """
            Common function to prepare list data where only value is enough including related fields
        """
        response_data = []
        for data in datas:
            response = {}
            # T2695: status tag change in shipment list according to language.
            requested_lang = request.httprequest.headers.get("lang",False)
            ignore_convertion_field = ['planned_arrival', 'planned_pickup', 'actual_pickup', 'planned_delivery',
                                       'actual_delivery']
            for field_name in field_list:
                field_obj = Model.sudo()._fields.get(field_name)
                if not field_obj:
                    return {"response": 'not_found', "message": f'{field_name} does not exist', 'status': 204}

                if field_obj.type == 'many2one':
                    field_record = data.get(field_name,False)
                    # T2695: status tag change in shipment list according to language.
                    if field_name == 'status_id' and requested_lang and requested_lang == 'es' and field_record:
                        status_id_es = request.env['shipment.status'].sudo().search_read([('id', '=', int(field_record[0]))],['name_es'],limit=1)
                        field_record = (status_id_es[0].get('id'),status_id_es[0].get('name_es'))
                    response.update({
                        f'{field_name}': field_record[1] if field_record else ""
                    })
                elif field_obj.type in ['one2many', 'many2many']:
                    values = request.env[field_obj.comodel_name].sudo().search([('id', 'in', data.get(field_name))], order='id asc')
                    response.update({
                        f'{field_name}': {
                            'data': [{
                                'id': rec.id,
                                'name': rec.name,
                            } for rec in values] if values else [],
                        }
                    })
                # elif 'image' in field_name:
                #     image_id = int(payload_data['id'])
                #     response.update({
                #         f'{field_name}': f"/api/web/image?model={Model._name}&field={field_name}&id={image_id}"})
                elif field_obj.type == 'datetime':
                    datetime_data = ""
                    if field_name in ignore_convertion_field:
                        datetime_data = data.get(field_name).strftime('%-m/%-d/%Y %I:%M %p') if data.get(field_name) else ''
                    else:
                        datetime_data = data.get(field_name) and self._convert_to_local_timezone(data.get(field_name)) if data.get(field_name) else ''

                    response.update({
                            f'{field_name}': datetime_data
                        })
                elif field_obj.type == 'boolean':
                    response.update({
                        f'{field_name}': data.get(field_name) or False
                    })
                else:
                    response.update({
                        f'{field_name}': data.get(field_name) or ""
                    })
            if Model._name == 'shipment.shipment':
                response.update({"status_color_code": status_color_codes[response['status_color']] if response.get('status_color') else 'a2a2a2' })
                response.pop('status_color',None)
                if response.get('item_ids') and response['item_ids'].get('data'):
                    response['item_ids']=response['item_ids']['data'][0].get('name')
                elif response.get('item_ids') and not response['item_ids'].get('data',):
                    response['item_ids']= ""
            # T2785: pickup_id_name and   delivery_id_name in shipmet list response
            response.update({'pickup_id_name': response.get('pickup_id',""),
                            'delivery_id_name': response.get('delivery_id',"")})
            response_data.append(response)

        # priority_order = ['Dispatched', 'At Pickup', 'In Transit', 'At Delivery']
        priority_order = [3, 4, 5, 6]

        def sort_shipment_list(data):
            date = datetime.strptime(data['create_date'], "%m/%d/%Y %I:%M %p")
            now = datetime.now()
            if data['status_sequence'] in priority_order:
              return 1, priority_order.index(data['status_sequence']), None
            elif data['status_sequence'] == 2:
                # return 2, data['create_date']
                planned_pickup = datetime.strptime(data['planned_pickup'], "%m/%d/%Y %I:%M %p")
                return 2, abs((planned_pickup - now).total_seconds())
            elif data['status_sequence'] == 1:
                return 3, data['create_date']
            elif data['status_sequence'] == 7:
                if data.get('actual_delivery'):
                    actual_delivery = datetime.strptime(data['actual_delivery'], "%m/%d/%Y %I:%M %p")
                    return 4, -actual_delivery.timestamp()
                else:
                    return 4, -date.timestamp()
            elif data['status_sequence'] == 8:
                return 5, -date.timestamp()
            else:
                return 6, None

        if len(response_data)>0:
            response_data = sorted(response_data, key=sort_shipment_list)
        return response_data

    def _prepare_response_data(self, Model, field_list, datas):
        response_list = super()._prepare_response_data(Model, field_list, datas)

        access_token = request.httprequest.headers.get("access_token")
        if not access_token:
            return response_list

        act_record = request.env['api.access_token'].sudo().search(
            [("access_token", "=", access_token)],
            order="id DESC",
            limit=1
        )
        if not act_record or act_record.scope != 'driver':
            return response_list

        from_fleet_v2 = request.env.context.get('from_fleet_v2')

        for i, response in enumerate(response_list):
            if not isinstance(response, dict):
                continue

            new_response = {}

            for field_name, value in response.items():
                field_obj = Model._fields.get(field_name)

                # ✅ MANY2ONE → flatten
                if isinstance(value, dict) and value.get("type") == "many2one":
                    data_dict = value.get("data", {})

                    if Model._name == 'shipment.stop' and field_name == 'location_id':
                        new_response['name'] = data_dict.get("name") or ""

                    elif from_fleet_v2 and field_name == 'shipment_id':
                        new_response['shipment_id'] = data_dict.get("id") or ""

                    else:
                        new_response[field_name] = {
                            "id": data_dict.get("id"),
                            "name": data_dict.get("name"),
                        } if data_dict else {}

                # ✅ ONE2MANY / MANY2MANY → already almost correct
                elif isinstance(value, dict) and value.get("type") in ["one2many", "many2many"]:
                    records = value.get("data", [])
                    new_response[field_name] = [
                        {
                            "id": rec.get("id"),
                            "name": rec.get("name"),
                        }
                        for rec in records
                    ] if records else []

                # ✅ DATETIME
                elif field_obj and field_obj.type == 'datetime':
                    datetime_data = ""
                    raw_value = value

                    ignore_conversion_field = [
                        'planned_arrival', 'planned_pickup', 'actual_pickup',
                        'planned_delivery', 'actual_delivery'
                    ]

                    if raw_value:
                        try:
                            if isinstance(raw_value, (int, float)):
                                raw_value = datetime.fromtimestamp(raw_value)
                            elif isinstance(raw_value, str):
                                if raw_value.isdigit():
                                    raw_value = datetime.fromtimestamp(int(raw_value))
                                else:
                                    raw_value = datetime.strptime(raw_value, '%Y-%m-%d %H:%M:%S')
                        except Exception:
                            raw_value = False

                    if field_name in ignore_conversion_field:
                        datetime_data = raw_value.strftime('%-m/%-d/%Y %I:%M %p') if raw_value else ''
                    else:
                        datetime_data = raw_value and self._convert_to_local_timezone(raw_value) if raw_value else ''

                    new_response[field_name] = datetime_data

                # ✅ BOOLEAN
                elif field_obj and field_obj.type == 'boolean':
                    new_response[field_name] = bool(value)

                # ✅ HTML
                elif field_obj and field_obj.type == 'html':
                    if value:
                        clean_text = re.sub(re.compile('<.*?>'), '', value)
                        clean_text = clean_text.lstrip('\n')
                        clean_text = clean_text[:100] + "..."
                        new_response[field_name] = clean_text
                    else:
                        new_response[field_name] = ""

                # ✅ DEFAULT
                else:
                    new_response[field_name] = value or ""

            # ✅ Special fix
            if new_response.get('current_shipment_id') and isinstance(new_response['current_shipment_id'], str):
                new_response['current_shipment_id'] = None

            response_list[i] = new_response

        return response_list

    # def _prepare_response_data(self, Model, field_list, datas):
    #     response_data = []
    #     from_fleet_v2 = request.env.context.get('from_fleet_v2')
    #     for data in datas:
    #         response = {}
    #         ignore_convertion_field = ['planned_arrival','planned_pickup', 'actual_pickup','planned_delivery','actual_delivery']
    #         for field_name in field_list:
    #             field_obj = Model.sudo()._fields.get(field_name)
    #             if not field_obj:
    #                 return {"response": 'not_found', "message": f'{field_name} does not exist', 'status': 404}
    #
    #             if field_obj.type == 'many2one':
    #                 field_record = data.get(field_name)
    #                 if Model._name == 'shipment.stop' and field_name == 'location_id':
    #                     response.update({
    #                         'name': field_record[1] if field_record else "",})
    #                 # T2785: pass only shipment id for offline api
    #                 if from_fleet_v2 and field_name == 'shipment_id':
    #                     response.update({
    #                         'shipment_id': field_record[0] if field_record else "",})
    #                 else:
    #                     response.update({
    #                         f'{field_name}': {
    #                                 'id': field_record[0],
    #                                 'name': field_record[1]
    #                             } if field_record else {}
    #
    #                     })
    #             elif field_obj.type in ['one2many', 'many2many']:
    #                 values = request.env[field_obj.comodel_name].sudo().search([('id', 'in', data.get(field_name))])
    #                 response.update({
    #                     f'{field_name}':
    #                         [{
    #                             'id': rec.id,
    #                             # 'name': rec.name,
    #                             'name': rec.display_name,
    #                         } for rec in values] if values else [],
    #
    #                 })
    #             # elif 'image' in field_name:
    #             #     image_id = int(payload_data['id'])
    #             #     response.update({
    #             #         f'{field_name}': f"/api/web/image?model={Model._name}&field={field_name}&id={image_id}"})
    #             elif field_obj.type == 'datetime':
    #                 datetime_data = ""
    #                 if field_name in ignore_convertion_field:
    #                     datetime_data = data.get(field_name).strftime('%-m/%-d/%Y %I:%M %p') if data.get(field_name) else ''
    #                 else:
    #                     datetime_data = data.get(field_name) and self._convert_to_local_timezone(data.get(field_name)) if data.get(field_name) else ''
    #                 response.update({
    #                         f'{field_name}': datetime_data
    #                     })
    #             elif field_obj.type == 'boolean':
    #                 response.update({
    #                     f'{field_name}': data.get(field_name) or False
    #                 })
    #             elif field_obj.type == 'html':
    #                 raw_html = data.get(field_name)
    #                 if raw_html:
    #                     clean_text = re.sub(re.compile('<.*?>'), '', raw_html)
    #                     clean_text = clean_text.lstrip('\n')
    #                     clean_text = clean_text[:100] + "..."
    #                     response.update({
    #                         f'{field_name}': clean_text,
    #                     })
    #                 else:
    #                     response.update({
    #                         f'{field_name}': "",
    #                     })
    #             else:
    #                 response.update({
    #                     f'{field_name}': data.get(field_name) or ""
    #                 })
    #         # T2493: current shipment value alter
    #         if response.get('current_shipment_id') and isinstance(response['current_shipment_id'],str):
    #             response['current_shipment_id'] = None
    #         response_data.append(response)
    #     return response_data

    def _get_shipment_list_data(self, domain, field_list):
        shipment_shipment = request.env['shipment.shipment']
        shipments= shipment_shipment.sudo().search_read(domain, field_list)
        if shipments:
            response_data = self._prepare_list_response_data(shipment_shipment, field_list, shipments)
            return response_data
        else:
            return {"response": 'not_found', "message": 'No record found with the given id', 'status': 204}

    @validate_token
    @http.route("/api/v1/fleet/get_shipment_list", methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_list(self, **payload):
        _logger.info("/api/v1/fleet/get_shipment_list: %s", payload)
        try:
            payload_data = payload
            domain = []
            current_driver_id = self._get_current_driver_id()
            if current_driver_id:
                domain = [('driver_id','=',current_driver_id)]
                field_list = [
                    'id', 'name', 'status_id', 'status_sequence','status_color', 'pickup_id', 'delivery_id', 'sale_order_no', 'planned_pickup', 'planned_delivery',
                    'actual_delivery','pickup_timezone', 'delivery_timezone', 'item_ids','tracking_status','create_date']
                if payload_data.get('id'):
                    domain.append(('id', '=', int(payload_data['id'])))
                #TODO: Need to figure out why record rules is not working while basic search/search_read
                #      Disucssion with other team to create separate domain function for driver user
                # if user_id.has_group('bista_driver_app.group_call_out_readonly_user_access') and not user_id.has_group(
                #                     'bista_driver_app.group_shipment_dispatcher_access'):
                #     domain.append(('id', 'in', user_id.get_allowed_shipment_ids()))
                response_data = self._get_shipment_list_data(domain, field_list)
                if isinstance(response_data, list):
                    return valid_response(response_data)
                else:
                    return invalid_response(response_data['response'], response_data['message'],response_data['status'])
            else:
                return invalid_response('invalid_user', "Current user is not a driver user", 204)

        except Exception as e:
            _logger.exception("Error while getting shipment data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting shipment data.'
            return invalid_response('bad_request', error_msg, 200)


    def _get_driver_user_detail(self, field_list):
        fleet_driver= request.env['fleet.driver']
        user_id = request.session.get('user')
        fleet_driver_data = fleet_driver.search_read([('user_id','=',user_id)], field_list)
        if fleet_driver_data:
            fleet_driver_data = fleet_driver_data[0]
            if fleet_driver_data.get('carrier_id', False):
                fleet_driver_data['carrier_id'] = fleet_driver_data['carrier_id'][1]
            else:
                fleet_driver_data['carrier_id'] = None
            return fleet_driver_data
        else:
            return {"response": 'not_found', "message": 'No Driver found with the given id', 'status': 204}

    @validate_token
    @http.route("/api/v1/fleet/get_driver_user_detail", methods=["GET"], type="http", auth="none", csrf=False)
    def get_driver_user_detail(self, **payload):
        _logger.info("/api/v1/fleet/get_driver_user_detail: %s", payload)
        try:
            field_list = ['id', 'driver_name', 'driver_login', 'carrier_id','test_user']
            response_data = self._get_driver_user_detail(field_list)
            if response_data.get('id'):
                response_data['name'] = response_data.pop('driver_name')
                response_data['login'] = response_data.pop('driver_login')
                return valid_response(response_data)
            else:
                return invalid_response(response_data)

        except Exception as e:
            _logger.exception("Error while getting Driver User data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting Driver User data.'
            return invalid_response('bad_request', error_msg, 200)


    def _prepare_shipment_detail_data(self, shipment_shipment, field_list, shipment_data_obj):
        response_data_list = self._prepare_response_data(shipment_shipment, field_list, shipment_data_obj)
        from_fleet_v2 = request.env.context.get('from_fleet_v2')

        if response_data_list:
            for response_data in response_data_list:
                if response_data.get('stop_ids',False) and response_data['stop_ids']:
                    stop_ids = []
                    for stop in response_data['stop_ids']:
                        if from_fleet_v2:  # v2 API data prepare
                            stop_ids.append(stop.get('id'))

                        else:
                            if stop.get('id'):
                                stop_field_list =  ['id','location_id','location_name','location_type','planned_arrival','timezone', 'formatted_address', 'contact_name',
                                                    'contact_phone', 'sequence', 'directions', 'notes', 'latitude', 'longitude']
                                shipment_stop = request.env['shipment.stop'].sudo()
                                stop_data = shipment_stop.search_read([('id','=',stop.get('id'))],stop_field_list)
                                stop_data = self._prepare_response_data(shipment_stop, stop_field_list, stop_data)[0]
                                stop_name = stop_data.pop('location_name')
                                if not stop_data.get('name'):
                                    stop_data['name'] = stop_name
                                if stop_data.get('planned_arrival'):
                                    stop_data['planned_arrival']+= ' ' + stop_data['timezone']
                                    stop_data.pop('timezone', None)
                                if stop_data.get('latitude'):
                                    stop_data['latitude'] = stop_data['latitude'].replace("−", "-")
                                if stop_data.get('longitude'):
                                    stop_data['longitude'] = stop_data['longitude'].replace("−", "-")
                                stop.update(stop_data) if stop_data else {}
                    if from_fleet_v2:
                        response_data.update({'stop_ids': stop_ids})
                    else:
                        response_data.update({
                            'stop_ids': sorted(response_data.get('stop_ids'), key=lambda l: l['sequence']),
                        })
                if response_data.get('status_id'):
                    status_id = response_data['status_id'].get('id')
                    shipment_status = request.env['shipment.status']
                    status_field_list = []
                    # T2785: fleet offline changes
                    if from_fleet_v2:
                        status_field_list = ['sequence','color']
                        status_data = shipment_status.search_read([('id','=',status_id)], status_field_list)
                        status_data = self._prepare_response_data(shipment_status,status_field_list,status_data)[0]
                        response_data.update({
                            "current_status_id": status_id,
                            "current_status_name": response_data['status_id'].get('name'),
                            "status_sequence": status_data.get('sequence'),
                            "status_color_code": status_color_codes[status_data['color']] if status_data.get('color') else 'a2a2a2',
                        })
                        response_data.pop('status_id')
                    else:
                        status_field_list = ['id','name', 'name_es', 'is_driver_can_choose','location_tracking','color','is_driver_can_choose','status_action',
                                            'is_completed','is_cancelled']
                        app_language = request.httprequest.headers.get('lang')
                        if app_language == 'es':
                            status_field_list+=['button_name_es']
                        else:
                            status_field_list+=['button_name_en']
                        status_data = shipment_status.search_read([('id','=',status_id)], status_field_list)
                        status_data = self._prepare_response_data(shipment_status,status_field_list,status_data)[0]
                        if app_language == 'es':
                            status_data.update({'name': status_data['name_es']})
                            status_data.update({'button_name': status_data['button_name_es']})
                            status_data.pop('button_name_es',None)
                        else:
                            status_data.update({'button_name': status_data['button_name_en']})
                            status_data.pop('button_name_en',None)
                        # to hide Change status button in pending state
                        # button_hide = True if status_data.get('id') == request.env.ref('bista_driver_app.shipment_status_pending').id else False
                        # if not status_data.get('is_driver_can_choose') and not status_data.get('is_completed') and not status_data.get('is_cancelled'):
                        #     button_hide = True
                        status_data.update({'button_hide': True if status_data.get('id') == request.env.ref('bista_driver_app.shipment_status_pending').id else False})
                        response_data['status_id'].update(status_data)
                        response_data['status_id'].update({"status_color_code": status_color_codes[status_data['color']] if status_data.get('color') else 'a2a2a2' })
                        response_data['status_id'].pop('color',None)

                if response_data.get('document_ids'):
                    # T2785: fleet offline changes
                    if from_fleet_v2:
                        response_data.update({'document_ids': [rec['id'] for rec in response_data.get('document_ids') if rec.get('id')]})

                    else:
                        for document in response_data.get('document_ids'):
                            if document.get('id'):
                                shipment_document = request.env['shipment.document']
                                document_field_list = ['document_type_id']
                                document_domain = [('id', '=', document.get('id'))]
                                document_data = shipment_document.search_read(document_domain, document_field_list)
                                document_data = self._prepare_response_data(shipment_document, document_field_list, document_data)[0]
                                document.update(document_data) if document_data else {}

### CALL OUT REQUEST Related COde ###
                # if response_data.get('call_out_id'):
                #     call_out = response_data.get('call_out_id')
                #     if call_out.get('id'):
                #         call_out_request = request.env['call.out.request']
                #         call_out_field_list = ['rig_id','rig_name','partner_id','contact_2_id']
                #         call_out_domain = [('id', '=', call_out.get('id'))]
                #         call_out_data = call_out_request.sudo().search_read(call_out_domain, call_out_field_list)
                #         call_out_data = self._prepare_response_data(call_out_request, call_out_field_list, call_out_data)[0]
                #
                #         if call_out_data.get('partner_id'):
                #             partner = call_out_data.get('partner_id')
                #             if partner.get('id'):
                #                 res_partner = request.env['res.partner'].sudo()
                #                 res_partner_field_list = ['phone']
                #                 res_partner_domain = [('id', '=', partner.get('id'))]
                #                 partner_data = res_partner.search_read(res_partner_domain, res_partner_field_list)
                #                 partner_data = self._prepare_response_data(res_partner, res_partner_field_list, partner_data)[0]
                #                 partner.update(partner_data)
                #
                #         if call_out_data.get('contact_2_id'):
                #             partner = call_out_data.get('contact_2_id')
                #             if partner.get('id'):
                #                 res_partner = request.env['res.partner'].sudo()
                #                 res_partner_field_list = ['phone']
                #                 res_partner_domain = [('id', '=', partner.get('id'))]
                #                 partner_data = res_partner.search_read(res_partner_domain, res_partner_field_list)
                #                 partner_data = self._prepare_response_data(res_partner, res_partner_field_list, partner_data)[0]
                #                 partner.update(partner_data)
                #         if not call_out_data.get('rig_id'):
                #             rig_id = {
                #                 'id': 0,
                #                 'name': call_out_data.get('rig_name')
                #             }
                #             call_out_data.update({'rig_id':rig_id})
                #             call_out_data.pop('rig_name',None)
                #         response_data.update(call_out_data) if call_out_data else {}

                item_records = response_data.get('item_ids')
                item_name_list = [item_record.get('name') for item_record in item_records] if item_records else []
                response_data.update({
                    'item_ids': item_name_list,
                })
                if from_fleet_v2:
                    pickup_id = response_data.get('pickup_id')
                    delivery_id = response_data.get('delivery_id')
                    response_data.update({'pickup_id_name': pickup_id.get('name') if pickup_id else "",
                                            'delivery_id_name': delivery_id.get('name') if delivery_id else ""})
            if from_fleet_v2:
                return response_data_list
            else:
                return response_data_list[0]

    def _get_shipment_detail_data(self,domain,field_list):
        shipment_shipment = request.env['shipment.shipment'].sudo()
        shipment= shipment_shipment.search_read(domain, field_list)
        from_fleet_v2 = request.env.context.get('from_fleet_v2')
        current_driver_id = self._get_current_driver_id()
        if shipment:
            if not from_fleet_v2:
                # T2750: check shipment driver with current driver during shipment refresh
                if not shipment[0].get('driver_id') or shipment[0]['driver_id'][0] != current_driver_id:
                    app_language = request.httprequest.headers.get('lang')
                    if app_language == 'es':
                        error_msg = 'Este envío ya no está asignado a usted. Será devuelto a la lista de envíos.'
                    else:
                        error_msg = "This shipment is no longer assigned to you.You'll be returned to the Shipments list."
                    return {"response": 'shipment_revoked', "message": error_msg, 'status': 403}
            if from_fleet_v2:
                response_list = []
                # for shipment_record in shipment:
                response_data = self._prepare_shipment_detail_data(shipment_shipment, field_list, shipment)
                response_list.append(response_data)
                return response_data
                # return response_list
            else:
                response_data = self._prepare_shipment_detail_data(shipment_shipment, field_list, shipment)
            # if response_data:
            #     # response_data = response_data[0]
            #     if response_data.get('stop_ids',False) and response_data['stop_ids']:
            #         for stop in response_data['stop_ids']:
            #             if stop.get('id'):
            #                 stop_field_list =  ['id','location_id','location_name','location_type','planned_arrival','timezone', 'formatted_address', 'contact_name',
            #                                     'contact_phone', 'sequence', 'directions', 'notes', 'latitude', 'longitude']
            #                 shipment_stop = request.env['shipment.stop'].sudo()
            #                 stop_data = shipment_stop.search_read([('id','=',stop.get('id'))],stop_field_list)
            #                 stop_data = self._prepare_response_data(shipment_stop, stop_field_list, stop_data)[0]
            #                 stop_name = stop_data.pop('location_name')
            #                 if not stop_data.get('name'):
            #                     stop_data['name'] = stop_name
            #                 if stop_data.get('planned_arrival'):
            #                     stop_data['planned_arrival']+= ' ' + stop_data['timezone']
            #                     stop_data.pop('timezone', None)
            #                 if stop_data.get('latitude'):
            #                     stop_data['latitude'] = stop_data['latitude'].replace("−", "-")
            #                 if stop_data.get('longitude'):
            #                     stop_data['longitude'] = stop_data['longitude'].replace("−", "-")
            #                 stop.update(stop_data) if stop_data else {}

            #         response_data.update({
            #             'stop_ids': sorted(response_data.get('stop_ids'), key=lambda l: l['sequence']),
            #         })
            #     if response_data.get('status_id'):
            #         status_id = response_data['status_id'].get('id')
            #         shipment_status = request.env['shipment.status']
            #         status_field_list = ['id','name', 'name_es', 'is_driver_can_choose','location_tracking','color','is_driver_can_choose','status_action',
            #                             'is_completed','is_cancelled']
            #         app_language = request.httprequest.headers.get('lang')
            #         if app_language == 'es':
            #             status_field_list+=['button_name_es']
            #         else:
            #             status_field_list+=['button_name_en']
            #         status_data = shipment_status.search_read([('id','=',status_id)], status_field_list)
            #         status_data = self._prepare_response_data(shipment_status,status_field_list,status_data)[0]
            #         if app_language == 'es':
            #             status_data.update({'name': status_data['name_es']})
            #             status_data.update({'button_name': status_data['button_name_es']})
            #             status_data.pop('button_name_es',None)
            #         else:
            #             status_data.update({'button_name': status_data['button_name_en']})
            #             status_data.pop('button_name_en',None)
            #         # to hide Change status button in pending state
            #         # button_hide = True if status_data.get('id') == request.env.ref('bista_driver_app.shipment_status_pending').id else False
            #         # if not status_data.get('is_driver_can_choose') and not status_data.get('is_completed') and not status_data.get('is_cancelled'):
            #         #     button_hide = True
            #         status_data.update({'button_hide': True if status_data.get('id') == request.env.ref('bista_driver_app.shipment_status_pending').id else False})
            #         response_data['status_id'].update(status_data)
            #         response_data['status_id'].update({"status_color_code": status_color_codes[status_data['color']] if status_data.get('color') else 'a2a2a2' })
            #         response_data['status_id'].pop('color',None)

            #     if response_data.get('document_ids'):
            #         for document in response_data.get('document_ids'):
            #             if document.get('id'):
            #                 shipment_document = request.env['shipment.document']
            #                 document_field_list = ['document_type_id']
            #                 document_domain = [('id', '=', document.get('id'))]
            #                 document_data = shipment_document.search_read(document_domain, document_field_list)
            #                 document_data = self._prepare_response_data(shipment_document, document_field_list, document_data)[0]
            #                 document.update(document_data) if document_data else {}

            #     if response_data.get('call_out_id'):
            #         call_out = response_data.get('call_out_id')
            #         if call_out.get('id'):
            #             call_out_request = request.env['call.out.request']
            #             call_out_field_list = ['rig_id','rig_name','partner_id','contact_2_id']
            #             call_out_domain = [('id', '=', call_out.get('id'))]
            #             call_out_data = call_out_request.sudo().search_read(call_out_domain, call_out_field_list)
            #             call_out_data = self._prepare_response_data(call_out_request, call_out_field_list, call_out_data)[0]

            #             if call_out_data.get('partner_id'):
            #                 partner = call_out_data.get('partner_id')
            #                 if partner.get('id'):
            #                     res_partner = request.env['res.partner'].sudo()
            #                     res_partner_field_list = ['phone']
            #                     res_partner_domain = [('id', '=', partner.get('id'))]
            #                     partner_data = res_partner.search_read(res_partner_domain, res_partner_field_list)
            #                     partner_data = self._prepare_response_data(res_partner, res_partner_field_list, partner_data)[0]
            #                     partner.update(partner_data)

            #             if call_out_data.get('contact_2_id'):
            #                 partner = call_out_data.get('contact_2_id')
            #                 if partner.get('id'):
            #                     res_partner = request.env['res.partner'].sudo()
            #                     res_partner_field_list = ['phone']
            #                     res_partner_domain = [('id', '=', partner.get('id'))]
            #                     partner_data = res_partner.search_read(res_partner_domain, res_partner_field_list)
            #                     partner_data = self._prepare_response_data(res_partner, res_partner_field_list, partner_data)[0]
            #                     partner.update(partner_data)
            #             if not call_out_data.get('rig_id'):
            #                 rig_id = {
            #                     'id': 0,
            #                     'name': call_out_data.get('rig_name')
            #                 }
            #                 call_out_data.update({'rig_id':rig_id})
            #                 call_out_data.pop('rig_name',None)
            #             response_data.update(call_out_data) if call_out_data else {}

            #     item_records = response_data.get('item_ids')
            #     item_name_list = [item_record.get('name') for item_record in item_records] if item_records else []
            #     response_data.update({
            #         'item_ids': item_name_list,
            #     })

                return response_data
        else:
            return {"response": 'not_found', "message": 'No record found with the given id', 'status': 204}


    @validate_token
    @http.route("/api/v1/fleet/get_shipment_detail", methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_detail(self, **payload):
        _logger.info("/api/v1/fleet/get_shipment_detail: %s", payload)
        try:
            payload_data = payload
            field_list = ['id','name','status_id','driver_id','stop_ids','document_ids','sale_order_no','customer_id',
                          'item_ids','notes','tracking_status'] # 'samsara_eld_asset_id','call_out_id',
            domain = []
            if payload_data.get('id'):
                domain = [('id','=', int(payload_data['id']))]

            response_data = self._get_shipment_detail_data(domain,field_list)
            if response_data.get('id'):
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
    

    def _get_document_type_list_data(self, domain, field_list):
        document_type = request.env['driver.documents.type']
        domain += [('is_shipment_document', '=', True)]

        document_type_records = document_type.sudo().search_read(domain, field_list)

        if document_type_records:
            response_data = self._prepare_response_data(document_type, field_list, document_type_records)
            return response_data
        else:
            return {"response": 'not_found', "message": 'No record found with the given id', 'status': 204}

    @validate_token
    @http.route("/api/v1/fleet/get_document_type_list", methods=["GET"], type="http", auth="none", csrf=False)
    def get_document_type_list(self, **payload):
        _logger.info("/api/v1/fleet/get_document_types: %s", payload)
        try:
            payload_data = payload
            field_list = ['id', 'type_name', 'is_default_shipment_document']
            domain = []

            response_data = self._get_document_type_list_data(domain, field_list)
            if isinstance(response_data, list):
                return valid_response(response_data)
            else:
                return invalid_response(response_data['response'], response_data['message'],response_data['status'])
        except Exception as e:
            _logger.exception("Error while getting Document types data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while getting Document types data"
            return invalid_response('bad_request', error_msg, 200)

    def _prepare_shipment_location_tracking_status_data(self, domain, field_list):
        fleet_driver = request.env['fleet.driver'].sudo()
        driver_data = fleet_driver.search_read(domain,field_list)
        if driver_data:
            # driver_data = driver_data[0]
            response_data = self._prepare_response_data(fleet_driver, field_list, driver_data)
            current_shipment_id = response_data[0].get('current_shipment_id')
            tracking_status = False
            if current_shipment_id: 
                current_shipment_rec = request.env['shipment.shipment'].sudo().browse(current_shipment_id)
                tracking_status = current_shipment_rec.tracking_status
                response_data[0].update({
                    "shipment_status_data":{
                        "status_id": current_shipment_rec.status_id.id,
                        "location_tracking": current_shipment_rec.status_id.location_tracking
                    }
                })
            location_reporting_frequency = request.env.ref('bista_driver_app.shipment_settings_location_reporting_frequency')
            location_reporting_distance_filter = request.env.ref('bista_driver_app.shipment_settings_location_reporting_distance_filter')
            response_data[0].update({'tracking_status': tracking_status if tracking_status else "",
                                    'location_reporting_frequency': location_reporting_frequency.value if location_reporting_frequency else "" ,
                                    'location_reporting_distance_filter': location_reporting_distance_filter.value*0.3048 if location_reporting_distance_filter else ""})
            return response_data
        else:
            return {"response": 'not_found', "message": 'No driver record found with the current user', 'status': 204}

    @validate_token
    @http.route("/api/v1/fleet/get_shipment_location_tracking_status", methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_location_tracking_status(self, **payload):
        _logger.info("/api/v1/fleet/get_shipment_location_tracking_status: %s", payload)
        try:
            payload_data = payload
            field_list = ['id', 'is_continuous_location_tracking', 'current_shipment_id', 'is_from_logout']
            current_driver_id = self._get_current_driver_id()
            if current_driver_id:
                domain = [('id','=', current_driver_id)]
                response_data = self._prepare_shipment_location_tracking_status_data(domain, field_list)
                if isinstance(response_data, list):
                    return valid_response(response_data[0])
                else:
                    return invalid_response(response_data['response'], response_data['message'],response_data['status'])
            else:
                return invalid_response('invalid_user', "Current user is not a driver user", 204)
        except Exception as e:
            _logger.exception("Error while getting Document types data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while getting Document types data"
            return invalid_response('bad_request', error_msg, 200)

    def _get_shipment_document_detail_data(self, domain, field_list):
        shipment_document = request.env['shipment.document'].sudo()
        document = shipment_document.search_read(domain, field_list)
        if document:
            if request.env.context.get('from_fleet_v2'):
                response_data = self._prepare_response_data(shipment_document, field_list, document)
                for rec in response_data:
                    rec.update({
                        'document_url': "?model=shipment.document&download=false&field=file&filename={}&id={}".format(rec.get('filename'),rec.get('id')),
                    })
            else:
                response_data = self._prepare_response_data(shipment_document, field_list, document)[0]
                response_data.update({
                    'document_url': "?model=shipment.document&download=false&field=file&filename={}&id={}".format(response_data.get('filename'),response_data.get('id')),
                })
            return response_data
        else:
            return  {"response": 'not_found', "message": 'No document found with the given id', 'status': 204}

    @validate_token
    @http.route("/api/v1/fleet/get_shipment_document_detail", methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_document_detail(self, **payload):
        _logger.info("/api/v1/fleet/get_shipment_document_detail: %s", payload)
        try:
            payload_data = payload
            field_list = ['id', 'filename', 'document_type_id', 'description','date', 'write_date',]
            document_id = int(payload_data.get('document_id'))
            shipment_id = payload_data.get('shipment_id')
            shipment_obj =  request.env['shipment.shipment'].sudo().browse(int(shipment_id)) if shipment_id else False
            current_driver_id = self._get_current_driver_id()
            if shipment_obj and shipment_obj.driver_id and shipment_obj.driver_id.id == current_driver_id:
                domain = [('id','=', document_id)]
                response_data = self._get_shipment_document_detail_data(domain,field_list)
                if response_data.get('id'):
                    # T2858 to show document last updated time (write_date) is added in the response
                    # For avoiding instant update in fleet app 'date' key is kept same in the response for the time being 
                    # but updated with the 'write_date'. Later should be updated in the app with 'write_date' key.
                    response_data['date'] = response_data.get('write_date',False)
                    return valid_response(response_data)
                else :
                    return invalid_response(response_data['response'], response_data['message'], 204)
            else:
                app_language = request.httprequest.headers.get('lang')
                # T2750: response type and message change for shipment revoked.
                if app_language == 'es':
                    error_msg ='Este envío ya no está asignado a usted. Será devuelto a la lista de envíos.'
                else:
                    error_msg = "This shipment is no longer assigned to you.You'll be returned to the Shipments list."
                return invalid_response('shipment_revoked', error_msg, 403)
        except Exception as e:
            _logger.exception("Error while getting Document types data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while getting Document types data"
            return invalid_response('bad_request', error_msg, 200)


    def _get_shipment_status_list_data(self, domain, field_list,app_language):
        shipment_status = request.env['shipment.status'].sudo()
        shipment_data = shipment_status.search_read(domain,field_list)
        if shipment_data:
            response_data =  self._prepare_response_data(shipment_status, field_list, shipment_data)
            if response_data:
                for data in response_data:
                    # T2785: changes for fleet offline status list api
                    if request.env.context.get('from_fleet_v2'):
                        # if app_language == 'es':
                        #     data.pop('name',None)
                        #     data.pop('button_name_en',None)
                        # else:
                            # data.pop('name_es',None)
                            # data.pop('button_name_es',None)
                        data.update({'name_en': data.pop('name')})
                    else:
                        if app_language == 'es':
                            data.update({'name': data.get('name_es')})
                            data.pop('name_es',None)
            return response_data
        else:
            return {"response": 'not_found', "message": 'No Shipment Status found.', 'status': 204}

    @validate_token
    @http.route("/api/v1/fleet/get_shipment_status_list", methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_status_list(self, **payload):
        _logger.info("/api/v1/fleet/get_shipment_status_list: %s", payload)
        try:
            payload_data = payload
            field_list = ['id', 'location_tracking', 'sequence']
            app_language = request.httprequest.headers.get('lang')
            if app_language == 'es':
                field_list+=['name_es']
            else:
                field_list+=['name']

            domain = [('is_driver_can_choose','=', True)]
            response_data = self._get_shipment_status_list_data(domain,field_list,app_language)
            if isinstance(response_data, list):
                return valid_response(response_data)
            else:
                return invalid_response(response_data['response'], response_data['message'],response_data['status'])
        except Exception as e:
            _logger.exception("Error while getting Document types data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while getting Document types data"
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/v1/fleet/get_shipment_settings", methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_settings(self, **payload):
        _logger.info("/api/v1/fleet/get_shipment_settings: %s", payload)
        try:
            payload_data = payload
            response_data = {}
            settings_list = [
                'shipment_settings_location_reporting_frequency',
                'shipment_settings_location_timeout_threshold',
                'shipment_settings_image_compression_ratio',
                'shipment_settings_auto_refresh_interval',
                'shipment_settings_geofence_radius',
                'shipment_settings_location_reporting_distance_filter',
            ]
            for rec in settings_list:
                if request.env.ref(f'bista_driver_app.{rec}'):
                    value = request.env.ref(f'bista_driver_app.{rec}').value
                    response_data.update({
                        f'{rec.removeprefix("shipment_settings_")}': value if rec != 'shipment_settings_location_reporting_distance_filter' else value*0.3048,
                    })
            if isinstance(response_data, dict):
                return valid_response(response_data)
            else:
                return invalid_response('not_found', 'No shipping settings found', 204)

        except Exception as e:
            _logger.exception("Error while getting shipment settings data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting shipment settings data.'
            return invalid_response('bad_request', error_msg, 200)

    @staticmethod
    def _get_server_list_data(self,domain):
        driver_app_server = False
        response_data = []
        driver_app_server = request.env['driver.app.server'].sudo().search(domain)
        if driver_app_server:
            for server in driver_app_server:
                response_data.append({
                    'server_name': server.name,
                    'domain': server.server_route,
                    'api_path': server.api_route,
                    'content_path': server.content_route,
                    'webview_path': server.web_route,
                })
            return response_data
        else:
            return {'response': 'not_found','message': 'No server data found', 'status': 204}

    @validate_token
    @http.route("/api/v1/fleet/get_server_lists", methods=["GET"], type="http", auth="none", csrf=False)
    def get_server_list(self, **payload):
        _logger.info("/api/v1/fleet/get_server_lists: %s", payload)
        try:
            payload_data = payload
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            server_url = re.sub(r'^https?://', '', base_url)
            domain = [('server_route', '!=', server_url)]
            response_data = self._get_server_list_data(self,domain)
            if isinstance(response_data, list):
                return valid_response(response_data)
            else:
                return invalid_response(response_data['response'], response_data['message'],response_data['status'])

        except Exception as e:
            _logger.exception("Error while getting server data for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting server data.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/v1/fleet/get_shipment_instructions", methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_instructions(self, **payload):
        """
            Get shipment notes
        """
        _logger.info("/api/v1/fleet/get_shipment_instructions: %s", payload)
        try:
            payload_data = payload
            shipment_id = False
            app_language = request.httprequest.headers.get('lang')
            if app_language == 'es':
                no_notes_msg = "Sin notas"
                no_direction_msg = "Sin indicaciones"
            else:
                no_notes_msg = "No Notes"
                no_direction_msg = "No Directions"
            values = {}
            required_fields = ['type', 'from', 'id']
            missing_fields = [f for f in required_fields if
                              f not in payload_data or payload_data[f] in [None, '', [], {}]]
            if missing_fields:
                return invalid_response('bad_request', 'Required field is missing', 400)
            values.update({'no_breadcrumbs': True})

            if payload_data.get('from') == 'shipment' and int(payload_data['id']):
                shipment_id = request.env['shipment.shipment'].sudo().search_read(
                    [('id', '=', int(payload_data['id']))], [payload_data['type']])
                if not shipment_id:
                    return invalid_response('not_found', 'Shipment not found', 204)
                for shipment in shipment_id:
                    if not shipment.get(payload_data['type']) or shipment.get(payload_data['type']) == '<p><br></p>':
                        shipment[payload_data['type']] = Markup(f'<div style="display: flex; justify-content: center; align-items: center; height: 100vh;"><p style="text-align: center;">{no_notes_msg}</p></div>')
                    elif '/web/image/' in shipment.get(payload_data['type']):
                        shipment[payload_data['type']] = Markup(
                            re.sub(r'(?<=src=")/web/', '/api/web/', shipment.get(payload_data['type'])))
                values.update({'record': shipment_id[0], 'type': payload_data.get('type', False)})

            elif payload_data.get('from') == 'stops' and int(payload_data['id']):
                stops_id = request.env['shipment.stop'].sudo().search_read([('id', '=', int(payload_data['id']))],
                                                                           [payload_data['type']])
                if not stops_id:
                    return invalid_response('not_found', 'Stops not found', 204)
                for stops in stops_id:
                    if not stops.get(payload_data['type']) or stops.get(payload_data['type']) == '<p><br></p>':
                        val = no_direction_msg if payload_data['type'] == 'directions' else no_notes_msg
                        stops[payload_data['type']] = Markup('<div style="display: flex; justify-content: center; align-items: center; height: 100vh;"><p style="text-align: center;">'+val+'</p></div>')
                    elif '/web/image/' in stops.get(payload_data['type']):
                        stops[payload_data['type']] = Markup(
                            re.sub(r'(?<=src=")/web/', '/api/web/', stops.get(payload_data['type'])))
                values.update({'record': stops_id[0], 'type': payload_data.get('type', False)})
            else:
                return invalid_response('bad_request', 'Record ID is required', 400)

            return request.render("bista_driver_app.shipment_instruction_layout", values)

        except Exception as e:
            _logger.exception("Error while getting Shipment instruction for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting Shipment instructions.'
            return invalid_response('bad_request', error_msg, 200)
    

    @validate_token
    @http.route("/api/v1/fleet/get_shipment_pdf_instructions", methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_pdf_instructions(self, **payload):
        """
            Get shipment notes
        """
        _logger.info("/api/v1/fleet/get_shipment_pdf_instructions: %s", payload)
        try:
            payload_data = payload
            shipment_id = False
            values = {}
            # required_fields = ['type', 'from', 'id']
            # missing_fields = [f for f in required_fields if
            #                   f not in payload_data or payload_data[f] in [None, '', [], {}]]
            # if missing_fields:
            #     return invalid_response('bad_request', 'Required field is missing', 400)
            # values.update({'no_breadcrumbs': True})

            # if payload_data.get('from') == 'stops' and int(payload_data['id']):
            #     document_id = request.env['shipment.stop'].sudo().search_read(
            #         [('id', '=', int(payload_data['id']))], [payload_data['type']])
            #     if not document_id:
            #         return invalid_response('not_found', 'Shipment not found', 204)
                
            # else:
            #     return invalid_response('bad_request', 'Record ID is required', 400)
            shipment_stop_rec = request.env['shipment.stop'].sudo().browse(int(payload_data['id']))
            pdf_content, _= request.env['ir.actions.report'].sudo()._render_qweb_pdf('bista_driver_app.action_report_shipment_stop_instruction',
                                                                       shipment_stop_rec.id)
            return request.make_response(pdf_content, headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Length', str(len(pdf_content))),
                ])

        except Exception as e:
            _logger.exception("Error while getting Shipment instruction for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting Shipment instructions.'
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route("/api/v1/fleet/get_shipment_binary_instructions", methods=["GET"], type="http", auth="none", csrf=False)
    def get_shipment_binary_instructions(self, **payload):
        """
            Get shipment notes
        """
        _logger.info("/api/v1/fleet/get_shipment_binary_instructions: %s", payload)
        try:
            payload_data = payload
            shipment_id = False
            app_language = request.httprequest.headers.get('lang')
            if app_language == 'es':
                no_notes_msg = "Sin notas"
                no_direction_msg = "Sin indicaciones"
            else:
                no_notes_msg = "No Notes"
                no_direction_msg = "No Directions"
            values = {}
            values.update({'no_breadcrumbs': True})
            shipment_rec = request.env['shipment.shipment'].sudo().browse(int(payload_data['id']))
            # return valid_response(request.env['ir.actions.report'].sudo()._render_qweb_pdf('bista_driver_app.action_report_shipment_instruction',
            #                                                            shipment_rec.id))
            pdf_data = base64.b64decode(shipment_rec.notes_binary)
            report_content_disposition = content_disposition('Shipment Instruction Binary.pdf')
            return request.make_response(pdf_data, headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Length', str(len(pdf_data))),
                    ('Content-Disposition', report_content_disposition),
                ])
            # return request.env.ref('bista_driver_app.action_report_shipment_instruction').report_action(self)
        except Exception as e:
            _logger.exception("Error while getting Shipment instruction for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while getting Shipment instructions.'
            return invalid_response('bad_request', error_msg, 200)
    
    
    @http.route("/api/v1/fleet/get_fleet_app_public_configuration", methods=["GET"], type="http", auth="none", csrf=False)
    def get_public_url(self, **payload):
        """
            Get Privacy policy and terms and condition page links
        """
        _logger.info("/api/v1/fleet/get_fleet_app_public_configuration")
        try:
            app_language = request.httprequest.headers.get('lang')
            if app_language == 'es':
                privacy_policy_url = request.env.ref('bista_driver_app.shipment_settings_privacy_policy_url').sudo().url_value_es
                terms_and_conditions_url = request.env.ref('bista_driver_app.shipment_settings_terms_and_conditions_url').sudo().url_value_es
            else:
                privacy_policy_url = request.env.ref('bista_driver_app.shipment_settings_privacy_policy_url').sudo().url_value_en
                terms_and_conditions_url = request.env.ref('bista_driver_app.shipment_settings_terms_and_conditions_url').sudo().url_value_en
            
            return valid_response({
                                    'privacy_policy_url': privacy_policy_url if privacy_policy_url else '',
                                    'terms_and_conditions_url': terms_and_conditions_url if terms_and_conditions_url else '',
                                })
        except Exception as e:
            error_msg = 'Error while getting Privacy Policy and Terms and Condition url'
            _logger.exception(error_msg)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            return invalid_response('bad_request', error_msg, 200)

    #######################################
    # POST APIs
    #######################################

    def _post_shipment_status_response_data(self,shipment_id,status_action):
        """
            Update the status of a shipment.
        """
        shipment = request.env['shipment.shipment'].browse(shipment_id).sudo()
        if hasattr(shipment, status_action):
            action = getattr(shipment, status_action)
            if callable(action):
                action()
                return {'message': "Shipment status updated successfully", 'shipment_id': shipment.id}

        return  {"response": 'invalid_action', "message": "Not a valid action", 'status': 400}

    @validate_token
    @http.route("/api/v1/fleet/post_shipment_detail", type="json", auth="none", methods=["POST"], csrf=False)
    def post_shipment_detail(self, **payload):
        """
            
        """
        _logger.info("/api/v1/fleet/post_shipment_detail: %s", payload)
        try:
            payload_data = payload if len(payload) > 0 else json.loads(
                request.httprequest.data.decode())
            shipment_id = payload_data.get('id')
            status_action = payload_data.get('status_action')
            if shipment_id and status_action:
                response_data = self._post_shipment_status_response_data(shipment_id,status_action)
            if not response_data.get('status'):
                return valid_response(response_data)
            else:
                return invalid_response(response_data['response'], response_data['message'], response_data['status'])

        except Exception as e:
            _logger.exception("Error while updating Shipment detail for payload: %s", payload)
            error_msg = 'Error while updating Shipment detail.'
            code = 'bad_request'
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
                if 'POD Document not found' in error_msg:
                    code = 'pod_document_not_found'
            else:
                error_msg = 'Error while updating Shipment detail.'

            return invalid_response(code, error_msg, 400)

    def get_timezone_from_lat_lng(self, latitude, longitude):
        """
            Returns the timezone (e.g., 'America/New_York') from coordinates.
        """
        return TimezoneFinder().timezone_at(lat=latitude, lng=longitude)

    def _post_shipment_live_location_response(self, req_data):
    
        shipment_id = req_data.get('shipment_id')
        shipment_rec = request.env['shipment.shipment'].browse(shipment_id)
        connectivity_status =  req_data.get('connectivity_status')
        carrier_id = False
        company_id = False
        date_recorded = req_data.get('timestamp')
        date_recorded = datetime.fromtimestamp(date_recorded)
        if shipment_rec:
            shipment_rec = shipment_rec.sudo()
            carrier_id = shipment_rec.driver_id
            company_id = shipment_rec.customer_id
            driver_user_id = shipment_rec.driver_id.user_id
    
            if (shipment_rec.driver_id and shipment_rec.driver_id.id != self._get_current_driver_id() and connectivity_status == "online") or (shipment_rec.driver_id == False and connectivity_status == "online"):
                return {"response": 'stop_tracking_service', "message": "The driver was changed", 'status': 400}
            if shipment_rec.status_id.location_tracking == 'disabled' and connectivity_status == "online":
                return {"response": 'stop_tracking_service', "message": "Location tracking is disabled for this shipment", 'status': 400}
    
            # update the shipments latest lat/long based on the latest date_recorded among Fleet app and ELD
            # geolocation_history_latest_rec = request.env['geolocation.history'].sudo().search([('shipment_id','=',shipment_rec.id),
                                                                                            # ('latest','=', True)])
            # if date_recorded and geolocation_history_latest_rec:
            if date_recorded:
                # Driver app
                # if geolocation_history_latest_rec.date_recorded < date_recorded:
                shipment_rec.with_user(driver_user_id).with_context(from_mobile_app = True).sudo().write(
                                                                                        {'latest_latitude':req_data.get('latitude',""),
                                                                                        'latest_longitude':req_data.get('longitude',"")})
        # NOTE: Driver app
        zone_name = self.get_timezone_from_lat_lng(req_data.get('latitude'), req_data.get('longitude'))
        timezone = datetime.fromtimestamp(req_data.get('timestamp'), ZoneInfo(zone_name)).strftime("%Z")
    
        geolocation_history_rec = request.env['geolocation.history'].sudo().create({
                    'source_id': request.env.ref('bista_driver_app.source_driver_phone').id,
                    'reference': f'shipment.shipment,{shipment_id}',
                    'asset_latitude': req_data.get('latitude',""),
                    'asset_longitude': req_data.get('longitude',""),
                    'shipment_id': shipment_id,
                    'approximate_location': req_data.get('accuracy',""),
                    'speed':  req_data.get('speed',""),
                    'date_recorded': date_recorded,
                    'connectivity_status': req_data.get('connectivity_status', ""),
                    'company_id': company_id.id if company_id else False,
                    'carrier_id': carrier_id.id if carrier_id else False,
                    'timezone': timezone,
                    'device_unique_id': req_data.get('device_unique_id',""),
                    'device_info': {
                                    'device_brand': req_data.get('device_brand',""),
                                    'device_model': req_data.get('device_model',""),
                                    'device_os': req_data.get('device_os',""),
                                  }
                })
        if shipment_rec:
            return {'message': "Shipment location updated"}
        else:
            return {"response": 'not_updated', "message": "Can not update shipment location for given data", 'status': 400}

    @validate_token
    @http.route(["/api/v1/fleet/post_shipment_live_location"], type="json", auth="none", methods=["POST"], csrf=False)
    def post_shipment_live_location(self, **payload):
        """
            creates geolocation history for Shipments
        """
        _logger.info("/api/post_shipment_live_location POST payload: %s", payload)
        try:
            req_data = json.loads(request.httprequest.data.decode())
            _logger.info("/api/post_shipment_live_location POST request data: %s", req_data)
            response_data = {}
            response_data = self._post_shipment_live_location_response(req_data)
            if not response_data.get('status'):
                return valid_response(response_data)
            else:
                return invalid_response(response_data['response'], response_data['message'], response_data['status'])
        except Exception as e:
            _logger.exception("Error while updating live location for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = 'Error while updating live location.'
            return invalid_response('bad_request', error_msg, 200)

    def _prepare_create_write_vals(self, payload, fields):
        fields_to_update = [field for field in fields if field in payload]
        vals = {}

        for field in fields_to_update:
            field_data = payload.get(field)
            if field_data:
                vals.update({
                    field: field_data,
                })
        if 'document_type_id' in vals:
            document_type_id = vals.get('document_type_id')
            if document_type_id:
                vals['document_type_id'] = int(document_type_id)

        # if 'description' in payload:
        #     if payload.get('description') == "":
        #         vals['description'] = ""

        return vals

    @staticmethod
    def get_page_size(pdf_reader):
        max_width = max_height = 0
        for page in pdf_reader.pages:
            media_box = page.mediaBox
            width = media_box and media_box.getWidth()
            height = media_box and media_box.getHeight()
            max_width = width if width > max_width else max_width
            max_height = height if height > max_height else max_height

        return (max_width, max_height) if max_width and max_height else None
    
    @staticmethod
    def _convert_to_pdf(document_file):
        """Convert image document file to pdf
            Returns the following data::
            - pdf_bytes
            - is_image_document flag"""
        try:
            img = Image.open(io.BytesIO(document_file))
            pdf_bytes = io.BytesIO()

            # Handle multiple frames (e.g. multi-page TIFF)
            if getattr(img, "n_frames", 1) > 1:
                imgs = []
                for i in range(img.n_frames):
                    img.seek(i)
                    imgs.append(img.convert("RGB"))
                imgs[0].save(pdf_bytes, format="PDF", save_all=True, append_images=imgs[1:])
            else:
                img.convert("RGB").save(pdf_bytes, format="PDF")

            pdf_bytes.seek(0)
            return pdf_bytes.read(), True
        except Exception as e:
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while converting to pdf"
            _logger.exception("Error while converting to pdf: %s", error_msg)
            return False, False

    def _update_shipment_document_signature(self, document_file, document_signature_bytes, signed_by, signed_on_time_str):
        """
            Here signature of the pdf document is updated.

        """
        is_image_document = False
        try:
            if document_file and document_signature_bytes:
                # Decode original PDF file
                document_file = base64.b64decode(document_file)
                file_header = document_file[:4]
                is_pdf = file_header.startswith(b"%PDF")
                if not is_pdf:
                    document_file, is_image_document = self._convert_to_pdf(document_file)

                old_document_file = PdfFileReader(io.BytesIO(document_file), strict=True)
                # Prepare overlay canvas
                packet = io.BytesIO()
                # page_width, page_height = self.get_page_size(old_document_file) 
                page_width, page_height = A4 if is_image_document else self.get_page_size(old_document_file)
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))

                # Currently signature image is considered 20% of the pdf document. signature image dimension found from the app is h:w = 2:1  
                if page_width >= page_height:
                    sig_width = int(page_width/5)
                    sig_height = int(sig_width/2)
                    can.setFont("Helvetica", 10)
                else:
                    sig_height = int(page_height/5)
                    sig_width = sig_height*2
                    can.setFont("Helvetica", 15)
                # Compute position — bottom middle
                x = int((page_width - sig_width) / 2)
                y = 35  # 40 pts from bottom edge

                # Draw text above signature
                
                can.setFillColorRGB(0, 0, 0)  # black color
                can.drawCentredString(x + sig_width / 2, y + sig_height + 8, f"Signed by {signed_by} on {signed_on_time_str}")
                # Draw image on canvas
                signature_img = ImageReader(io.BytesIO(document_signature_bytes))
                can.drawImage(signature_img, x, y, width=sig_width, height=sig_height, mask='auto')
                can.save()

                # Merge overlay into the original PDF
                packet.seek(0)
                new_pdf = PdfFileReader(packet)
                output = PdfFileWriter()

                a4_width, a4_height = A4
                for page_num in range(old_document_file.getNumPages()):
                    page = old_document_file.getPage(page_num)
                    if is_image_document:
                        # convert the pdf to A4 size
                        # Get original page size
                        page_width = float(page.mediaBox[2] - page.mediaBox[0])
                        page_height = float(page.mediaBox[3] - page.mediaBox[1])

                        # Scale to A4
                        scale = min(a4_width / page_width, a4_height / page_height)
                        tx = (a4_width - page_width * scale) / 2
                        ty = (a4_height - page_height * scale) / 2

                        page.scale(scale, scale)
                        page.addTransformation([1, 0, 0, 1, tx, ty])

                        # Reset mediaBox to A4
                        page.mediaBox.lowerLeft = (0, 0)
                        page.mediaBox.upperRight = (a4_width, a4_height)

                        # Recalculate signature for resized page
                        page_width, page_height = a4_width, a4_height 
                        # if page_width >= page_height:
                        sig_width = int(page_width / 5)
                        sig_height = int(sig_width / 2)
                        can.setFont("Helvetica", 10)
                        # else:
                        #     sig_height = int(page_height / 5)
                        #     sig_width = sig_height * 2
                        #     can.setFont("Helvetica", 15)
                        x = int((page_width - sig_width) / 2)
                        y = 35

                        # Recreate overlay canvas for this resized page
                        packet_page = io.BytesIO()
                        can_page = canvas.Canvas(packet_page, pagesize=(page_width, page_height))
                        can_page.setFillColorRGB(0, 0, 0)
                        can_page.drawCentredString(x + sig_width / 2, y + sig_height + 8,
                                                f"Signed by {signed_by} on {signed_on_time_str}")
                        can_page.drawImage(signature_img, x, y, width=sig_width, height=sig_height, mask='auto')
                        can_page.save()
                        packet_page.seek(0)
                        overlay_pdf = PdfFileReader(packet_page)
                        page.mergePage(overlay_pdf.getPage(0))
                    # Uncomment next line to apply only on last page:
                    # if page_num == old_document_file.getNumPages() - 1:
                    else:
                        page.mergePage(new_pdf.getPage(0))
                    output.addPage(page)

                # Write merged PDF to memory
                output_stream = io.BytesIO()
                output.write(output_stream)
                output_stream.seek(0)

                # Encode to base64 and update record
                signed_pdf_b64 = base64.b64encode(output_stream.read()).decode()

                return {
                        'file': signed_pdf_b64,
                        'is_signature': True,
                        }, is_image_document
            else:
                return {}, is_image_document
        except Exception as e:
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while uploading document"
            _logger.exception("Error while updating document signature: %s", error_msg)
            return {'is_signature': True,}, is_image_document

    @validate_token
    @http.route(["/api/v1/fleet/upload_shipment_document"], type="http", auth="none", methods=["POST"], csrf=False)
    def upload_shipment_document(self, **payload):
        _logger.info("/api/v1/fleet/upload_shipment_document POST payload: %s", payload)
        try:
            shipment_id = payload.get('shipment_id', False)
            document_file = payload.get('document', False) # FileStorage object
            filename = payload.get('filename', "")
            document_file_base64 = base64.b64encode(document_file.read()) if document_file else None
            date_timestamp = payload.get('date')
            id = int(payload.get('id')) if payload.get('id') else False
            # sign data
            document_signature = payload.get('document_signature', False)
            document_signature_bytes = document_signature.read() if document_signature else None
            document_signature_base64 = base64.b64encode(document_signature_bytes) if document_signature_bytes else None
            signed_by =  payload.get('signed_by', False)
            # signed_on_timestamp = int(payload.get("signed_on_timestamp")) if payload.get("signed_on_timestamp") else False
            signed_on_time_str = payload.get("signed_on_time_str", False)
            # signed_on_timezone_offset = payload.get("signed_on_timezone_offset", False) 
            signature_time_data = {
                'signed_on_timestamp': int(payload.get("signed_on_timestamp")) if payload.get("signed_on_timestamp") else False,
                'signed_on_time_str': signed_on_time_str,
                'signed_on_timezone_offset': payload.get("signed_on_timezone_offset", False),
            }

            shipment_obj =  request.env['shipment.shipment'].sudo().browse(int(shipment_id)) if shipment_id else False
            current_driver_id = self._get_current_driver_id()
            if shipment_obj and shipment_obj.driver_id and shipment_obj.driver_id.id == current_driver_id:
                date = False
                if date_timestamp:
                    date = datetime.fromtimestamp(int(date_timestamp)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                # shipment_shipment = request.env['shipment.shipment'].sudo()
                shipment_document = request.env['shipment.document'].sudo()

                if id:
                    document_id = shipment_document.browse(id)
                    vals = self._prepare_create_write_vals(payload, ['document_type_id', 'description'])
                    if document_signature:
                        if document_id.is_signature:
                            document_file = document_id.original_file
                        else:
                            document_file = document_id.file
                            # in original_file field initial document is kept for future signature update
                            vals.update({'original_file': document_file})
                        signature_data, is_image_document = self._update_shipment_document_signature(document_file, document_signature_bytes, signed_by, signed_on_time_str)
                        
                        if is_image_document:
                            # update file name extension after converting to pdf
                            filename = document_id.filename
                            name, ext = os.path.splitext(filename)
                            if ext.lower() != ".pdf":
                                filename = f"{name}.pdf"
                                vals.update({'filename': filename,})

                        vals.update({**signature_data, 
                                    'document_signature':document_signature_base64, 
                                    'signature_time_data': signature_time_data,
                                    'signed_by': signed_by })
                    document_id.write(vals)
                    return valid_response({
                        'message': "Document updated successfully",
                        'document_id': id,
                    })
                    
                if not document_file_base64:
                    return invalid_response('bad_request', "Document not found", 200)

                
                ### Dependency Remover ( work of
                document_type_id = payload.get('document_type_id', False)
                # NOTE: comment this block later if don't want to assign POD as default document_type_id
                if not document_type_id:
                    document_type_id = request.env.ref('bista_driver_app.driver_document_type_pod_fleet').id
                # T2843:document type to integer and shipment_id in vals
                vals = {
                    'document_type_id': int(document_type_id),
                    'file': document_file_base64,
                    'filename': filename,
                    'description': payload.get('description', ""),
                    'date': date if date else datetime.now(),
                    'shipment_id':shipment_obj.id,
                }
                if document_signature:
                        signature_data, is_image_document = self._update_shipment_document_signature(document_file_base64, document_signature_bytes, signed_by, signed_on_time_str)
                        if signature_data:
                            if is_image_document:
                                name, ext = os.path.splitext(filename)
                                if ext.lower() != ".pdf":
                                    filename = f"{name}.pdf"
                                    vals.update({'filename': filename,})
                            # in original_file field initial document is kept for future signature update
                            vals.update({**signature_data, 
                                        'original_file': document_file_base64, 
                                        'document_signature':document_signature_base64, 
                                        'signature_time_data': signature_time_data,
                                        'signed_by': signed_by })
                
                document_id = shipment_document.create(vals)

                # if shipment_obj:
                # shipment_obj.write({
                #     'document_ids': [(4, document_id.id, 0)]
                # })
                return valid_response({
                    'message': "Document uploaded successfully",
                    'document_id': document_id.id
                })
                # else:
                #     error_msg = "Shipment record not found."
                #     return invalid_response('bad_request', error_msg, 200)
            else:
                app_language = request.httprequest.headers.get('lang')
                # T2750: response type and message change for shipment revoked.
                if app_language == 'es':
                    error_msg ='Este envío ya no está asignado a usted. Será devuelto a la lista de envíos.'
                else:
                    error_msg = "This shipment is no longer assigned to you.You'll be returned to the Shipments list."
                return invalid_response('shipment_revoked', error_msg, 403)
        except Exception as e:
            _logger.exception("Error while uploading document for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while uploading document"
            return invalid_response('bad_request', error_msg, 200)


    @validate_token
    @http.route(["/api/v1/fleet/post_change_shipment_status"], type="http", auth="none", methods=["POST"], csrf=False)
    def post_change_shipment_status(self, **payload):
        _logger.info("/api/v1/fleet/post_change_shipment_status POST payload: %s", payload)
        try:
            req_data = json.loads(request.httprequest.data.decode())
            _logger.info("/api/v1/fleet/post_change_shipment_status POST request data: %s", req_data)
            shipment_id = int(req_data.get('shipment_id', False))
            status_id = req_data.get('status_id', False)
            is_move_to_next = req_data.get('is_move_to_next',False)
            next_status_search_domain = []
            shipment_rec = request.env['shipment.shipment'].sudo().browse(shipment_id)

            current_driver_id = self._get_current_driver_id()
            if shipment_rec and shipment_rec.driver_id and shipment_rec.driver_id.id == current_driver_id:
                if is_move_to_next:
                    current_status_sequence = shipment_rec.status_id.sequence
                    next_status_search_domain = [('sequence','=', current_status_sequence+1)]
                    _logger.info(f"'/api/v1/fleet/post_change_shipment_status' - is_move_to_next: {is_move_to_next}, shipment_rec: {shipment_rec}, shipment status: {shipment_rec.status_id}, current_status_sequence: {current_status_sequence}, next_status_search_domain: {next_status_search_domain}")
                elif status_id:
                    next_status_search_domain = [('id','=',int(status_id))]

                is_driver_can_choose = False
                location_tracking = False
                is_completed = False
                next_status_data = request.env['shipment.status'].sudo().search_read(next_status_search_domain,['is_driver_can_choose', 'location_tracking','is_completed','status_action'])
                if next_status_data:
                    next_status_data = next_status_data[0]
                    status_id = next_status_data.get('id')
                    is_driver_can_choose = next_status_data.get('is_driver_can_choose', False)
                    location_tracking = next_status_data.get('location_tracking')
                    is_completed = next_status_data.get('is_completed')
                _logger.info(f"'/api/v1/fleet/post_change_shipment_status' shipment_rec: {shipment_rec} & is_driver_can_choose: {is_driver_can_choose} & status_id: {status_id} & is_completed: {is_completed} & next_status_data: {next_status_data}")
                if shipment_rec and is_driver_can_choose:
                    shipment_rec = shipment_rec.with_context(from_mobile_app=True)
                    if is_completed:
                        if not shipment_rec.document_ids:
                            return invalid_response('document_not_found', 'Upload the mandatory document for your shipment to complete Delivery.', 400)
                    if request.env.ref('bista_driver_app.shipment_status_at_pickup').id == int(status_id):
                        shipment_rec.action_set_at_pickup()
                    elif request.env.ref('bista_driver_app.shipment_status_in_transit').id == int(status_id):
                        shipment_rec.action_set_in_transit()
                    elif request.env.ref('bista_driver_app.shipment_status_at_delivery').id == int(status_id):
                        shipment_rec.action_set_at_delivery()
                    elif request.env.ref('bista_driver_app.shipment_status_delivered').id == int(status_id):
                        shipment_rec.action_set_delivered()
                    elif request.env.ref('bista_driver_app.shipment_status_accepted').id == int(status_id):
                        shipment_rec.action_set_accepted()
                    # elif request.env.ref('bista_driver_app.shipment_status_cancelled').id == int(status_id):
                    #     shipment_rec.action_set_cancelled()
                    # else:
                    #     shipment_rec.sudo().write({'status_id': status_id})
                    # shipment_rec.sudo().write({'status_id': status_id})
                    # shipment_rec.driver_id.sudo().write({
                    #                                     "is_continuous_location_tracking": True if location_tracking == 'enabled' else False,
                    #                                     "current_shipment_id": shipment_rec.id
                    #                                     })
                    return valid_response({'message': "Shipment Status updated"})
                else:
                    return invalid_response('not_updated', 'Can not update shipment status', 200)
            else:
                app_language = request.httprequest.headers.get('lang')
                # T2750: response type and message change for shipment revoked.
                if app_language == 'es':
                    error_msg ='Este envío ya no está asignado a usted. Será devuelto a la lista de envíos.'
                else:
                    error_msg = "This shipment is no longer assigned to you.You'll be returned to the Shipments list."
                return invalid_response('shipment_revoked', error_msg, 403)
        except Exception as e:
            _logger.exception("Error while updating Shipment detail for payload: %s", payload)
            error_msg = 'Error while updating Shipment detail.'
            code = 'bad_request'
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
                if 'Upload the mandatory document for your shipment' in error_msg:
                    code = 'document_not_found'
            else:
                error_msg = 'Error while updating Shipment detail.'
            return invalid_response(code, error_msg, 400)


    @validate_token
    @http.route(["/api/v1/fleet/post_delete_shipment_document"], type="http", auth="none", methods=["POST"], csrf=False)
    def post_delete_shipment_document(self, **payload):
        _logger.info("/api/v1/fleet/post_delete_shipment_document POST payload: %s", payload)
        try:
            req_data = json.loads(request.httprequest.data.decode())
            document_id = int(req_data.get('document_id'))
            document_rec = request.env['shipment.document'].browse(document_id)

            if document_rec.exists():
                document_rec.sudo().unlink()
                return valid_response({
                    'message': "Document deleted successfully",
                })
            else:
                error_msg = "Document record not found."
                return invalid_response('bad_request', error_msg, 200)
        except Exception as e:
            _logger.exception("Error while deleting shipment document for payload: %s", payload)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while deleting shipment document."
            return invalid_response('bad_request', error_msg, 200)

    @validate_token
    @http.route(["/api/v1/fleet/post_shipment_tracking_status"], type="http", auth="none", methods=["POST"], csrf=False)
    def post_shipment_tracking_status(self, **payload):
        """
            Show the change in location tracking status in the log.
        """
        _logger.info("/api/v1/fleet/post_shipment_tracking_status POST payload: %s", payload)
        try:
            req_data = json.loads(request.httprequest.data.decode())
            _logger.info("/api/v1/fleet/post_shipment_tracking_status POST request data: %s", req_data)

            driver_id = self._get_current_driver_id()
            required_fields = ['shipment_id', 'tracking_status']
            missing_fields = [f for f in required_fields if f not in req_data or req_data[f] in [None, '', [], {}]]
            if missing_fields:
                return invalid_response('bad_request', 'Required field is missing', 400)
            shipment_rec = request.env['shipment.shipment'].sudo().browse(int(req_data.get('shipment_id')))
            if shipment_rec.exists() and shipment_rec.driver_id and int(shipment_rec.driver_id.id) == int(driver_id):
                if shipment_rec.is_valid_status_action():
                    tracking_status = req_data.get('tracking_status')
                    shipment_rec.sudo().write({'tracking_status': tracking_status})
                    shipment_rec.driver_id.sudo().write(
                        {'is_continuous_location_tracking': False if tracking_status in ['inactive', 'paused'] else True,
                         'is_from_logout': req_data.get('is_from_logout')})
                    return valid_response({
                        'message': "Shipment tracking Status updated in the log",
                    })
            else:
                app_language = request.httprequest.headers.get('lang')
                # T2750: response type and message change for shipment revoked.
                if app_language == 'es':
                    error_msg ='Este envío ya no está asignado a usted. Será devuelto a la lista de envíos.'
                else:
                    error_msg = "This shipment is no longer assigned to you.You'll be returned to the Shipments list."
                return invalid_response('shipment_revoked', error_msg, 403)
        except Exception as e:
            _logger.exception("Error while updating shipment tracking status in the log: %s", req_data)
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while updating shipment tracking status in the log."
            return invalid_response('bad_request', error_msg, 200)
    
    
    @validate_token
    @http.route(["/api/v1/fleet/post_location_service_status_timeline"], type="http", auth="none", methods=["POST"], csrf=False)
    def post_location_service_status(self, **payload):
        """
            Update Shipment Timeline for change in location service status(on/off).
        """
        _logger.info("/api/v1/fleet/post_location_service_status_timeline POST payload: %s", payload)
        try:
            req_data = json.loads(request.httprequest.data.decode())
            _logger.info("/api/v1/fleet/post_location_service_status_timeline POST request data: %s", req_data)

            location_service_status = req_data.get('location_service_status')
            reason = req_data.get('reason',False)

            driver_id = self._get_current_driver_id()
            shipment_rec = request.env['shipment.shipment'].sudo().search([('driver_id','=',driver_id),('location_tracking','=','enabled')], limit=1)

            if shipment_rec.exists():
                msg = ''
                if reason:
                    msg = f'Location Service turned off by the user (Reason: {reason}).'
                else:
                    msg = 'Location Service turned on by the user.'

                timeline_record = request.env['shipment.timeline'].sudo().create({
                                                                    'name': msg,
                                                                    'datetime': fields.Datetime.now(), 
                                                                    'user_id': request.env.user.id,
                                                                    'user_name': request.env.user.name,
                                                                    'driver_id': driver_id if driver_id else False,
                                                                    # 'source_id': request.env.ref('bista_driver_app.source_driver_phone').id, (geolocation.source is not Present)
                                                                    'shipment_id': shipment_rec.id,
                                                                })
                if timeline_record:
                    return valid_response({
                        'message': "Shipment Timeline created.",
                    })
                else:
                    return invalid_response('bad_request', 'Could not create Shipment Timeline', 200)
        
        except Exception as e:
            _logger.exception("Error while updating Shipment Timeline for change in location service status(on/off)")
            err = _serialize_exception(e)
            if err.get('message'):
                error_msg = err.get('message')
            else:
                error_msg = "Error while updating Shipment Timeline for change in location service status(on/off)"
            return invalid_response('bad_request', error_msg, 200)
