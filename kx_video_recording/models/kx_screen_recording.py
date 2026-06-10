# -*- coding: utf-8 -*-
import logging
import secrets
from datetime import timedelta
from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import format_datetime, human_size

_logger = logging.getLogger(__name__)


class KxScreenRecording(models.Model):
    _name = "kx.screen.recording"
    _description = "Screen recording"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "recorded_at desc, id desc"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Recorded by",
        required=True,
        default=lambda self: self.env.user,
        index=True,
        tracking=True,
    )
    recorded_at = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    duration_seconds = fields.Float(string="Duration (s)")
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Video file",
        required=True,
        ondelete="restrict",
        copy=False,
    )
    mimetype = fields.Char(related="attachment_id.mimetype", store=True)
    file_size = fields.Integer(related="attachment_id.file_size", string="File size")
    res_model = fields.Char(string="Linked model", index=True)
    res_id = fields.Many2oneReference(
        string="Linked record",
        model_field="res_model",
        index=True,
    )
    linked_record_name = fields.Char(compute="_compute_linked_record_name")
    linked_document_ref = fields.Reference(
        string="Linked document",
        selection="_linked_document_models",
        compute="_compute_linked_document_ref",
        inverse="_inverse_linked_document_ref",
        help="Link this recording to any business document. Use “Post to document” to add it to that document’s chatter.",
    )
    chatter_posted = fields.Boolean(
        string="Posted to document chatter",
        default=False,
        copy=False,
    )
    auto_delete = fields.Boolean(
        string="Auto delete",
        default=False,
        help="Automatically delete this recording after the selected number of days.",
    )
    auto_delete_days = fields.Integer(
        string="Delete after (days)",
        default=30,
    )
    expires_on = fields.Datetime(
        string="Expires on",
        compute="_compute_expires_on",
        store=True,
    )
    access_token = fields.Char(
        copy=False,
        default=lambda self: secrets.token_urlsafe(32),
        groups="kx_video_recording.group_recording_user,kx_video_recording.group_recording_manager",
    )
    share_ids = fields.One2many(
        "kx.screen.recording.share",
        "recording_id",
        string="Shared with",
    )
    shared_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_shared_user_ids",
        string="Shared users",
        store=False,
    )
    is_manager = fields.Boolean(compute="_compute_is_manager")
    can_manage_shares = fields.Boolean(compute="_compute_can_manage_shares")
    log_ids = fields.One2many(
        "kx.screen.recording.log",
        "recording_id",
        string="Operation log",
        readonly=True,
    )

    def _chatter_log_operations(self):
        """Operations posted as notes on the linked document chatter."""
        return frozenset(
            {
                "create",
                "share",
                "unshare",
                "link",
                "email",
                "download",
                "delete",
                "auto_delete",
            }
        )

    def _format_chatter_log_body(self, operation, description):
        labels = dict(
            self.env["kx.screen.recording.log"]._fields["operation"].selection
        )
        label = labels.get(operation, operation)
        actor = self.env.user.display_name
        detail = description or self.name
        if operation in ("share", "unshare"):
            return Markup("<p><strong>%s</strong> — %s: %s</p>") % (label, actor, detail)
        return Markup(
            "<p><strong>%s</strong> — %s<br/><span class='text-muted'>%s</span></p>"
        ) % (label, actor, detail)

    @api.model
    def _format_user_share_log_detail(self, user):
        if not user:
            return _("Unknown user")
        user_type = _("portal") if user.share else _("internal")
        return _(
            "%(name)s (%(user_type)s · %(login)s)",
            name=user.display_name,
            user_type=user_type,
            login=user.login or "—",
        )

    def _log_share_access(self, operation, users):
        """One audit + chatter entry listing all users added or removed."""
        users = users.exists().filtered(lambda u: u.active)
        if not users:
            return
        for rec in self:
            owner = rec.user_id
            users = users.filtered(lambda u: u != owner)
            if not users:
                continue
            description = ", ".join(rec._format_user_share_log_detail(u) for u in users)
            rec._log_operation(operation, description)

    def _post_log_to_chatter(self, operation, description):
        """Post on the linked document chatter, or on the recording if not linked."""
        if operation not in self._chatter_log_operations():
            return
        author = self.env.user.partner_id
        post_kwargs = {
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_comment",
            "author_id": author.id,
        }
        for rec in self:
            post_kwargs["body"] = rec._format_chatter_log_body(operation, description)
            target = rec.sudo()
            if rec.res_model and rec.res_id and rec.res_model in self.env:
                document = self.env[rec.res_model].browse(rec.res_id)
                if document.exists() and hasattr(document, "message_post"):
                    target = document.sudo()
            try:
                target.with_context(mail_create_nosubscribe=True).message_post(**post_kwargs)
            except Exception:
                _logger.warning(
                    "Could not post screen recording log on %s,%s",
                    target._name,
                    target.id,
                    exc_info=True,
                )

    def _log_operation(self, operation, description=""):
        Log = self.env["kx.screen.recording.log"].sudo()
        for rec in self:
            Log.create(
                {
                    "recording_id": rec.id,
                    "user_id": self.env.user.id,
                    "operation": operation,
                    "description": description or False,
                }
            )
            rec._post_log_to_chatter(operation, description)

    @api.model
    def _linked_document_models(self):
        models = self.env["ir.model"].sudo().search(
            [
                ("transient", "=", False),
                ("model", "not in", ["kx.screen.recording", "kx.screen.recording.share"]),
            ]
        )
        return [(m.model, m.name) for m in models]

    @api.depends("res_model", "res_id")
    def _compute_linked_document_ref(self):
        for rec in self:
            ref = False
            if rec.res_model and rec.res_id:
                try:
                    doc = self.env[rec.res_model].browse(rec.res_id)
                    if doc.exists():
                        ref = f"{rec.res_model},{rec.res_id}"
                except Exception:
                    ref = False
            rec.linked_document_ref = ref

    def _inverse_linked_document_ref(self):
        for rec in self:
            if rec.linked_document_ref:
                doc = rec.linked_document_ref
                rec.res_model = doc._name
                rec.res_id = doc.id
            else:
                rec.res_model = False
                rec.res_id = 0

    @api.depends("res_model", "res_id")
    def _compute_linked_record_name(self):
        for rec in self:
            name = False
            if rec.res_model and rec.res_id:
                try:
                    record = self.env[rec.res_model].browse(rec.res_id)
                    if record.exists():
                        name = record.display_name
                except Exception:
                    _logger.debug("Could not resolve linked record for recording %s", rec.id)
            rec.linked_record_name = name or False

    @api.depends("auto_delete", "auto_delete_days", "recorded_at")
    def _compute_expires_on(self):
        for rec in self:
            if rec.auto_delete and rec.auto_delete_days and rec.recorded_at:
                rec.expires_on = rec.recorded_at + timedelta(days=rec.auto_delete_days)
            else:
                rec.expires_on = False

    @api.depends("share_ids.user_id")
    def _compute_shared_user_ids(self):
        for rec in self:
            rec.shared_user_ids = rec.share_ids.mapped("user_id")

    def _compute_is_manager(self):
        is_mgr = self.env.user.has_group("kx_video_recording.group_recording_manager")
        for rec in self:
            rec.is_manager = is_mgr

    @api.depends("user_id")
    def _compute_can_manage_shares(self):
        is_mgr = self.env.user.has_group("kx_video_recording.group_recording_manager")
        uid = self.env.user.id
        for rec in self:
            rec.can_manage_shares = is_mgr or rec.user_id.id == uid

    def _check_recording_access(self, mode="read"):
        self.check_access_rights(mode)
        if mode == "read":
            self._check_read_access_with_linked_document()
        else:
            self.check_access_rule(mode)

    def _has_linked_document_read_access(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        try:
            self.env[self.res_model].browse(self.res_id).check_access_rule("read")
            return True
        except AccessError:
            return False

    def _check_read_access_with_linked_document(self):
        try:
            self.check_access_rule("read")
        except AccessError as err:
            for rec in self:
                if not rec._has_linked_document_read_access():
                    raise AccessError(
                        _("You are not allowed to access this screen recording.")
                    ) from err

    @api.model
    def search_read_for_document(self, res_model, res_id):
        """Return recordings linked to a document for chatter (any document reader, not only shares)."""
        if not res_model or not res_id:
            return []
        document = self.env[res_model].browse(res_id)
        document.check_access_rights("read")
        document.check_access_rule("read")
        uid = self.env.user.id
        is_mgr = self.env.user.has_group("kx_video_recording.group_recording_manager")
        recordings = self.sudo().search(
            [("res_model", "=", res_model), ("res_id", "=", res_id)],
            order="recorded_at desc",
            limit=30,
        )
        return [
            {
                "id": rec.id,
                "name": rec.name,
                "duration_seconds": rec.duration_seconds,
                "recorded_at": fields.Datetime.to_string(rec.recorded_at),
                "recorded_at_display": format_datetime(self.env, rec.recorded_at),
                "attachment_id": rec.attachment_id.id,
                "shared_with": ", ".join(rec.share_ids.mapped("grantee_display"))
                or False,
                "can_share": is_mgr or rec.user_id.id == uid,
                "can_email": is_mgr or rec.user_id.id == uid,
            }
            for rec in recordings
        ]

    @api.model
    def _finalize_upload_name(self, name, res_model=None, res_id=None):
        """Use custom name, or '{document} - Screen Recording - {time}' when linked."""
        custom = (name or "").strip()
        if custom:
            return custom
        now = fields.Datetime.context_timestamp(
            self.with_context(tz=self.env.user.tz or None),
            fields.Datetime.now(),
        )
        stamp = now.strftime("%Y-%m-%d %H:%M")
        if res_model and res_id:
            try:
                doc = self.env[res_model].browse(res_id)
                if doc.exists():
                    doc_name = doc.display_name or _("Document")
                    return _("%s - Screen Recording - %s", doc_name, stamp)
            except Exception:
                _logger.debug("Could not resolve document name for recording", exc_info=True)
        return _("Screen Recording - %s", stamp)

    def _portal_partner(self):
        return self.env.user.partner_id.commercial_partner_id

    def _portal_can_read_linked_document(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        try:
            doc = self.env[self.res_model].browse(self.res_id)
            if not doc.exists():
                return False
            doc.check_access_rights("read")
            doc.check_access_rule("read")
            return True
        except AccessError:
            return False

    @api.model
    def _recording_ids_from_portal_accessible_documents(self):
        """Recordings linked to business documents the portal user may read."""
        if not self.env.user.has_group("base.group_portal"):
            return []
        candidates = self.sudo().search(
            [("res_model", "!=", False), ("res_id", "!=", 0), ("active", "=", True)]
        )
        return candidates.filtered(
            lambda r: r._portal_can_read_linked_document()
        ).ids

    def _portal_user_can_read_recording(self):
        """Portal user may view if shared with them or linked doc is readable."""
        self.ensure_one()
        if not self.env.user.has_group("base.group_portal"):
            return False
        partner = self._portal_partner()
        if self.share_ids.filtered(lambda s: s.user_id == self.env.user):
            return True
        return self._portal_can_read_linked_document()

    @api.model
    def search_read_for_portal(self):
        """Recordings for /my (portal users: shared + linked docs; others: access rules)."""
        is_portal = self.env.user.has_group("base.group_portal")
        if is_portal:
            partner = self._portal_partner()
            shared = self.search(
                [
                    ("active", "=", True),
                    ("share_ids.user_id", "=", self.env.user.id),
                ],
                order="recorded_at desc",
            )
            linked = self.sudo().browse(self._recording_ids_from_portal_accessible_documents())
            candidates = (shared | linked).sorted("recorded_at", reverse=True)
        else:
            candidates = self.search([("active", "=", True)], order="recorded_at desc", limit=100)
        seen = set()
        result = []
        for rec in candidates:
            if rec.id in seen:
                continue
            try:
                rec._check_recording_access("read")
            except AccessError:
                continue
            if is_portal and not rec._portal_user_can_read_recording():
                continue
            seen.add(rec.id)
            result.append(rec._portal_recording_dict())
            if len(result) >= 100:
                break
        return result

    def _portal_format_duration(self):
        self.ensure_one()
        seconds = int(self.duration_seconds or 0)
        if seconds < 3600:
            return f"{seconds // 60}:{seconds % 60:02d}"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"

    def _portal_linked_document_name(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        try:
            doc = self.sudo().env[self.res_model].browse(self.res_id)
            if doc.exists():
                return doc.display_name
        except Exception:
            pass
        return False

    def _portal_expiry_info(self):
        """Expiry labels for portal UI."""
        self.ensure_one()
        if self.auto_delete and self.expires_on:
            return {
                "has_expiry": True,
                "expires_on_display": format_datetime(self.env, self.expires_on),
                "expires_note": _(
                    "Scheduled removal %(days)s days after recording",
                    days=self.auto_delete_days,
                ),
            }
        return {
            "has_expiry": False,
            "expires_on_display": False,
            "expires_note": _("No expiry — kept until deleted by owner"),
        }

    def _portal_recording_dict(self):
        self.ensure_one()
        rec = self.sudo()
        attachment = rec.attachment_id
        expiry = rec._portal_expiry_info()
        file_size = rec.file_size or 0
        return {
            "id": rec.id,
            "name": rec.name,
            "recorded_by_name": rec.user_id.display_name or _("Unknown"),
            "recorded_at_display": format_datetime(self.env, rec.recorded_at),
            "duration_display": rec._portal_format_duration(),
            "file_size_display": human_size(file_size) if file_size else _("—"),
            "linked_document_name": rec._portal_linked_document_name(),
            "watch_url": rec.get_watch_url(),
            "download_url": rec.get_token_download_url() if attachment else False,
            "has_expiry": expiry["has_expiry"],
            "expires_on_display": expiry["expires_on_display"],
            "expires_note": expiry["expires_note"],
        }

    def _ensure_access_token(self):
        """Return a stable token (sudo) for tokenized watch/stream URLs."""
        self.ensure_one()
        rec = self.sudo()
        if not rec.access_token:
            rec.write({"access_token": secrets.token_urlsafe(32)})
        return rec.access_token

    def get_token_watch_url(self, absolute=False):
        """HTML player page; does not require ir.attachment ACL."""
        self.ensure_one()
        token = self._ensure_access_token()
        path = f"/kx_recording/public/{self.id}/{token}"
        if absolute:
            return f"{self.get_base_url().rstrip('/')}{path}"
        return path

    def get_token_stream_url(self, download=False):
        """Binary stream; does not require ir.attachment ACL."""
        self.ensure_one()
        url = f"{self.get_token_watch_url()}/stream"
        if download:
            url += "?download=1"
        return url

    def get_token_download_url(self):
        return self.get_token_stream_url(download=True)

    def get_public_watch_url(self):
        """Shareable link for email recipients (no Odoo login required)."""
        self.ensure_one()
        return self.get_token_watch_url(absolute=True)

    def get_email_watch_body_values(self):
        """Values for the default outbound email template."""
        self.ensure_one()
        watch_url = self.get_public_watch_url()
        expiry_note = ""
        if self.auto_delete and self.auto_delete_days:
            expiry_note = _(
                "This recording is set to expire and will be removed automatically "
                "after <strong>%(days)s days</strong> "
                "(around %(date)s).",
                days=self.auto_delete_days,
                date=format_datetime(self.env, self.expires_on) if self.expires_on else "—",
            )
        linked = self.linked_record_name or ""
        return {
            "watch_url": watch_url,
            "expiry_note": expiry_note,
            "linked_record_name": linked,
            "recorded_at_display": format_datetime(self.env, self.recorded_at),
            "duration_display": _("%s s", int(self.duration_seconds or 0)),
        }

    @api.model
    def _cron_auto_delete_recordings(self):
        now = fields.Datetime.now()
        candidates = self.search([("auto_delete", "=", True), ("auto_delete_days", ">", 0)])
        to_unlink = candidates.filtered(
            lambda r: r.recorded_at
            and r.recorded_at + timedelta(days=r.auto_delete_days) <= now
        )
        if to_unlink:
            _logger.info("Auto-deleting %s screen recording(s)", len(to_unlink))
            for rec in to_unlink:
                rec._log_operation(
                    "auto_delete",
                    _("Auto deleted after %s days", rec.auto_delete_days),
                )
            to_unlink.unlink()

    def unlink(self):
        for rec in self:
            rec._log_operation("delete", _("Recording deleted"))
        attachments = self.mapped("attachment_id")
        res = super().unlink()
        attachments.exists().unlink()
        return res

    @api.model
    def create_from_upload(
        self,
        name,
        data,
        mimetype="video/webm",
        duration_seconds=0,
        res_model=None,
        res_id=None,
        post_to_chatter=False,
        auto_delete=False,
        auto_delete_days=30,
    ):
        """Create attachment + recording; optionally post on the linked record's chatter."""
        if not self.env.user.has_group("kx_video_recording.group_recording_user"):
            raise AccessError(_("You are not allowed to create screen recordings."))
        if not data:
            raise UserError(_("Recording data is empty."))
        name = self._finalize_upload_name(name, res_model=res_model, res_id=res_id)
        if not mimetype:
            mimetype = "video/webm"
        # Strip codec suffixes (e.g. video/webm;codecs=vp9) for reliable browser playback.
        if ";" in mimetype:
            mimetype = mimetype.split(";", 1)[0].strip()
        if not mimetype.startswith("video/"):
            mimetype = "video/webm"

        file_name = name if name.lower().endswith((".webm", ".mp4", ".mkv")) else f"{name}.webm"
        attachment = self.env["ir.attachment"].create(
            {
                "name": file_name,
                "datas": data,
                "mimetype": mimetype,
                "type": "binary",
            }
        )
        recording = self.create(
            {
                "name": name,
                "duration_seconds": duration_seconds or 0,
                "attachment_id": attachment.id,
                "res_model": res_model or False,
                "res_id": res_id or 0,
                "auto_delete": bool(auto_delete),
                "auto_delete_days": int(auto_delete_days or 30) if auto_delete else 0,
            }
        )
        attachment.write(
            {
                "res_model": self._name,
                "res_id": recording.id,
            }
        )

        if res_model and res_id and post_to_chatter:
            recording._post_on_linked_record(attachment)
            recording.chatter_posted = True

        log_details = []
        if duration_seconds:
            log_details.append(_("Duration: %s s", int(duration_seconds)))
        if auto_delete:
            log_details.append(_("Auto delete in %s days", auto_delete_days))
        recording._log_operation("create", "; ".join(log_details) if log_details else False)
        if res_model and res_id:
            recording._log_operation(
                "link",
                _("%(model)s #%(id)s", model=res_model, id=res_id),
            )

        return {
            "id": recording.id,
            "name": recording.name,
            "attachment_id": attachment.id,
            "view_url": recording.get_watch_url(),
        }

    def _post_on_linked_record(self, attachment):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return
        try:
            record = self.env[self.res_model].browse(self.res_id)
        except KeyError:
            return
        if not record.exists():
            return
        if not hasattr(record, "message_post"):
            return
        record.check_access_rights("write")
        record.check_access_rule("write")
        body = _("Screen recording: %s", self.name)
        record.message_post(
            body=body,
            attachment_ids=[attachment.id],
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        attachment.sudo().write(
            {
                "res_model": self.res_model,
                "res_id": self.res_id,
            }
        )
        self.chatter_posted = True

    def action_post_to_document(self):
        """Post the video on the linked document’s chatter (if it uses mail.thread)."""
        for rec in self:
            if not rec.res_model or not rec.res_id:
                raise UserError(_("Select a linked document first."))
            if rec.chatter_posted:
                raise UserError(_("This recording is already on the document’s chatter."))
            rec._post_on_linked_record(rec.attachment_id)
            rec.chatter_posted = True
        return True

    def action_open_linked_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            raise UserError(_("This recording is not linked to a record."))
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }

    def get_watch_url(self):
        """URL of the HTML player page (tokenized; works for portal users)."""
        self.ensure_one()
        return self.get_token_watch_url()

    def get_playback_data(self):
        """Return attachment info for inline video playback in the web client."""
        self.ensure_one()
        self._check_recording_access("read")
        self._log_operation("view", _("Recording played"))
        attachment = self.attachment_id
        mimetype = attachment.mimetype or "video/webm"
        if ";" in mimetype:
            mimetype = mimetype.split(";", 1)[0].strip()
        return {
            "attachment_id": attachment.id,
            "name": attachment.name or self.name,
            "mimetype": mimetype,
        }

    def action_download_video(self):
        self.ensure_one()
        self._check_recording_access("read")
        attachment = self.attachment_id
        self._log_operation("download", _("Video downloaded"))
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def action_email_wizard(self):
        self.ensure_one()
        if not self.can_manage_shares:
            raise AccessError(_("You cannot send this recording."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Email recording"),
            "res_model": "kx.screen.recording.email.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_recording_id": self.id},
        }

    def action_open_video(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "kx_recording_playback",
            "params": {"recording_id": self.id},
        }

    def action_share_wizard(self):
        self.ensure_one()
        if not self.can_manage_shares:
            raise AccessError(_("You cannot manage sharing for this recording."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Share recording"),
            "res_model": "kx.screen.recording.share.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_recording_id": self.id},
        }
