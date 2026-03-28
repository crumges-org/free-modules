# -*- coding: utf-8 -*-
{
    'name': 'POS Product Brand',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add product brands to POS with filtering capability',
    'description': """
POS Product Brand
=================
This module adds brand management to Point of Sale:

Features:
---------
* Create and manage product brands
* Assign brands to products
* Configure available brands per POS
* Filter products by brand in POS interface
* Brand selector in POS product screen

Use Case:
---------
Perfect for retail stores that carry multiple brands and want to
quickly filter products by brand in the POS interface.
    """,
    'author': 'Ahmed Magdy',
    'website': 'https://idealitsetup.com/',
    'maintainer': 'Ahmed Magdy',
    'support': 'qarsan4@gmail.com',
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'USD',
    'images': ['static/description/banner.png'],
    'depends': [
        'point_of_sale',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_brand_views.xml',
        'views/product_template_views.xml',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'am_product_brand/static/src/js/**/*',
            'am_product_brand/static/src/xml/**/*',
            'am_product_brand/static/src/css/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
