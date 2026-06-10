# -*- coding: utf-8 -*-
{
    'name': 'Analytic Distribution by Sales Team',
    'version': '18.0.1.0.2',
    'category': 'Accounting/Accounting',
    'summary': 'Add Sales Team as a matching criterion for analytic '
               'distribution models.',
    'description': """
Analytic Distribution by Sales Team
===================================

Extends ``account.analytic.distribution.model`` to add Sales Team as
an additional matching criterion, alongside the standard ones (partner,
partner category, product, product category, account prefix, company).

When a sale order or customer invoice belongs to a given sales team,
the analytic distribution assigned to that team is applied automatically.

Behaviour
---------
* Rules **without** a sales team behave exactly as before.
* Rules **with** a sales team only apply to documents that actually
  belong to that team (sale orders and journal entries).
* On documents that have no concept of a sales team (purchase orders,
  expenses, etc.), rules with a sales team are silently skipped — they
  never produce a false positive.
""",
    'author': 'Lune Makers SL',
    'website': 'https://lunemakers.com',
    'support': 'info@lunemakers.com',
    'license': 'LGPL-3',
    'depends': ['account', 'sale'],
    'data': [
        'views/account_analytic_distribution_model_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
}
