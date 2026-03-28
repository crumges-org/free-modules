# -*- coding: utf-8 -*-

{
    "name": "Disable Update Quantity Feature",
    "version": "18.0.0.0",
    "category": "Warehouse",
    'summary': 'Restrict product quantity updates for particular users to maintain accurate stock records',
    "description": """TRestrict product quantity updates for particular users to maintain accurate stock records.""",
    'author': 'Apagen Solutions Pvt Ltd',
    'company': 'Apagen Solutions Pvt Ltd',
    'maintainer': 'Apagen Solutions Pvt Ltd',
    'website': "https://www.apagen.com",
    "depends": ["stock"],
    "data": [
        'security/product_security.xml',
        'views/product.xml',
    ],
    "License": 'LGPL-3',
    "installable": True,
    "application": True,
    "auto_install": False,
    "images": ['static/description/banner.jpg'],
}


