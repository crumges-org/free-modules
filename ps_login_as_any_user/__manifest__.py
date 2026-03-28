# -*- coding: utf-8 -*-

{
    # Module Info
    'name': 'Login As Any User',
    'version': '18.0.1.0.0',
    'category': 'Extra Tools',
    'summary': '''
        This module allows an admin (or authorized user) to log in as any user without needing their password.
        A “Back to Admin” button lets you return to your original account instantly.
        Perfect for debugging, support, and testing user-specific issues.
    ''',
    'description': '''
        login as user
        sudo login odoo
        admin access user account
        switch user odoo
        user impersonation odoo
        login without password odoo
        admin debug user
        support user login
        odoo sudo mode
   ''',

    # Author 
    'author': 'Pysquad Informatics',
    'website': 'https://pysquad.com',

    # Dependencies
    'depends': ['base', 'portal', 'website'],

    # Data File
    'data': [
        'security/ir.model.access.csv',
        'wizards/user_selection_views.xml',
        'views/back_to_admin_portal.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ps_login_as_any_user/static/src/js/systray_button.js',
            'ps_login_as_any_user/static/src/js/back_to_admin.js',
            'ps_login_as_any_user/static/src/xml/systray_button_templates.xml',
        ],
    },
    'images': [
        'static/description/banner_img.jpg'
    ],

    # Technical Spec.
    'installable': True,
    'auto-install': False,
    'application': False,
}
