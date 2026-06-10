# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    kx_video_recording_active = fields.Boolean(
        string="Screen recording in chatter",
        default=True,
        help="Allow users to record screen videos from the chatter and link them to records.",
    )
