# -*- coding: utf-8 -*-
# Copyright (C) 2025 NEXA Solutions (<https://www.nexa-solutions.com>).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).
{
    'name': "Portal Customer Statement",

    'summary': "Allow Portal Users to View Customer Statement Report like Partner Ledger",

    'description': """
Portal Customer Statement
=========================

Empower your customers to view their account statements directly from the portal! 
A complete Partner Ledger experience with filtering, running balances, and PDF export.

Key Features:
-------------
* 📊 Partner Ledger in Portal
  Customers can view their complete account statement with the same columns as the backend Partner Ledger report.

* 📅 Flexible Date Filters
  Filter by Month, Quarter, Year, or Custom Date Range. Easy dropdown selection with intuitive UX.

* 💰 Running Balance
  Each transaction shows the cumulative balance. Initial balance is calculated for filtered periods automatically.

* 📄 PDF Export
  Customers can download their statement as a professionally formatted PDF document with company branding.

* 🔒 Secure Access
  Portal users can only see their own transactions. Data is filtered by partner ensuring complete privacy.

* 🎨 Modern Design
  Clean, responsive interface that matches Odoo's portal design. Works perfectly on desktop and mobile devices.

Statement Columns:
------------------
* Journal Code
* Account Code
* Reference / Name
* Invoice Date
* Due Date
* Matching Number
* Debit
* Credit
* Running Balance

How It Works:
-------------
1. Install the module from Apps
2. Customer logs into the portal and clicks on "Customer Statement"
3. Customer can filter by date, view their running balance, and export to PDF
    """,

    'author': "NEXA",
    'website': "https://www.nexa-solutions.com",
    'category': 'Accounting/Portal',
    'version': '18.0',
    'license': 'LGPL-3',

    'depends': ['portal', 'account'],

    'data': [
        # Report
        'reports/customer_statement_pdf_report.xml',
        # Views
        'views/portal_customer_statement.xml',
    ],

    'images': ['static/description/banner.png'],

    'installable': True,
    'application': False,
    'auto_install': False,
}
