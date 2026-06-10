# -*- coding: utf-8 -*-
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        info = super().session_info()
        if self.env.user and self.env.user.id:
            info["kx_video_recording_active"] = self.env.company.kx_video_recording_active
            info["kx_video_recording_user"] = self.env.user.has_group(
                "kx_video_recording.group_recording_user"
            )
        return info
