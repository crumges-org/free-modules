# -*- coding: utf-8 -*-
#
#  ┌────────────────────────────────────────────────────────────────┐
#  │   Developed by: Code Sparks                                    │
#  │   Website: https://code-sparks.odoo.com                        │
#  │   LinkedIn: https://www.linkedin.com/company/codesparks-tech   │
#  │   Description: Login Audit Trail – Track IP, Device & Session  │
#  └────────────────────────────────────────────────────────────────┘
#
#  🔥 Empowering businesses with smart solutions! 💡

from odoo import api, models, fields

class LoginDetail(models.Model):
    _name = 'cs.login.audit'
    _description = 'User Login Audit Log'
    _rec_name = 'name'
    _order = 'login_time desc'
    _log_access = True

    name = fields.Char(string="Login Summary", compute="_compute_name", store=True)
    user_id = fields.Many2one('res.users', string="User", ondelete="set null", index=True)
    login_email = fields.Char(string="Login Email", required=True, index=True)
    ip_address = fields.Char(string="IP Address")
    user_agent = fields.Text(string="User Agent String")
    session_id = fields.Char(string="Session ID")
    login_time = fields.Datetime(string="Login Time", default=lambda self: fields.datetime.now(), required=True, index=True)
    company_id = fields.Many2one('res.company', string="Company")
    company_name = fields.Char(string="Company Name")
    db_name = fields.Char(string="Database")
    lang = fields.Char(string="Language")
    tz = fields.Char(string="Timezone")
    is_admin = fields.Boolean(string="Is Admin")
    device_type = fields.Char(string="Device Type")
    browser = fields.Char(string="Browser")
    os = fields.Char(string="Operating System")

    @api.depends('login_email', 'login_time', 'ip_address')
    def _compute_name(self):
        for rec in self:
            time_str = rec.login_time.strftime('%Y-%m-%d %H:%M:%S') if rec.login_time else 'Unknown Time'
            rec.name = f"{rec.user_id.name or 'Unknown'} @ {time_str} from {rec.ip_address or 'Unknown IP'}"
