# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, api


class MailAutoResend(models.Model):
    _name = 'mail.auto.resend.cron'
    _description = 'Automatically Resend Failed Emails'

    @api.model
    def resend_failed_emails(self):
        """Resend failed emails based on user-configured interval."""
        if not self.env['resend.email.settings'].search([], limit=1).active:
            return  # If disabled, exit

        failed_mails = self.env['mail.mail'].search([('state', '=', 'exception')])
        for mail in failed_mails:
            mail.write({'state': 'outgoing'})  # Move to Outgoing
            mail.send(auto_commit=True)  # Attempt resend
        return True

    @api.model
    def send_failed_email_report(self):
        """Send a report with the total failed emails count."""
        settings = self.env['resend.email.settings'].search([], limit=1)
        if not settings.enable_report:
            return  # If report is disabled, exit

        failed_count = self.env['mail.mail'].search_count([('state', '=', 'exception')])
        template = self.env.ref('resend_failed_emails_automatically.failed_email_report_template', raise_if_not_found=False)

        if template:
            template.with_context(failed_count=failed_count).sudo().send_mail(
                self.env.user.id, force_send=True
            )