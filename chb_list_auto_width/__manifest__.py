# -*- coding: utf-8 -*-
{
    "name": "Smart List Auto Width",
    "version": "18.0.0",
    "summary": "Automatically adjust Odoo list view column widths based on content and headers",
    "description": """
        Smart List Auto Width automatically adjusts column widths in all Odoo list views, 
        including embedded One2many and Many2many lists in forms. It ensures that columns are 
        always readable, taking into account both column headers and cell content.
        
        Features:
        - Auto-fit columns based on content and header
        - Header-first logic: column header width is preserved if larger than content
        - Works for text, numeric, selection fields, and editable cells
        - Global effect: works across all list views in menus and forms
        - Lightweight: pure front-end patch, no server restart required
        - Adds proper padding to prevent content from touching cell borders
    """,
    "category": "User Interface",
    "author": "Chen Han Bin",
    "website": "",
    "support": "jeffreyfirstten@163.com",
    "currency": "EUR",
    "price": "0.0",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "assets": {
        "web.assets_backend": [
            "chb_list_auto_width/static/src/js/auto_width_list_renderer.js",
        ],
    },
    "images": [
        "static/description/icon.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
