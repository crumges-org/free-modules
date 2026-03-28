from odoo import models, fields, api


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    event = fields.Char("Event", prefetch=False)

    def _prepare_tn_webhooks(self, company):
        self.ensure_one()
        return {
            'name': self.name,
            'event': self.event,
            'automation_id': self.id,
            'company_id': company.id,
        }