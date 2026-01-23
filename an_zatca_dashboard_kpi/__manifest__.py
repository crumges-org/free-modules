# -*- coding: utf-8 -*-
{
    'name': 'ZATCA Dashboard KPIs',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations/Saudi Arabia',
    'summary': 'Display ZATCA submission status KPIs on Accounting Dashboard',
    'description': """
ZATCA Dashboard KPIs
====================

This module adds ZATCA (Zakat, Tax and Customs Authority) submission status KPIs
at the top of the Odoo Accounting Dashboard.

Features:
---------
* Company-wide ZATCA invoice status overview
* Real-time count of sent invoices
* Track pending invoices awaiting ZATCA submission
* Monitor invoices with submission errors
* View invoices with ZATCA warnings
* Clickable KPIs to filter and view relevant invoices
* Beautiful dashboard design matching Odoo style

Use Case:
---------
Saudi Arabian companies using ZATCA e-invoicing can quickly see their submission
status at a glance from the main accounting dashboard. No need to navigate to
different screens to check ZATCA compliance status.
    """,
    'author': 'Ahmed Nour',
    'website': 'https://odoosa.net',
    'maintainer': 'Ahmed Nour',
    'support': 'ahmednour@outlook.com',
    'license': 'LGPL-3',
    'price': 0.00,
    'currency': 'USD',
    'images': ['static/description/banner.png'],
    'depends': [
        'account',
        'l10n_sa_edi',
    ],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'an_zatca_dashboard_kpi/static/src/components/zatca_kpi_dashboard/zatca_kpi_dashboard.js',
            'an_zatca_dashboard_kpi/static/src/components/zatca_kpi_dashboard/zatca_kpi_dashboard.xml',
            'an_zatca_dashboard_kpi/static/src/views/account_dashboard_kanban/zatca_dashboard_kanban_renderer.js',
            'an_zatca_dashboard_kpi/static/src/views/account_dashboard_kanban/zatca_dashboard_kanban_renderer.xml',
            'an_zatca_dashboard_kpi/static/src/views/account_dashboard_kanban/zatca_dashboard_kanban_view.js',
            'an_zatca_dashboard_kpi/static/src/views/account_tree/zatca_account_tree_renderer.js',
            'an_zatca_dashboard_kpi/static/src/views/account_tree/zatca_account_tree_renderer.xml',
            'an_zatca_dashboard_kpi/static/src/views/account_tree/zatca_account_tree_view.js',
            'an_zatca_dashboard_kpi/static/src/css/zatca_dashboard.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
