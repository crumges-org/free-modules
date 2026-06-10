# -*- coding: utf-8 -*-

{
    'name': 'Odoo Studio Access Control',
    'summary': 'Restrict Odoo Studio visibility and access for selected users',
    'description': """
        Odoo Studio Access Control allows administrators to control who can access and use Odoo Studio within the 
        system.
        By default, any user with Settings access can use Studio. This module introduces an additional control layer, 
        enabling you to restrict Studio usage to selected users only.

        Key Features:
        - Restrict Odoo Studio access based on user groups
        - Hide Studio interface for unauthorized users
        - Prevent accidental or unauthorized customizations
        - Clean and seamless integration with existing Odoo permissions
        
        Benefits:
        - Improve system stability by limiting risky changes
        - Ensure only trained users modify views, fields, and reports
        - Maintain a clean and controlled user experience
        
    """,
    'author': 'CodeSphere Tech',
    'website': 'https://www.codespheretech.in/',
    'category': 'Extra Tools',
    'version': '18.0.1.0.0',
    'sequence': 0,
    'currency': 'USD',
    'price': '0.00',
    'depends': ['web', 'web_studio',],
    'data': [
        'security/security.xml',
    ],
    'assets': {
        'web.assets_backend': [
            "cst_studio_access_control/static/src/js/studio_access_systray.js",
        ],
    },
    'images': ["static/description/Banner.png"],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
