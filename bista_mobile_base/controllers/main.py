# -*- coding: utf-8 -*-
import json
import logging
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request
from odoo.addons.bista_mobile_base.common import (
    invalid_response,
    valid_response,
)
from datetime import datetime, timezone, timedelta
from odoo import fields, http
import werkzeug.wrappers

_logger = logging.getLogger(__name__)


class BistaBaseApi(http.Controller):
    """Bista Base APIs"""


    @http.route(
        "/api/v1/auth/login", methods=["POST"], type="json", auth="none", csrf=False
    )
    def auth_login(self, **post):
        """The token URL to be used for getting the access_token and refresh token.

        str post[db]: db of the system, in which the user logs in to.

        str post[login]: username of the user

        str post[password]: password of the user

        :param list[str] str post: **post must contain db, login and password.
        :returns: https response
            if failed error message in the body in json format and
            if successful user's details with the access_token.
        """
        Token = request.env["api.access_token"]
        params = ["db", "login", "password", "scope"]
        req_data = json.loads(
            request.httprequest.data.decode()
        )  # convert the bytes format to dict format
        req_params = {key: req_data.get(key) for key in params if req_data.get(key)}
        db, username, password = (
            req_params.get("db") if req_params.get("db") else request.env.cr.dbname,
            req_params.get("login"),
            req_params.get("password"),
        )
        _credentials_includes_in_body = all([db, username, password])
        if not _credentials_includes_in_body:
            # The request post body is empty the credentials maybe passed via the headers.
            headers = request.httprequest.headers
            db = headers.get("db") if headers.get("db") else request.env.cr.dbname
            username = headers.get("login")
            password = headers.get("password")
            _credentials_includes_in_headers = all([db, username, password])
            if not _credentials_includes_in_headers:
                # Empty 'db' or 'username' or 'password:
                return invalid_response(
                    "missing error",
                    "Either of the following are missing [db, username,password]",
                    200,
                )
        # Login in odoo database:
        session_info = []
        try:
            request.session.authenticate(
                db, {"login": username, "password": password, "type": "password"}
            )
            session_info = (
                request.env["ir.http"].session_info().get("server_version_info", [])
            )
        except AccessError as aee:
            return invalid_response("Access error", "Error: %s" % aee.name)
        except AccessDenied as ade:
            return invalid_response("Access denied", "Login, password or db invalid")
        except Exception as e:
            # Invalid database:
            info = "The database name is not valid {}".format(e)
            error = "invalid_database"
            _logger.error(info)
            return invalid_response(typ=error, message=info, status=200)

        uid = request.session.uid
        # odoo login failed:
        if not uid:
            info = "authentication failed"
            error = "authentication failed"
            _logger.error(info)
            return invalid_response(status=200, typ=error, message=info)

        # NOTE: Add scope allow multiple app
        # Generate tokens
        # access_token, refresh_token = Token._find_one_or_create_token(
        #     user_id=uid, create=True, refresh_token_obj=False
        # )
        access_token, refresh_token = Token._find_one_or_create_token(
            user_id=uid, create=True, refresh_token_obj=False, scope=req_params.get("scope")
        )
        user_id = request.env.user
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": {
                "id": user_id.id,
                "name": user_id.name,
            },
        }
        # response_data = self.auth_login_response_data(data)
        response_data = {
            **{
                "status": True,
                "count": len(data) if not isinstance(data, str) else 1,
            },
            **data,
        }
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(response_data),
        )

    @http.route(
        "/api/v1/get_access_token",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    def get_access_token(self, **payload):
        """
            Gets Refresh token from request and
            returns corresponding access token.
        """
        _logger.info("/api/v1/get_access_token payload: %s", payload)

        try:
            payload_data = payload
            Token = request.env["api.access_token"].sudo()
            if "refresh_token" in payload_data and payload_data["refresh_token"]:
                token_id = Token.search(
                    [("refresh_token", "=", payload["refresh_token"])]
                )
                if token_id:
                    if datetime.now() > fields.Datetime.from_string(
                        token_id.refresh_token_expires
                    ):
                        return invalid_response(
                            "data_expires", "refresh token expires", 401
                        )
                    elif (
                        not token_id.access_token
                        or datetime.now()
                        > fields.Datetime.from_string(token_id.access_token_expires)
                    ):
                        uid = request.session.uid
                        access_token, refresh_token = (
                            Token._find_one_or_create_token(
                                user_id=uid, create=True, refresh_token_obj=token_id
                            )
                        )
                        return valid_response({"access_token": access_token})
                    else:
                        return valid_response({"access_token": token_id.access_token})
                else:
                    return invalid_response("not_found", "No refresh token found.", 401)
            else:
                return invalid_response("not_found", "No refresh token found.", 401)
        except Exception as e:
            _logger.exception(
                "Error while getting access_token for payload: %s", payload
            )
            error_msg = "Error while getting access_token."
            return invalid_response("bad_request", error_msg, 400)

    def _prepare_response_data(self, Model, field_list, datas):
        response_list = []
        for data in datas:
            response = {}
            for field_name in field_list:
                field_obj = Model.sudo()._fields.get(field_name)

                # TODO: rtype is list not dict
                if not field_obj:
                    return {
                        "response": "not_found",
                        "message": f"{field_name} does not exist",
                        "status": 404,
                    }
                    # NOTE: maybe needed for next offline features
                    # response.update({
                    #     f"{field_name}_id": field_record[0] if field_record else 0, # what should be the default value 0/empty string or None(NULL) ???
                    #     f"{field_name}_name": field_record[1] if field_record else "",
                    # })
                
                # NOTE: {type, model, data} structure is needed for get_model_data api 
                # which will be used to select record in m2o field in mobile app for create/write operation.
                if field_obj.type == "many2one":
                    field_record = data.get(field_name)
                    response.update(
                        {
                            f"{field_name}": {
                                "type": field_obj.type,
                                "model": field_obj.comodel_name,
                                "data": (
                                    {"id": field_record[0], "name": field_record[1]}
                                    if field_record
                                    else {}
                                ),
                            }
                        }
                    )
                elif field_obj.type in ["one2many", "many2many"]:
                    record_list = (
                        request.env[field_obj.comodel_name]
                        .sudo()
                        .search_read(
                            domain=[("id", "in", data.get(field_name))],
                            fields=["id", "display_name"],
                        )
                    )
                    response.update({
                        f'{field_name}': {
                            "type": field_obj.type,
                            "model": field_obj.comodel_name,
                            "data": [{
                                "id": record_dict.get("id"),
                                # 'name': rec.name, # NOTE: name field does not exists in some models which are just for showing in the notebook page
                                "name": record_dict.get("display_name", ""),
                            } for record_dict in record_list] if record_list else [],
                        }
                    })
                # elif 'image' in field_name:
                #     image_id = int(payload_data['id'])
                #     response.update({
                #         f'{field_name}': f"/api/web/image?model={Model._name}&field={field_name}&id={image_id}"})
                elif field_obj.type == "binary" and "image" in field_name: # NOTE: other type of fields can contain image in the name also. so add the type binary condition for image
                    res_id = int(data.get('id'))
                    response.update({
                        f'{field_name}': f"/web/image/{Model._name}/{res_id}/{field_name}",
                    })
                elif field_obj.type == "datetime":
                    response.update({
                        f"{field_name}": data.get(field_name)
                        and str(
                            int(
                                data.get(field_name)
                                .replace(tzinfo=timezone.utc)
                                .timestamp()
                            )
                        )
                        or ""
                    })
                elif field_obj.type == "integer":
                    response.update({f"{field_name}": data.get(field_name) or 0})
                elif field_obj.type == "float":
                    response.update({f"{field_name}": data.get(field_name) or 0.0})
                elif field_obj.type == "monetary":
                    response.update({f"{field_name}": data.get(field_name) or 0.0})
                else:
                    response.update({f"{field_name}": data.get(field_name) or ""})
            response_list.append(response)
        return response_list
