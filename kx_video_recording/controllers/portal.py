# -*- coding: utf-8 -*-

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class KxRecordingPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "recording_count" in counters:
            Recording = request.env["kx.screen.recording"]
            if request.env.user.has_group(
                "base.group_portal"
            ) or request.env.user.has_group("kx_video_recording.group_recording_user"):
                try:
                    values["recording_count"] = len(Recording.search_read_for_portal())
                except AccessError:
                    values["recording_count"] = 0
            else:
                values["recording_count"] = 0
        return values

    @http.route(["/my/screen_recordings", "/my/screen_recordings/page/<int:page>"], type="http", auth="user", website=True)
    def portal_screen_recordings(self, page=1, **kw):
        Recording = request.env["kx.screen.recording"]
        if not (
            request.env.user.has_group("base.group_portal")
            or request.env.user.has_group("kx_video_recording.group_recording_user")
        ):
            return request.redirect("/my")
        try:
            recordings = Recording.search_read_for_portal()
        except AccessError:
            recordings = []
        values = {
            "recordings": recordings,
            "page_name": "screen_recordings",
        }
        return request.render("kx_video_recording.portal_screen_recordings", values)

    @http.route("/my/screen_recording/<int:recording_id>", type="http", auth="user", website=True)
    def portal_screen_recording_watch(self, recording_id, **kw):
        recording = request.env["kx.screen.recording"].browse(recording_id)
        if not recording.exists() or not recording._portal_user_can_read_recording():
            return request.not_found()
        return request.redirect(recording.get_watch_url())

    @http.route("/my/screen_recording/<int:recording_id>/download", type="http", auth="user")
    def portal_screen_recording_download(self, recording_id, **kw):
        recording = request.env["kx.screen.recording"].browse(recording_id)
        if not recording.exists() or not recording._portal_user_can_read_recording():
            return request.not_found()
        if not recording.attachment_id:
            return request.not_found()
        return request.redirect(recording.get_token_download_url(), code=302)
