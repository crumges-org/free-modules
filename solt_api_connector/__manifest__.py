# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
{
    'name': "API Connector",
    'summary': "Configurable API orchestration framework for Odoo 18",
    'description': """API Connector
===================

Model, execute, and monitor integrations with any REST API directly from Odoo. Define multiple
connections, map payloads visually, orchestrate automations, and log every call with retry and
webhook support.
""",
    'author': 'Soltein SA de CV',
    'maintainers': ['soltein'],
    'website': 'https://www.soltein.mx',
    'support': 'soporte@soltein.mx',
    'category': 'Tools/Connectivity',
    'version': '18.0.1.0.1',
    'license': 'LGPL-3',
    'depends': ['base', 'base_automation', 'social_media'],
    'application': True,
    'installable': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_company.xml',
        'views/solt_api_call_log.xml',
        'views/solt_api_connector.xml',
        'views/solt_api_endpoint.xml',
        'views/base_automation.xml',
        'views/ir_actions_server.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'solt_api_connector/static/src/scss/**/*',
        ],
        'web.assets_common': [
            'solt_api_connector/static/description/icon.png',
        ],
    },
    'images': ['static/description/icon_module.png'],
}