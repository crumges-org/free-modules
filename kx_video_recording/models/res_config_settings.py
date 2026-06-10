# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    kx_video_recording_active = fields.Boolean(
        related="company_id.kx_video_recording_active",
        readonly=False,
    )
