# -*- coding: utf-8 -*-
{
    "name": "Screen video recording",
    "version": "18.0.1.0",
    "category": "Productivity",
    "summary": "Record screen with microphone and system audio; store and share recordings.",
    "description": """
Record screen videos with microphone and system/tab audio from the systray or chatter.
Recordings are stored as attachments and can be linked to business records.
Managers see all recordings; users see their own and those shared with them.
    """,
    "author": "KoderXpert Technologies Private Limited",
    "company": "KoderXpert Technologies Private Limited",
    "maintainer": "KoderXpert Technologies Private Limited",
    "website": "https://koderxpert.com",
    "depends": ["web", "mail", "base_setup", "portal"],
    "data": [
        "security/recording_groups.xml",
        "security/ir.model.access.csv",
        "security/recording_security.xml",
        "data/ir_cron_data.xml",
        "views/kx_screen_recording_views.xml",
        "views/kx_screen_recording_share_views.xml",
        "views/kx_screen_recording_email_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu.xml",
        "views/kx_screen_recording_portal_templates.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "kx_video_recording/static/src/portal/portal_recordings.scss",
            "kx_video_recording/static/src/portal/portal_recordings.js",
        ],
        "web.assets_backend": [
            "kx_video_recording/static/src/recording_stream.js",
            "kx_video_recording/static/src/recording_playback_service.js",
            "kx_video_recording/static/src/recording_service.js",
            "kx_video_recording/static/src/systray/recording_systray.scss",
            "kx_video_recording/static/src/systray/recording_systray.xml",
            "kx_video_recording/static/src/systray/recording_systray.js",
            "kx_video_recording/static/src/patches/form_controller_patch.js",
            "kx_video_recording/static/src/patches/chatter_patch.js",
            "kx_video_recording/static/src/patches/chatter_patch.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": 'OPL-1',
    "images": ["static/description/kx_video_recording.gif"]
}
