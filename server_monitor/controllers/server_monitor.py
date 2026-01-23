from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

from .main import ServerMonitorBase, psutil


class ServerMonitorController(http.Controller, ServerMonitorBase):
    @http.route("/server_monitor/metrics", type="json", auth="user")
    def get_metrics(self):
        if not request.env.user.has_group("server_monitor.group_server_monitor_user"):
            raise AccessError(_("You do not have access to Server Monitor."))

        config = self._get_config()
        if psutil is None:
            return {
                "error": {
                    "code": "psutil_missing",
                    "message": "psutil is not installed on the server.",
                },
                "config": config,
            }

        base_payload = self._get_base_payload(config["adapters_include"])
        payload = {
            **base_payload,
            "network": [adapter.copy() for adapter in base_payload["network"]],
            "disk_io": [disk.copy() for disk in base_payload["disk_io"]],
            "config": config,
        }
        self._apply_network_rates(payload)
        self._apply_disk_rates(payload)
        payload["processes"] = self._get_process_payload(
            config["process_limit"], config["process_interval_ms"]
        )
        payload["gpus"] = self._get_gpu_payload(config["gpu_interval_ms"])
        return payload
