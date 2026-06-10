# -*- coding: utf-8 -*-
{
    'name': 'Auto Logout User',
    'version': '18.0.0.0',
    'category': 'Extra Tools',
    'summary': """Auto logout idle user with fixed time""",
    'description': """User can fix the timer in the user's profile, if the user
     is in idle mode the user will logout from session automatically """,
    'author': 'Apagen Solutions Pvt Ltd',
    'company': 'Apagen Solutions Pvt Ltd',
    'maintainer': 'Apagen Solutions Pvt Ltd',
    'website': 'www.apagen.com',
    'depends': ['base'],
    'data': [
        'views/res_users_views.xml'
    ],
    'images': [
        'static/description/banner.jpg',
    ],
    'assets': {
        'web.assets_backend': [
            '/apg_auto_logout_idle/static/src/xml/systray.xml',
            '/apg_auto_logout_idle/static/src/js/systray.js',
            '/apg_auto_logout_idle/static/src/css/systray.css'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
