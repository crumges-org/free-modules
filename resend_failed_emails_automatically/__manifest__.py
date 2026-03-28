# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'Email Auto Resend',
    'version': '18.0',
    'summary': """
        Automatically resends failed emails in Odoo and optionally sends a daily report of email failures.
        resend emails
        email failure
        auto resend
        mail exception
        failed email report
        email monitoring
        email automation
        Odoo email scheduler
        cron resend mail
        mail.mail state exception
        retry email sending
        outgoing email
        email delivery error
        scheduled email resend
        daily email report
        Odoo email queue
        failed mail handler
        automatic email retry
        Odoo mail automation
        mail failure notifications
        Odoo16
        Odoo17
        Odoo18
        TUS
        tus
        techultra solutions
        techultra
        techultra solutions private limited
        """,
    'author': 'TechUltra Solutions Private Limited',
    'company': 'TechUltra Solutions Private Limited',
    'website': "https://www.techultrasolutions.com/",
    'description': """
        This module monitors failed emails in the system and automatically retries sending them at a configured interval. It also provides an option to send a daily report showing the number of failed emails. Admins can easily enable or disable the resend and report features via a simple settings view.
        resend emails
        email failure
        auto resend
        mail exception
        failed email report
        email monitoring
        email automation
        Odoo email scheduler
        cron resend mail
        mail.mail state exception
        retry email sending
        outgoing email
        email delivery error
        scheduled email resend
        daily email report
        Odoo email queue
        failed mail handler
        automatic email retry
        Odoo mail automation
        mail failure notifications
        Odoo16
        Odoo17
        Odoo18
        TUS
        tus
        techultra solutions
        techultra
        techultra solutions private limited
    """,
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_resend_data.xml',
        'data/mail_template.xml',
        'views/resend_settings_views.xml',
    ],
    "images": [
        "static/description/main_screen.gif"
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
