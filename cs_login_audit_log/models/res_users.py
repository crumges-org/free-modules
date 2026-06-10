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

from odoo import api, models
from odoo.http import request
from user_agents import parse

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _check_credentials(self, password, user_agent_env):
        result = super(ResUsers, self)._check_credentials(password, user_agent_env)

        ip_address = request.httprequest.environ.get('REMOTE_ADDR')
        user_agent_str = request.httprequest.headers.get('User-Agent')
        session_id = getattr(request.session, 'sid', None)

        user_agent = parse(user_agent_str or "")
        device_type = (
            'Mobile' if user_agent.is_mobile else
            'Tablet' if user_agent.is_tablet else
            'PC' if user_agent.is_pc else
            'Bot' if user_agent.is_bot else
            'Unknown'
        )

        vals = {
            'name': self.name,
            'user_id': self.id,
            'login_email': self.login,
            'ip_address': ip_address,
            'user_agent': user_agent_str,
            'session_id': session_id,
            'company_id': self.company_id.id if self.company_id else None,
            'company_name': self.company_id.name if self.company_id else None,
            'db_name': request.db,
            'lang': self.lang,
            'tz': self.tz,
            'is_admin': self.has_group('base.group_system'),
            'device_type': device_type,
            'browser': user_agent.browser.family,
            'os': user_agent.os.family,
        }

        self.env['cs.login.audit'].sudo().create(vals)
        return result
