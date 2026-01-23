# -*- coding: utf-8 -*-
{
    'name': 'Record and Embed Audio or Video in Html Editor',
    'description': 'Web E-learning Video',
    'category': 'Extra Tools',
    'summary': 'Create and play videos/audios on Odoo platform',
    'sequence': 10,
    'version': '1.3',
    'website': 'https://www.manprax.com',
    'author': 'ManpraX Software LLP',
    'depends': ['web', 'website', 'website_slides', 'web_editor'],
    'assets': {
        'web_editor.assets_wysiwyg': [
            'web_elearning_video/static/src/js/wysiwyg.js',
        ],
        'web.assets_backend': [
            'web_elearning_video/static/src/js/video_plugin.js',
            'web_elearning_video/static/src/js/audio_plugin.js',
        ],
        'web_editor.assets_media_dialog': [
            'web_elearning_video/static/src/js/video_dialog.js',
            'web_elearning_video/static/src/xml/video_dialog_template.xml',
            'web_elearning_video/static/src/js/audio_dialog.js',
            'web_elearning_video/static/src/xml/audio_dialog_template.xml',
        ],
    },
    'images': ['static/description/images/banner.png'],
    'application': True,
    'license': 'AGPL-3',
}