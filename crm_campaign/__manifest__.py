# -*- coding: utf-8 -*-
{
    'name': "CRM Campaign",

    'summary': "Configure campaigns directly from the Sales menu in the CRM app",

    'description': """
Configure campaigns directly from the Sales menu in the CRM app
""",

    'author': "JD Solutions",
    'website': "https://javierdiez.netlify.app/",
    'license': 'AGPL-3',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'CRM',
    'version': '18.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/campaign_views.xml',
        'views/campaign_menus.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
        "images": ['static/images/banner.png', 'static/description/icon.png'],
    'installable': True,
    'auto_install': False,
}

