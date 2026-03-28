# -*- coding: utf-8 -*-
{
    'name': "Odoo ↔ Tiendanube Connector",
    'summary': "Bi-directional integration between Odoo and Tiendanube",
    'description': """
        Sync Tiendanube catalogs, orders, fulfillment and webhooks with Odoo 18.0.
        The connector centralizes product data, pricing, stock availability and shipment statuses for multi-warehouse sellers.
    """,
    'author': 'Soltein SA de CV',
    'website': 'https://www.soltein.mx',
    'support': 'soporte@soltein.mx',
    'maintainers': ['soltein'],
    'version': '18.0.1.1.1',
    'license': 'LGPL-3',
    'category': 'Sales/Multichannel',
    'application': True,
    'installable': True,
    'auto_install': False,
    # any module necessary for this one to work correctly
    'depends': [
        'solt_api_connector',
        'sale',
        'sale_stock',
        'stock',
        'solt_l10n_mx_partner_address',
        'stock_delivery',
    ],
    # always loaded
    'data': [
        'security/ir_groups.xml',
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'views/product_category_views.xml',
        'views/res_partner_views.xml',
        'views/solt_register_webhooks_views.xml',
        'views/solt_product_brand_views.xml',
        'views/product_multi_category_views.xml',
        'views/product_template_views.xml',
        'views/solt_product_image_views.xml',
        'views/sale_order_views.xml',
        'views/sale_order_multi_warehouse_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/solt_api_connector_views.xml',
        'views/solt_warehouse_sync_mapping_views.xml',
        'data/ir_config_parameter.xml',
        'data/tiendanube_data.xml',
        'data/endpoints_tiendanube_data.xml',
        'data/base_automation_data.xml',
        'data/ir_cron_data.xml',
        'data/config_meta_field_data.xml',
        'data/res_country.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'solt_tiendanube/static/src/scss/image_style.scss',
        ]
    },
    'images': ['static/description/odoo_tiendanube_main.png'],
    'post_init_hook': 'post_init_hook',
}
