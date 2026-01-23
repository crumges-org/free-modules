from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from .main import ServerMonitorBase


class ServerMonitorOdooController(http.Controller, ServerMonitorBase):
    @http.route("/server_monitor/odoo", type="json", auth="user")
    def get_odoo_metrics(self):
        if not request.env.user.has_group("server_monitor.group_server_monitor_user"):
            raise AccessError(_("You do not have access to Server Monitor."))

        config = self._get_config()
        return self._get_odoo_payload(config)

    @http.route("/server_monitor/odoo/logs", type="json", auth="user")
    def get_odoo_logs(self, log_lines=None, log_search=None):
        if not request.env.user.has_group("server_monitor.group_server_monitor_user"):
            raise AccessError(_("You do not have access to Server Monitor."))

        config = self._get_config()
        return self._get_odoo_log_payload(
            config, log_lines=log_lines, log_search=log_search
        )
