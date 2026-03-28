# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
from odoo import fields, models


class ResLocality(models.Model):
    _name = 'res.locality'
    _description = 'Locality'
    _rec_names_search = ['name', 'code', 'state_id']

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    country_id = fields.Many2one('res.country', string='Country', required=True)
    state_id = fields.Many2one('res.country.state', 'State', domain="[('country_id', '=', country_id)]", required=True)
