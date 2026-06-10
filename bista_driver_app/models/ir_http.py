# -*- coding: utf-8 -*-
import json
from odoo.http import Response, serialize_exception as _serialize_exception
import json
from odoo import models,api,SUPERUSER_ID
from odoo.http import request
from datetime import datetime
from odoo import tools, sql_db
import logging
import threading
import contextlib


_logger = logging.getLogger(__name__)



# _logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    
    @classmethod
    def _handle_error(cls, exception):
        """
            While new Driver user creation, if duplucate phone number is used then update the
            validation error message.
        """
        response = super()._handle_error(exception)
        try:
            http_request_data = {}
            if request and getattr(request, 'httprequest', None):
                raw_data = getattr(request.httprequest, 'data', None)
                if raw_data:
                    http_request_data = json.loads(raw_data)
            params = http_request_data.get('params',{})
            if params.get('model') == 'fleet.driver':
                if isinstance(response, Response) and response.mimetype == 'application/json':
                    if response.response:
                        response_content = response.response[0].decode('utf-8')
                        json_response = json.loads(response_content)
                        if json_response.get('error',{}) and json_response.get('error',{}).get('data') and json_response.get('error',{}).get('data',{}).get('arguments'):
                            arguments = json_response['error']['data']['arguments'][0]
                            if arguments == 'The operation cannot be completed: You can not have two users with the same login!':
                                json_response['error']['data']['arguments'][0] = 'The operation cannot be completed: You can not have two users with the same phone number!'
                                response.set_data(json.dumps(json_response).encode('utf-8'))
        except Exception as e:
            err = _serialize_exception(e)
            _logger.error(err)
            return response
            
        return response

    @classmethod
    def _dispatch(cls, endpoint):
        response = super()._dispatch(endpoint)

        # Check if the request method is POST
        if request.httprequest.method == 'POST':
            json_data = cls._get_json_data()

            if json_data:
                flag = cls._process_json_data(json_data)
                if flag:
                    return response

        # Perform database operations
        cls._update_last_activity()
        try:
            if endpoint and endpoint.routing:
                api_route = endpoint.routing.get('routes', '')[0]
                if api_route.startswith('/api/v1/') and response.mimetype and response.mimetype != 'application/pdf':
                    _logger.info(f"In _dispatch: \n response:{response.response}")
        except:
            return response
        return response

    @classmethod
    def _get_json_data(cls):
        try:
            return json.loads(request.httprequest.data)
        except json.JSONDecodeError:
            return None


    @classmethod
    def _process_json_data(cls, json_data):
        try:
            # ✅ Handle list of dicts safely (your earlier need)
            if isinstance(json_data, list) and json_data:
                json_data = json_data[0]

            params = json_data.get('params', {})
            model = params.get('model')
            method = params.get('method')

            # 🔹 Your custom logic
            if model == 'sale.order' and method == 'web_search_read':
                return False  # block or change behavior


        except Exception as e:
            tools.logger.error("Error processing JSON data: %s", e)
        return False

    @classmethod
    def _update_last_activity(cls):
        ct = threading.current_thread()
        ct_db = getattr(ct, 'dbname', None)
        dbname = tools.config['log_db'] if tools.config['log_db'] and tools.config['log_db'] != '%d' else ct_db
        if not dbname or not request.session.uid:
            return

        try:
            with contextlib.suppress(Exception), tools.mute_logger('odoo.sql_db'), sql_db.db_connect(dbname,
                                                                                                     allow_uri=True).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    with env.cr.savepoint():
                        user_id = env["res.users"].browse(request.session.uid)
                        if user_id and user_id.last_activity != datetime.now().date():
                            user_id.write({
                                'last_activity':datetime.now()
                            })

        except Exception as e:
            tools.logger.error("Error updating last activity: %s", e)