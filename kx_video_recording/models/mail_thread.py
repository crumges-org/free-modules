# -*- coding: utf-8 -*-
from odoo import _, fields, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    kx_screen_recording_count = fields.Integer(string="Screen recordings", compute="_compute_kx_screen_recording_count")

    def _compute_kx_screen_recording_count(self):
        if not self.ids:
            for record in self:
                record.kx_screen_recording_count = 0
            return
        grouped = self.env["kx.screen.recording"]._read_group(
            domain=[("res_model", "=", self._name), ("res_id", "in", self.ids)],
            groupby=["res_id"],
            aggregates=["__count"],
        )
        counts = {}
        for row in grouped:
            if len(row) == 2:
                res_id, count = row
            else:
                continue
            rid = res_id.id if hasattr(res_id, "id") else res_id
            counts[rid] = count
        for record in self:
            record.kx_screen_recording_count = counts.get(record.id, 0)

    def action_view_kx_screen_recordings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Screen recordings"),
            "res_model": "kx.screen.recording",
            "view_mode": "list,form",
            "domain": [("res_model", "=", self._name), ("res_id", "=", self.id)],
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }
