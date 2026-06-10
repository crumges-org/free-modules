# Part of Axoline Layout Editor. See LICENSE file for full copyright and licensing details.
{
    'name': 'Axoline PDF Report Designer FREE | Drag & Drop Layout Editor',
    'version': '18.0.1.1.0',
    'category': 'Reporting',
    'summary': 'Free No-Code WYSIWYG Drag & Drop Report Designer for Odoo invoices — design custom Invoice PDF layouts without coding',
    'description': """
Axoline PDF Report Designer — Drag & Drop Layout Editor (FREE)
==============================================================

The **free** visual **Report Designer** and **PDF Editor** for Odoo
invoices. Redesign your **customer invoices, credit notes and vendor bills**
with a true **WYSIWYG** drag and drop interface — no XML, no QWeb coding,
no developer required.

A powerful **Odoo Studio alternative** dedicated to invoice PDF reports.

What's included in the FREE version
------------------------------------

* **Invoice layouts** (``account.move``): customer invoices, vendor bills,
  credit notes and receipts.
* **Full Drag & Drop Editor** with real-time canvas and **Live PDF Preview**.
* **Complete Block Library (15+ blocks)**: Company Header, Sender Line,
  Company Details, Document Title, Recipient Address, Introduction Text,
  Info Table, Line Items, Totals & Taxes, Payment & Shipping Info, Free
  Text, Two-Column Layout, Spacer, Separator, Page Break and Footer.
* **Per-Block Properties**: fonts, colors, spacing, alignment, page margins,
  headers and footers — all configurable, no code.
* **Classic Template**: start from a professional layout in one click.
* **Test Print & Sample Record Picker**: preview your invoice with real data.
* **Multi-Language** (English & German) and **multi-company** aware.

Upgrade to PRO — all documents & all templates
-----------------------------------------------

Need the same polished layout on more than invoices? The **PRO** add-on
unlocks **every QWeb PDF report** and **all built-in templates**:

* **All document types**: Quotations & Sale Orders, Purchase Orders & RFQs,
  Delivery Slips / Pickings, Payment Receipts and **any** custom QWeb PDF.
* **All built-in templates**: Modern, Compact and Letterhead (in addition
  to the free Classic template).

Get it here → `Axoline PDF Report Designer PRO
<https://apps.odoo.com/apps/modules/18.0/axoline_layout_editor_pro>`_

(The PRO add-on installs on top of this free module and preserves all your
existing layouts, templates and settings.)

Why Axoline Report Designer?
----------------------------

If you have ever struggled with QWeb XML, complex inheritance, or the
limitations of Odoo Studio for invoice PDFs, this module is for you. Get
the flexibility of a custom developer without the cost — for free.

Keywords
--------

Report Designer, Layout Editor, PDF Editor, QWeb Designer, Invoice
Template, Custom Invoice Template, Invoice Branding, Corporate Identity
Reports, No Code Report Customization, WYSIWYG PDF Editor, Easy Report
Styling, Edit Reports without Coding, Flexible Document Styling, Odoo
Studio Alternative, Free Invoice Designer, Drag and Drop Report Designer.
    """,
    'author': 'Axoline',
    'website': 'https://www.axoline.de',
    'support': 'support@axoline.de',
    'license': 'OPL-1',
    'price': 0.00,
    'currency': 'EUR',
    'live_test_url': 'https://odoodemo.axoline.de/',
    'images': [
        'images/main_screenshot.png',
        'images/screenshot_reports.png',
        'images/screenshot_layouts.png',
        'images/screenshot_templates.png',
        'images/screenshot_template_picker.png',
    ],
    'depends': [
        'base',
        'web',
        'account',
        'sale',
        'purchase',
        'stock',
    ],
    'data': [
        'security/layout_security.xml',
        'security/ir.model.access.csv',
        'data/layout_templates.xml',
        'views/report_templates.xml',
        'views/layout_custom_views.xml',
        'views/layout_template_views.xml',
        'views/ir_actions_report_views.xml',
        'views/layout_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'axoline_layout_editor/static/src/css/layout_editor.css',
            'axoline_layout_editor/static/src/js/layout_editor.js',
            'axoline_layout_editor/static/src/xml/layout_editor.xml',
        ],
        'web.report_assets_common': [
            'axoline_layout_editor/static/src/css/report_axoline.css',
        ],
    },
    'installable': True,
    'application': True,
}
