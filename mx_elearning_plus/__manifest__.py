# -*- coding: utf-8 -*-
{
    'name': 'eLearning Plus',
    'version': '18.0.0.5',
    'sequence': 10,
    'summary': 'Added extra features to enhance learning.',
    'website': 'https://www.manprax.com',
    'author': 'ManpraX Software LLP',
    'category': 'Website/eLearning',
    'description': """
Extended feature of elearning.
""",
    'depends': [
        'website_slides',
    ],
    'data': [
        'views/slide_view.xml',
        'views/website_slides_templates_course.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
        'web.assets_frontend': [
            'mx_elearning_plus/static/src/js/slides_course.js',
            'mx_elearning_plus/static/src/js/slides_course_extend.js',
            'mx_elearning_plus/static/src/js/slides_course_rating_fullscreen.js',
            'mx_elearning_plus/static/src/js/slide_comment_composer_fullscreen.js',
            'mx_elearning_plus/static/src/xml/comment_composer.xml',
            'mx_elearning_plus/static/src/xml/comment_button_composer_extend.xml',
        ],
    },
    'demo': [],
    'qweb': [],
    'images': ["static/description/images/app_banner_plus.png"],
    'installable': True,
    'application': True,
    'license': 'AGPL-3',
}