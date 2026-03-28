from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_private = fields.Boolean("Private Contact", default=False, groups='private_contact.group_private_contact')
