# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, fields, api, exceptions


class ResendEmailSettings(models.Model):
    _name = 'resend.email.settings'
    _description = 'Resend Email Settings'
    _rec_name = 'name'

    name = fields.Char(default="Resend Email Configuration", readonly=True)
    active = fields.Boolean(string="Enable Resend", default=True)
    resend_interval = fields.Integer(string="Resend Interval", default=10)
    resend_unit = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days')
    ], string="Interval Unit", default="minutes")
    enable_report = fields.Boolean(string="Enable Daily Report", default=True)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        cron = self.env.ref('resend_failed_emails_automatically.cron_resend_failed_emails')
        print("cron==> ", cron.interval_number)
        cron.interval_number = res.resend_interval
        cron.interval_type = res.resend_unit
        print(res)
        return res