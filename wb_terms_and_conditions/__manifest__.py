# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) Wan Buffer Services (<https://wanbuffer.com/>).
#
#    For Module Support : support@wanbuffer.com  or Call : +91 9638442270
#
##############################################################################
{
    "name": "Dynamic Terms & Conditions for Sales, Purchase, and Invoices",
    'author': 'Wan Buffer Services',
    "license": "OPL-1",
    "website": "https://wanbuffer.com",
    "version": "0.0.1",

    "category": "Sales",

    "summary": """This module adds dynamic Terms and Conditions support for Sales,
                  Purchase, and Invoices in Odoo. It allows you to set and display Sales Terms and Conditions 
                  on quotations and sale orders (SO), including options like "Sale T&C", "Quotation T&C", and 
                  "Sales Terms and Conditions". For purchases, it supports PO terms such as "Purchase Order T&C" 
                  and "PO Terms and Conditions". On invoices and bills, you can manage and print terms like 
                  "Invoice T&C", "Vendor Bill Terms and Conditions", and "Print Terms and Conditions on Invoice".
                   It’s ideal for businesses needing clear, customizable T&C on all key documents.""",

    "description": """Each seller must declare their company policies through Terms and Conditions. 
                      This module allows you to define and display Terms and Conditions for Sales,
                       Purchases, and Invoices in Odoo. You can easily create T&C using an HTML editor 
                       and show them on quotations, sale orders, purchase orders, and invoices/bills. 
                       The terms are printed on related reports for transparency. Ideal for managing SO, 
                       PO, and invoice terms in a clear and professional format.""",
    "depends": [
        'sale_management','purchase','accountant','contacts',
    ],
    "data": [
        'security/wb_so_tnc_security.xml',
        'security/ir.model.access.csv',
        'views/terms_condition_views.xml',
        'views/res_partner_view.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/purchase_order_view.xml',
        'report/purchse_order_template.xml',
        'report/sale_order_templates.xml',
        'report/account_move_templates.xml',

    ],
    'demo': [],
    'post_init_hook': 'post_init_hook_sale',
    "images": ["static/description/background.png", ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "price": 0,
    "currency": "EUR"
}
