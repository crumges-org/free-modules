{

    'name': 'Auto Barcode Generator',
    'description': """
        Barcode Generator
    """,
    'summary': """
        Barcode Generator on Inventory
    """,
    'category': 'Barcode',
    "author": "One Stop Odoo",
    "website": "https://onestopodoo.com",
    "maintainer": 'One Stop Odoo',
    'version': '18.0.1.0.0',
    'license': 'OPL-1',
    # Dependencies
    'depends': ['stock'],
    # Views
    'data': [
        'views/product_category_ext.xml',
        'views/product_template_ext.xml',
    ],

    # Technical
    "installable": True,
    "auto_install": False,
    "images": 
    [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],
    "installable": True,
    "auto_install": False,
    'application': True,
}
