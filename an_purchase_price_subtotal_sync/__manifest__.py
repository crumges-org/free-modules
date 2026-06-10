{
    "name": "Purchase Price Subtotal Sync",
    "summary": "Adds bidirectional synchronization between price_unit and price_subtotal in Purchase Orders.",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "author": "Ahmed Nour",
    "website": "http://www.odoosa.net",
    "license": "AGPL-3",
    "depends": ["purchase"],
    "description": """
Purchase Price Subtotal Sync
============================
This module, developed by Ahmed Nour, adds bidirectional synchronization between price_unit and price_subtotal 
in Purchase Orders. 

Key Features:
-------------
- Automatically updates price_subtotal when price_unit or product_qty changes.
- Automatically recalculates price_unit when price_subtotal is manually updated.
- Error handling for scenarios with zero quantity.
- Seamless integration with Odoo's native Purchase module.

Developer Information:
----------------------
- Name: Ahmed Nour
- Email: ahmednour@outlook.com
- Website: www.odoosa.net
""",
    "data": [
        # XML files can be added here if required
    ],
    "images": [
        "static/description/banner.png",
        "static/description/feature.png",
    ],
    "installable": True,
    "application": False,
    "price": 0.0,
    "currency": "EUR",
    "maintainer": "Ahmed Nour",
    "support": "ahmednour@outlook.com",
    "live_test_url": "http://www.odoosa.net/web/demo",
    "demo": [],
    "external_dependencies": {
        "python": [],
    },
}
