import json
import werkzeug.wrappers
from reportlab.lib.pagesizes import elevenSeventeen

from odoo import fields, models, api

import logging
import datetime
import collections
import collections.abc

import os
# from twilio.rest import Client
# from odoo.tools import date_utils
from odoo.tools import json_default
# from odoo.http import JsonRequest, Response
from odoo.http import JsonRPCDispatcher, Response, request
from odoo.http import request, content_disposition, serialize_exception, SessionExpiredException
from werkzeug.exceptions import NotFound

_logger = logging.getLogger(__name__)


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, bytes):
        return str(o)


def valid_response(data, status=200):
    """Valid Response
    This will be return when the http request was successfully processed."""
    data = {
        "count": len(data) if not isinstance(data, str) else 1,
        "status": True if status else False,
        "data": data
    }
    return werkzeug.wrappers.Response(
        status=status, content_type="application/json; charset=utf-8", response=json.dumps(data, default=default),
    )


def invalid_response(typ, message=None, status=200):
    """Invalid Response

    This will be the return value whenever the server runs into an error
    either from the client or the server.

    :param str typ: type of error,
    :param str message: message that will be displayed to the user,
    :param int status: integer HTTP status code that will be sent in response body & header.
    """
    # return json.dumps({})
    return werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps(
            {
                "code": status,
                "type": typ,
                "message": str(message) if str(message) else "wrong arguments (missing validation)",
                "status": False
            },
            default=datetime.datetime.isoformat,
        ),
    )


def _response(self, result=None, error=None):
    response = {
        'jsonrpc': '2.0',
        'id': self.jsonrequest.get('id')
    }
    if error is not None:
        # if self.jsonrequest.get('mobile_app',False):
        #     response.update(error)
        response['error'] = error
    if result is not None:
        # Start of customization
        if isinstance(result, werkzeug.wrappers.Response):
            return result
        try:
            rest_result = json.loads(result)
            if isinstance(rest_result, dict) and 'rest_api_flag' in rest_result and rest_result.get('rest_api_flag'):
                response.update(rest_result)
                response['result'] = None
            else:
                response['result'] = result
        except Exception as e:
            response['result'] = result
        # End of customization
        # response['result'] = result

    mime = 'application/json'
    # NOTE MIGRATION v17 to v18: adjust import
    # body = json.dumps(response, default=date_utils.json_default)
    body = json.dumps(response, default=json_default)

    return Response(
        body, status=error and error.pop('http_status', 200) or 200,
        headers=[('Content-Type', mime), ('Content-Length', len(body))]
    )


setattr(JsonRPCDispatcher, '_response', _response)  # overwrite the method


def handle_error(self, exc: Exception) -> collections.abc.Callable:
    """
    Handle any exception that occurred while dispatching a request to
    a `type='json'` route. Also handle exceptions that occurred when
    no route matched the request path, that no fallback page could
    be delivered and that the request ``Content-Type`` was json.

    :param exc: the exception that occurred.
    :returns: a WSGI application
    """
    if self.jsonrequest.get('mobile_app'):
        data = serialize_exception(exc)
        error_msg = data.get('message')

        if '\n' in error_msg:
            error_msg = error_msg.replace('\n', '')
        return werkzeug.wrappers.Response(
            status=400,
            content_type="application/json; charset=utf-8",
            response=json.dumps(
                {
                    "code": 400,
                    "message": str(error_msg) if str(error_msg) else "Unknown error occurred.",
                    "status": False
                },
                default=datetime.datetime.isoformat,
            ),
        )

    error = {
        'code': 200,  # this code is the JSON-RPC level code, it is
        # distinct from the HTTP status code. This
        # code is ignored and the value 200 (while
        # misleading) is totally arbitrary.
        'message': "Odoo Server Error",
        'data': serialize_exception(exc),
    }
    if isinstance(exc, NotFound):
        error['code'] = 404
        error['message'] = "404: Not Found"
    elif isinstance(exc, SessionExpiredException):
        error['code'] = 100
        error['message'] = "Odoo Session Expired"

    return self._response(error=error)


setattr(JsonRPCDispatcher, 'handle_error', handle_error)


def convert_data_str(data):
    # Convert any data that is NOT [str, dictionary, array, tuple or bool] TO str
    if type(data) not in [str, dict, list, tuple, bool]:
        data = str(data)

    # Convert dictionary values that are NOT str TO str
    elif isinstance(data, dict):
        for key in data:
            if not isinstance(data[key], str) and not isinstance(data[key], list):
                data[key] = str(data[key])

            if isinstance(data[key], list):
                for index, elem in enumerate(data[key]):
                    if not isinstance(elem, str):
                        data[key][index] = str(elem)

    # Convert list elements that are NOT str TO str
    elif isinstance(data, list):
        for index, elem in enumerate(data):
            if not isinstance(elem, str):
                data[index] = str(elem)

    return data

# # T2493: verify driver twilio phone for sending sms
# def verify_driver_phone(self,driver):
#     twilio_account = self.env['twilio.account'].sudo().search([('state', '=', 'confirm')], limit=1)
#     driver_login = driver.get('driver_login') if isinstance(driver,dict) else driver.driver_login
#     if twilio_account and driver_login:
#         client = Client(twilio_account.account_sid, twilio_account.auth_token)
#         verification_response = client.lookups.v2.phone_numbers(f"+1{driver_login}").fetch()
#         if verification_response:
#             if isinstance(driver,dict):
#                 driver.update({'is_valid_phone': True if verification_response.valid else False})
#             else:
#                 driver.is_valid_phone = True if verification_response.valid else False
