# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, fields, api
from datetime import datetime, timedelta

class MailAutoResend(models.Model):
    _inherit = 'mail.mail'

    def resend_failed_emails(self):
        failed_emails = self.search([('state', '=', 'exception')])
        for email in failed_emails:
            email.write({'state': 'outgoing'})

class FailedEmailReport(models.Model):
    _name = 'mail.failed.email.report'
    _description = 'Failed Email Report'

    failed_count = fields.Integer(string="Failed Count")
    @api.model
    def send_failed_email_report(self):
        failed_count = self.env['mail.mail'].search_count([('state', '=', 'exception')])
        template = self.env.ref('resend_failed_emails_automatically.failed_email_report_template')

        if template:
            template.sudo().send_mail(
                self.id,
                force_send=True,
                email_values={'body_html': template.body_html.replace('${failed_count}', str(failed_count))}
            )