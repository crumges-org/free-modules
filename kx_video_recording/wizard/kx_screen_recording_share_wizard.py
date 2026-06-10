# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class KxScreenRecordingShareWizard(models.TransientModel):
    _name = "kx.screen.recording.share.wizard"
    _description = "Share screen recording"

    recording_id = fields.Many2one("kx.screen.recording", required=True)
    recording_owner_id = fields.Many2one(
        related="recording_id.user_id",
        string="Recorded by",
        readonly=True,
    )
    user_ids = fields.Many2many(
        "res.users",
        "kx_recording_share_wizard_user_rel",
        "wizard_id",
        "user_id",
        string="Share with",
        domain="[('active', '=', True), ('id', '!=', recording_owner_id)]",
        help="Add or remove users who can watch and download this recording.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        recording_id = res.get("recording_id") or self.env.context.get("default_recording_id")
        if recording_id and "user_ids" in fields_list:
            recording = self.env["kx.screen.recording"].browse(recording_id)
            owner_id = recording.user_id.id
            shared_ids = recording.share_ids.user_id.filtered(
                lambda u: u.id != owner_id
            ).ids
            res["user_ids"] = [(6, 0, shared_ids)]
        return res

    def action_confirm(self):
        self.ensure_one()
        recording = self.recording_id
        if not recording.can_manage_shares:
            raise AccessError(_("You cannot share this recording."))
        owner = recording.user_id
        target_users = self.user_ids.filtered(lambda u: u != owner)
        if owner in self.user_ids:
            raise ValidationError(_("The owner already has access and cannot be added here."))

        Share = self.env["kx.screen.recording.share"].with_context(kx_skip_share_log=True)
        before_ids = set(recording.share_ids.user_id.ids)
        after_ids = set(target_users.ids)
        to_remove_ids = before_ids - after_ids
        to_add_ids = after_ids - before_ids

        removed_users = self.env["res.users"].browse(list(to_remove_ids))
        added_users = self.env["res.users"].browse(list(to_add_ids))

        if to_remove_ids:
            Share.search(
                [
                    ("recording_id", "=", recording.id),
                    ("user_id", "in", list(to_remove_ids)),
                ]
            ).unlink()
        for user in added_users:
            Share.create(
                {
                    "recording_id": recording.id,
                    "user_id": user.id,
                }
            )

        if removed_users:
            recording._log_share_access("unshare", removed_users)
        if added_users:
            recording._log_share_access("share", added_users)

        return {"type": "ir.actions.act_window_close"}
