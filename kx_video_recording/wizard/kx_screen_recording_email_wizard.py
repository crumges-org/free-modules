# -*- coding: utf-8 -*-
import re
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class KxScreenRecordingEmailWizard(models.TransientModel):
    _name = "kx.screen.recording.email.wizard"
    _description = "Email screen recording"

    recording_id = fields.Many2one("kx.screen.recording", required=True, ondelete="cascade")
    email_to = fields.Char(string="Recipients", required=True, help="One or more email addresses, separated by commas.")
    subject = fields.Char(required=True)
    body = fields.Html(string="Message")

    @api.model
    def _default_email_body(self, recording):
        vals = recording.get_email_watch_body_values()
        expiry_block = ""
        if vals.get("expiry_note"):
            expiry_block = f"""
            <p style="margin:16px 0;padding:12px 16px;background:#fff8e6;border-left:4px solid #f0ad4e;">
                {vals['expiry_note']}
            </p>"""
        linked_line = ""
        if vals.get("linked_record_name"):
            linked_line = f"<li><strong>Related to:</strong> {vals['linked_record_name']}</li>"
        return _(
            """
            <p>Hello,</p>
            <p>
                You have been sent a screen recording
                <strong>%(recording_name)s</strong>.
                Use the button below to watch it in your browser — no attachment is included.
            </p>
            <ul>
                <li><strong>Recorded on:</strong> %(recorded_at)s</li>
                <li><strong>Duration:</strong> %(duration)s</li>
                %(linked_line)s
            </ul>
            %(expiry_block)s
            <p style="margin:24px 0;">
                <a href="%(watch_url)s"
                   style="display:inline-block;padding:12px 24px;background:#714B67;color:#ffffff;
                          text-decoration:none;border-radius:4px;font-weight:600;">
                    Watch recording
                </a>
            </p>
            <p style="color:#666;font-size:13px;">
                If the button does not work, copy and paste this link into your browser:<br/>
                <a href="%(watch_url)s">%(watch_url)s</a>
            </p>
            <p>Best regards,<br/>%(sender)s</p>
            """,
            recording_name=recording.name,
            recorded_at=vals["recorded_at_display"],
            duration=vals["duration_display"],
            linked_line=linked_line,
            expiry_block=expiry_block,
            watch_url=vals["watch_url"],
            sender=self.env.user.name or _("Your team"),
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        rec_id = self.env.context.get("default_recording_id")
        if rec_id:
            rec = self.env["kx.screen.recording"].browse(rec_id)
            if rec.exists():
                res.setdefault("subject", _("Screen recording: %s", rec.name))
                res.setdefault("body", self._default_email_body(rec))
        return res

    def _parse_emails(self):
        self.ensure_one()
        raw = (self.email_to or "").replace(";", ",")
        emails = [part.strip() for part in raw.split(",") if part.strip()]
        if not emails:
            raise UserError(_("Enter at least one recipient email address."))
        invalid = [e for e in emails if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e)]
        if invalid:
            raise UserError(_("Invalid email address(es): %s", ", ".join(invalid)))
        return emails

    def action_send(self):
        self.ensure_one()
        recording = self.recording_id
        if not recording.can_manage_shares:
            raise AccessError(_("You cannot send this recording."))
        if not recording.attachment_id:
            raise UserError(_("This recording has no video file."))
        emails = self._parse_emails()
        mail_values = {
            "email_from": self.env.user.email_formatted or False,
            "subject": self.subject,
            "body_html": self.body,
            "auto_delete": True,
        }
        Mail = self.env["mail.mail"].sudo()
        for email in emails:
            Mail.create({**mail_values, "email_to": email}).send()
        recording._log_operation("email", _("Emailed link to %s", ", ".join(emails)))
        return {"type": "ir.actions.act_window_close"}
