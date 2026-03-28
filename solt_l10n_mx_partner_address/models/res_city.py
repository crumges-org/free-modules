# coding: utf-8
from odoo import fields, models


class City(models.Model):
    _inherit = 'res.city'
    _rec_names_search = ['name','zipcode', 'l10n_mx_code', 'state_id']

    l10n_mx_code = fields.Char(string="Code MX",
                               help="Code to use in the CFDI with external trade complement. It is based on the SAT catalog.")
    district_ids = fields.One2many('res.city.district', 'city_id', string="Districts", )
