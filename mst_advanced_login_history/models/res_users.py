import logging

from odoo import models,fields
from odoo.exceptions import AccessDenied
from odoo.http import request


_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @classmethod
    def authenticate(cls, db, credential, user_agent_env):
        login = ''

        if isinstance(credential, dict):
            login = credential.get('login') or ''

        try:
            auth_info = super().authenticate(
                db,
                credential,
                user_agent_env
            )

        except AccessDenied:
            try:
                if request and request.env:
                    request.env['login.failed.history'].sudo().create_failed_login_record(
                        login=login,
                        reason='Invalid login credentials'
                    )
            except Exception as error:
                _logger.exception(
                    'Failed login tracking failed: %s',
                    error
                )

            raise

        try:
            uid = False

            if isinstance(auth_info, dict):
                uid = auth_info.get('uid')

            if uid and request and request.env:
                user = request.env['res.users'].sudo().browse(uid)

                if user.exists():
                    request.env['login.history'].sudo().create_login_record(user)

        except Exception as error:
            _logger.exception(
                'Login history tracking failed: %s',
                error
            )

        return auth_info

    login_history_ids = fields.One2many(
        "login.history",
        "user_id",
        string="User Sessions"
    )

    activity_log_ids = fields.One2many(
        "mst.user.activity.log",
        "user_id",
        string="Activity Logs"
    )

    def action_kill_all_sessions(self):
        for user in self:
            active_sessions = self.env["login.history"].sudo().search(
                [
                    ("user_id", "=", user.id),
                    ("status", "=", "active"),
                ]
            )

            for session_record in active_sessions:
                session_id = session_record.session_id

                if session_id:
                    try:
                        if request and request.session_store:
                            session = request.session_store.get(session_id)
                            request.session_store.delete(session)
                    except Exception as error:
                        _logger.exception(
                            "Failed to delete session %s: %s",
                            session_id,
                            error
                        )

                session_record.write(
                    {
                        "logout_time": fields.Datetime.now(),
                        "status": "logout",
                    }
                )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Sessions Killed",
                "message": "All active sessions for this user have been killed.",
                "type": "success",
                "sticky": False,
            },
        }