{
    'name': 'Main Menu',
    'version': '18.0.1.0.0',
    'category': 'Technical/Technical',
    'sequence': 1,
    'summary': """The Main Menu module for Odoo Community Edition provides a streamlined dashboard for seamless navigation across core modules.
                  Featuring dynamic widgets for real-time date display and administrator-managed announcements, it enhances user efficiency.
                  Custom bookmarking allows users to organize essential menus and external links, improving workflow and accessibility within
                  the Odoo backend.""",
    'description': 'This module provides a centralized main menu for Odoo Community Edition, allowing users to quickly access core modules and enhance their workflow. It features widget functionality for displaying the current date and posting announcements, which can be managed by administrators.Users can create bookmarks for quick access to essential menus, as well as external links, improving overall navigation efficiency.',
    'author': 'Zehntech Technologies Inc.',
    'maintainer': 'Zehntech Technologies Inc.',
    'company': 'Zehntech Technologies Inc.',
    'website': 'https://zehntech.com',
    'depends': ['web', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/main_menu_views.xml',
        'views/menu_bookmark_views.xml',
        'views/res_config_setting_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zehntech_main_menu/static/src/components/**/*',
        ],
    },
    'images': [
        'static/description/banner.gif',
        
    ],
    'license': 'OPL-1',
    'auto_install': False,
    'application': True,
    'installable': True,
}