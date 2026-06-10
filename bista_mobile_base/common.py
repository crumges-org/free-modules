import json
import werkzeug.wrappers
import datetime
import functools
from odoo.http import JsonRPCDispatcher, request


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, bytes):
        return str(o)


def valid_response(data, status=200):
    """Valid Response
    This will be return when the http request was successfully processed."""
    data = {"count": len(data) if not isinstance(data, str) else 1, "status": True, "data": data}
    return werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps(data, default=default),
    )


def invalid_response(typ, message=None, status=200):
    """Invalid Response

    This will be the return value whenever the server runs into an error
    either from the client or the server.

    :param str typ: type of error,
    :param str message: message that will be displayed to the user,
    :param int status: integer HTTP status code that will be sent in response body & header.
    """
    response_status = False
   
    return werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps(
            {
                "code": status,
                "type": typ,
                "message": str(message) if str(message) else "wrong arguments (missing validation)",
                "status": response_status,
            },
            default=datetime.datetime.isoformat,
        ),
    )

def _response(self, result=None, error=None):
    response = {"jsonrpc": "2.0", "id": self.request_id}
    if error is not None:
        response["error"] = error
    if result is not None:
        # Start of customization
        if isinstance(result, werkzeug.wrappers.Response):
            return result
        try:
            rest_result = json.loads(result)
            if (
                isinstance(rest_result, dict)
                and "rest_api_flag" in rest_result
                and rest_result.get("rest_api_flag")
            ):
                response.update(rest_result)
                response["result"] = None
            else:
                response["result"] = result
        except Exception as e:
            response["result"] = result
        # End of customization
        # response['result'] = result

    return self.request.make_json_response(response)


setattr(JsonRPCDispatcher, "_response", _response)  # overwrite the method

def validate_token(func):
    """Token validation decorator."""

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        """Validate access token and update user session."""
        request_access_token = request.httprequest.headers.get("access_token") or kwargs.get("access_token")
        if not request_access_token:
            return invalid_response("invalid_token", "invalid access token", 401)

        access_token = request_access_token.split(",")[0]
        if not access_token:
            return invalid_response("access_token_not_found", "missing access token in request header", 200)
        access_token_data = (
            request.env["api.access_token"]
            .sudo()
            .search([("access_token", "=", access_token)], order="id DESC", limit=1)
        )
        if access_token_data:
            if datetime.datetime.now() > access_token_data.access_token_expires:
                return invalid_response("access_token_expired", "token seems to have expired", 401)
        else:
            return invalid_response("invalid_token", "invalid access token", 401)

        request.session.update(user=access_token_data.user_id.id)
        request.update_env(user=access_token_data.user_id.id)

        _validate_token_extension(access_token_data)

        return func(self, *args, **kwargs)

    return wrap

def _validate_token_extension(token_id):
    pass
