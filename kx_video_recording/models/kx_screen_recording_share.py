# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class KxScreenRecordingShare(models.Model):
    _name = "kx.screen.recording.share"
    _description = "Screen recording share"
    _order = "id desc"

    recording_id = fields.Many2one(
        "kx.screen.recording",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        index=True,
        domain="[('active', '=', True)]",
    )
    grantee_display = fields.Char(
        string="Shared with",
        compute="_compute_grantee_display",
        store=True,
    )
    company_id = fields.Many2one(
        related="recording_id.company_id",
        store=True,
    )
    permission = fields.Selection(
        [("view", "View only")],
        default="view",
        required=True,
    )
    shared_by_id = fields.Many2one(
        "res.users",
        string="Shared by",
        default=lambda self: self.env.user,
        readonly=True,
    )

    _sql_constraints = [
        (
            "recording_user_unique",
            "unique(recording_id, user_id)",
            "This user is already shared on the recording.",
        ),
    ]

    @api.depends("user_id")
    def _compute_grantee_display(self):
        for share in self:
            share.grantee_display = share.user_id.display_name if share.user_id else ""

    @api.constrains("user_id", "recording_id")
    def _check_not_owner(self):
        for share in self:
            if share.recording_id.user_id == share.user_id:
                raise ValidationError(_("The owner already has access to their recording."))

    def _grantee_name(self):
        self.ensure_one()
        return self.user_id.display_name if self.user_id else _("Unknown user")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            rec_id = vals.get("recording_id")
            if rec_id:
                recording = self.env["kx.screen.recording"].browse(rec_id)
                if not recording.can_manage_shares:
                    raise AccessError(_("You cannot share this recording."))
        shares = super().create(vals_list)
        if not self.env.context.get("kx_skip_share_log"):
            for share in shares:
                share.recording_id._log_share_access("share", share.user_id)
        return shares

    def unlink(self):
        if not self.env.context.get("kx_skip_share_log"):
            for share in self:
                share.recording_id._log_share_access("unshare", share.user_id)
        return super().unlink()
