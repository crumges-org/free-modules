import hashlib
import logging
import jwt
import base64
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class FleetApiAccessToken(models.Model):
    """
        Added fields and function for access_token and refresh token
    """
    _name = "fleet.api.access_token"
    _description = "Fleet API Access Token"

    access_token = fields.Char("Access Token")
    refresh_token = fields.Char("Refresh Token")
    user_id = fields.Many2one("res.users", string="User", required=True, ondelete='cascade')
    access_token_expires = fields.Datetime(string="Access Token Expires")
    refresh_token_expires = fields.Datetime(string="Refresh Token Expires")
    scope = fields.Char(string="Scope")

    def find_one_or_create_fleet_token(self, user_id=None, create=False, refresh_token_obj=False):
        now = datetime.now()
        def generate_access_token(user_id):
            access_exp = now + timedelta(seconds=3600)
            access_payload = {
                "user_id": f"access_{user_id}",
                "exp": access_exp
            }
            access_token = jwt.encode(access_payload, f'fleet_secret_key_{user_id}', algorithm="HS256")
            return access_token, access_exp
        if not user_id:
            user_id = self.env.user.id
        if not refresh_token_obj:
            token_id = self.env["fleet.api.access_token"].sudo().search([("user_id", "=", user_id)], 
                                                                        order="id DESC", limit=1)
        else:
            token_id = refresh_token_obj
        if token_id:
            if now > fields.Datetime.from_string(token_id.refresh_token_expires) and (
                        not token_id.access_token or now > fields.Datetime.from_string(token_id.access_token_expires)):
                token_id = None
        if token_id and (not token_id.access_token or  now > fields.Datetime.from_string(
                    token_id.access_token_expires)):
            access_token, access_exp = generate_access_token(user_id)
            token_id.sudo().write({
                "access_token":access_token,
                "access_token_expires":access_exp
            })
        if not token_id and create:
            access_token, access_exp = generate_access_token(user_id)

            refresh_payload = {
                "user_id": f"refresh_{user_id}",
                "exp": now + timedelta(seconds=1209600)
            }
            refresh_token = jwt.encode(refresh_payload, f'fleet_refresh_key_{user_id}', algorithm="HS256")
            vals = {
                "user_id": user_id,
                "scope": "tokeninfo",
                "access_token_expires": access_exp,
                "refresh_token_expires": refresh_payload['exp'],
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
            token_id = self.env["fleet.api.access_token"].sudo().create(vals)
        if not token_id:
            return None
        if token_id.access_token and fields.Datetime.from_string(
                    token_id.refresh_token_expires) < fields.Datetime.from_string(
                    token_id.access_token_expires):
            token_id.access_token_expires = token_id.refresh_token_expires  

        _logger.info(f"In find_one_or_create_fleet_token: \n user: id:{token_id.user_id.id}, name: {token_id.user_id.name} ")
        return token_id.access_token, token_id.refresh_token
    
    
    def delete_expired_token(self):
        """Schedule action function to delete expired tokens"""

        fleet_api_access_token_ids = self.env['fleet.api.access_token'].sudo().search([])
        now = datetime.now()
        for token_id in fleet_api_access_token_ids:
            if now > fields.Datetime.from_string(token_id.refresh_token_expires) and (
                        not token_id.access_token or now > fields.Datetime.from_string(token_id.access_token_expires)):
                token_id.sudo().unlink()
            elif token_id.access_token and now > fields.Datetime.from_string(
                                                token_id.access_token_expires):
                token_id.sudo().write({
                                        "access_token": "",
                                        "access_token_expires":""
                                    })

        return 
