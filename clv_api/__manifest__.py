# noinspection PyStatementEffect
{
    'name': 'Cleverence Inventory for Odoo (barcode mobile app)',
    'author': 'Cleverence',
    'summary': 'Mobile Warehouse Automation Kit',
    'description': """
    This module provides integration with the Cleverence Inventory mobile app, enabling seamless communication between your Odoo system and the mobile devices.  

    As part of its functionality, the module collects the following data:  
    - **Host Information**: Unique host ID (hashed), OS details (platform, name, type).  
    - **Odoo Server Information**: Server URL, server version, database name, database settings (storage locations tracking, expiration dates tracking).  
    - **Module Information**: Module version, module settings.  
    - **Python Environment**: Python version.  

    This data is collected and used exclusively to improve the quality of the product.
    **No data is transferred to third parties.**

    For more details, please refer to our [Privacy Policy](https://www.cleverence.com/privacypolicy/).   
    """,
    'website': 'https://www.cleverence.com/solutions/welcome-wms-odoo-owners/',
    'live_test_url': 'https://clv.ae/odoo-live-preview-db',
    'category': 'Inventory',
    'version': '5.1.0',
    'depends': ['stock'],
    'data': [
        'data/ir_model.xml',
        'data/ir_model_fields.xml',
        'data/ir_actions_server.xml',
        'data/ir_ui_menu.xml',
        'data/ir_model_access.xml'
    ],
    'images': ['static/images/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
