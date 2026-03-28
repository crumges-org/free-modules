{
    "name": "Chatter Voice Note",
    "version": "19.0.1.0.0",
    "summary": "Record voice note from chatter",
    "author": "Niraj Mamtora",
    "maintainer": "Niraj Mamtora",
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "chatter_voice_note/static/src/js/voice_recorder.js",
            "chatter_voice_note/static/src/xml/voice_button.xml",
        ],
    },
    "data": [

    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}