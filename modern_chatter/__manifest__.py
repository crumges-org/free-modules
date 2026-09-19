{
    'name': 'Modern Chatter | Filter Chatter, Search Chatter, Advance Chatter',
    'version': '17.0.1.0.0',
    'summary': 'Modern chatter with search and clean UI for Odoo',
    'category': 'Productivity',
    'author': 'Northlight',
    'website': 'https://alaskahub.io',
    'license': 'LGPL-3',
    'price': 0.0,
    'currency': 'EUR',
    'support': 'alisa@alaskahub.io',
    'depends': ['mail'],
    'assets': {
        'web.assets_backend': [
            'modern_chatter/static/src/scss/modern_chatter.scss',
            'modern_chatter/static/src/components/modern_chatter_thread/modern_chatter_thread.xml',
            'modern_chatter/static/src/components/modern_chatter_thread/modern_chatter_thread.js',
        ],
    },
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
