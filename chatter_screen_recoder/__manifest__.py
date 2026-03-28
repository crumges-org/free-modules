# -*- coding: utf-8 -*-
{
    'name': "Chatter Screen Recorder",
    'summary': "Record screen and attach to any record with chatter",
    'description': """
        Record your screen directly from any Odoo chatter with a single click.
        The recording persists across page navigation via a global service
        and is controllable from a systray icon in the top-right navbar.

        Key Features:
        - One-click screen recording from any chatter
        - Persistent recording across page navigation
        - Systray controls: Save, Pause, Resume, Discard
        - Captures screen video + system audio + microphone audio
        - Auto-uploads recording as WebM attachment to source record
        - No server-side dependencies - pure frontend JavaScript
    """,
    'author': "Abdallah Salem",
    'website': 'https://apps.odoo.com/apps/modules/browse?search=Abdallah+salem',
    'category': 'Productivity',
    'version': '18.0.2.0.0',
    'license': 'LGPL-3',
    'depends': ['mail'],
    'images': ['static/description/banner.jpg'],
    'assets': {
        'web.assets_backend': [
            'chatter_screen_recoder/static/src/css/screen_recorder.scss',
            'chatter_screen_recoder/static/src/js/screen_recorder_service.js',
            'chatter_screen_recoder/static/src/js/screen_recorder_systray.js',
            'chatter_screen_recoder/static/src/js/chatter_screen_recorder.js',
            'chatter_screen_recoder/static/src/xml/screen_recorder_systray.xml',
            'chatter_screen_recoder/static/src/xml/chatter_screen_recorder.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
