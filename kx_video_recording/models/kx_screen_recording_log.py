# -*- coding: utf-8 -*-
from odoo import fields, models


class KxScreenRecordingLog(models.Model):
    _name = "kx.screen.recording.log"
    _description = "Screen recording operation log"
    _order = "create_date desc, id desc"

    recording_id = fields.Many2one(
        "kx.screen.recording",
        string="Recording",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    operation = fields.Selection(
        selection=[
            ("create", "Created"),
            ("share", "Access granted"),
            ("unshare", "Access removed"),
            ("delete", "Deleted"),
            ("auto_delete", "Auto deleted"),
            ("link", "Linked to document"),
            ("view", "Viewed"),
            ("email", "Emailed"),
            ("download", "Downloaded"),
        ],
        required=True,
        index=True,
    )
    description = fields.Char()
    create_date = fields.Datetime(readonly=True)
