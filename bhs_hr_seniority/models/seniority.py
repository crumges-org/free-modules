import datetime
from datetime import datetime, timedelta
from _datetime import date, datetime
from odoo import models, fields, api, _


class Bhseniority(models.Model):
    _inherit = 'hr.employee'

    seniority = fields.Char(string='Seniority', compute='_compute_seniority')
    
    def _compute_seniority(self):
        # self.joined_date = self.employee_id.joining_date if self.employee_id.joining_date else ''
        for rec in self:
            today = date.today()
            if rec.first_contract_date:
                days = (today - rec.first_contract_date).days
                if days < 365:
                    month = int(days) // 30
                    rec.seniority = _('%s months', month)
                else:
                    year = int(days) // 365
                    month = (int(days) - year * 365) // 30
                    rec.seniority = _('%s years %s months', year, month)
            else:
                rec.seniority = 'Not define'
