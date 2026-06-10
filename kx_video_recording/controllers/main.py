# -*- coding: utf-8 -*-
import base64
import logging
import secrets
from urllib.parse import quote
from markupsafe import escape
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


def _render_watch_page(recording, attachment, src_url):
    mimetype = attachment.mimetype or "video/webm"
    if ";" in mimetype:
        mimetype = mimetype.split(";", 1)[0].strip()
    if not mimetype.startswith("video/"):
        mimetype = "video/webm"
    title = escape(recording.name or "Screen recording")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>{title}</title>
    <style>
        html, body {{
            margin: 0;
            min-height: 100%;
            background: #111;
            color: #eee;
            font-family: system-ui, -apple-system, sans-serif;
        }}
        body {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            box-sizing: border-box;
        }}
        h1 {{
            font-size: 1rem;
            font-weight: 500;
            margin: 0 0 1rem;
            opacity: 0.85;
            text-align: center;
        }}
        video {{
            width: 100%;
            max-width: 1200px;
            max-height: calc(100vh - 4rem);
            background: #000;
            border-radius: 4px;
        }}
        a {{ color: #7af; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <video controls playsinline preload="metadata">
        <source src="{src_url}" type="{escape(mimetype)}"/>
    </video>
    <p style="margin-top:1rem;font-size:0.85rem;opacity:0.7">
        <a href="{src_url}" download>Download video</a>
    </p>
</body>
</html>"""


class KxRecordingController(http.Controller):
    @http.route(
        "/kx_recording/upload",
        methods=["POST"],
        type="http",
        auth="user",
        csrf=True,
    )
    def upload_recording(self, ufile, name=None, duration=0, res_model=None, res_id=None, **kwargs):
        """Upload a recorded video blob and create kx.screen.recording + attachment."""
        try:
            if not ufile:
                return request.make_json_response({"error": "No file uploaded"}, status=400)
            raw = ufile.read()
            if not raw:
                return request.make_json_response({"error": "Empty recording"}, status=400)
            data = base64.b64encode(raw).decode()
            res_id_int = int(res_id) if res_id not in (None, "", "0", 0) else None
            res_model_str = res_model if res_model not in (None, "", "false") else None
            auto_delete = str(request.httprequest.form.get("auto_delete", "")).lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            auto_delete_days = int(request.httprequest.form.get("auto_delete_days") or 30)
            result = request.env["kx.screen.recording"].create_from_upload(
                name=name or ufile.filename or "Screen recording",
                data=data,
                mimetype=ufile.content_type or "video/webm",
                duration_seconds=float(duration or 0),
                res_model=res_model_str,
                res_id=res_id_int,
                post_to_chatter=False,
                auto_delete=auto_delete,
                auto_delete_days=auto_delete_days,
            )
            return request.make_json_response(result)
        except Exception as exc:
            _logger.exception("Screen recording upload failed")
            return request.make_json_response({"error": str(exc)}, status=400)

    @http.route(
        "/kx_recording/watch/<int:recording_id>",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def watch_recording(self, recording_id, **kwargs):
        """Redirect legacy watch URLs to the tokenized player."""
        recording = request.env["kx.screen.recording"].browse(recording_id)
        if not recording.exists():
            return request.not_found()
        try:
            recording._check_recording_access("read")
        except AccessError:
            return request.not_found()
        return request.redirect(recording.get_watch_url(), code=302)

    @http.route(
        "/kx_recording/public/<int:recording_id>/<string:token>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def watch_recording_public(self, recording_id, token, **kwargs):
        """Public watch page for email links (token required)."""
        recording = request.env["kx.screen.recording"].sudo().browse(recording_id)
        if not recording.exists() or not recording.active:
            return request.not_found()
        expected = recording.access_token or ""
        if not expected or not secrets.compare_digest(expected, token):
            return request.not_found()
        attachment = recording.attachment_id
        if not attachment:
            return request.not_found()
        src = recording.get_token_stream_url()
        html = _render_watch_page(recording, attachment, src)
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route(
        "/kx_recording/public/<int:recording_id>/<string:token>/stream",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def stream_recording_public(self, recording_id, token, download=None, **kwargs):
        recording = request.env["kx.screen.recording"].sudo().browse(recording_id)
        if not recording.exists() or not recording.active:
            return request.not_found()
        expected = recording.access_token or ""
        if not expected or not secrets.compare_digest(expected, token):
            return request.not_found()
        attachment = recording.attachment_id
        if not attachment:
            return request.not_found()
        if not attachment.datas:
            return request.not_found()
        data = base64.b64decode(attachment.datas)
        mimetype = attachment.mimetype or "video/webm"
        if ";" in mimetype:
            mimetype = mimetype.split(";", 1)[0].strip()
        filename = attachment.name or "recording.webm"
        headers = [
            ("Content-Type", mimetype),
            ("Content-Length", len(data)),
        ]
        if download:
            headers.append(
                ("Content-Disposition", f'attachment; filename="{quote(filename, safe="")}"')
            )
        else:
            headers.append(("Content-Disposition", "inline"))
        return request.make_response(data, headers=headers)
