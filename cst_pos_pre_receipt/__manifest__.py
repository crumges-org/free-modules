# -*- coding: utf-8 -*-
{
    'name': 'POS Pre-Payment Receipt',
    "summary": "Print or preview POS receipt before completing payment for faster customer processing.",
    'description': """
        This module allows users to print or preview the POS receipt before making any payment. 
        It enables faster order confirmation, improves customer communication, and helps verify 
        order details prior to finalizing the transaction.

        Key Features:
        ✔ Print POS receipt before payment  
        ✔ Quick preview of the POS receipt  
        ✔ Improves order verification and customer confirmation  
        ✔ No core file changes – fully safe and modular  
        ✔ Works seamlessly with POS screen and custom layouts  

    """,
    "author": "CodeSphere Tech",
    "website": "https://www.codespheretech.in/",
    "category": "Point of Sale",
    "version": "18.0.1.0.0",
    "sequence": 0,
    "currency": "USD",
    "price": "0",
    "depends": ["point_of_sale", ],
    "data": [
        'views/res_config_settings_view.xml',
    ],
    "assets": {
        'point_of_sale._assets_pos': [
            'cst_pos_pre_receipt/static/src/**/*',
        ],
    },
    "images": ["static/description/Banner.png"],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
