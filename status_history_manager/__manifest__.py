{
    'name': 'Field Tracker History Management',
    'version': '18.0.1.1.0',
    'category': 'Inventory/Purchase',
    'summary': 'Track status, price & quantity changes in Purchase, Sales and Inventory with employee audit log',

    'description': """
Audit log - Status & Changes History Manager
=================================

Track every important change across your business documents — automatically.

**What is recorded:**
- Status / State Changes
- Price Changes (Unit Price)
- Quantity Changes
- Discount Changes (Sales)

**Tracked on:**
- Purchase Orders & Lines
- Sales Orders & Lines
- Inventory / Stock Pickings & Moves

**Each log entry shows:**
- Employee Name (who made the change)
- What changed (Status / Price / Quantity / Discount)
- From value -> To value
- Date & Time of change
- Product reference (for line changes)

**Access Control:**
- History User  -- can view Change History tab & per-app menus
- History Manager -- full access including the global All Change History log

Compatible with Odoo 18.
    """,

    'author': 'Techie Buddy',
    'website': '',
    'support': 'vsmanoj144@gmail.com',
    'maintainer': 'Techie Buddy',

    'license': 'LGPL-3',
    'price': 0.00,
    'currency': 'USD',

    'depends': [
        'purchase',
        'sale_management',
        'stock',
        'hr',
    ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/history_log_views.xml',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/menu_views.xml',
    ],

    'images': [
        'static/description/banner.png',
        'static/description/screenshot_01_purchase.png',
        'static/description/screenshot_02_sales.png',
        'static/description/screenshot_03_inventory.png',
        'static/description/screenshot_04_global_history.png',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
