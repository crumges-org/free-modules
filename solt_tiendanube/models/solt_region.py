# -*- coding: utf-8 -*-
from odoo import fields, models, _


class SoltRegion(models.Model):
    _name = 'solt.region'
    _description = 'Region'
    _order = 'name'

    name = fields.Char("Name", required=True, translate=True)
    code = fields.Char("Code", required=True)
    country_id = fields.Many2one(comodel_name='res.country', string='Country', required=True)

    _sql_constraints = [
        ('name_country_unique', 'UNIQUE(name, country_id)', 'Name and country must be unique.'),
    ]
