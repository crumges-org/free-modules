# -*- coding: utf-8 -*-
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID


class City(models.Model):
    _inherit = 'res.city'

    def _compute_display_name(self):
        if self.env.context and self.env.context.get('is_from_location_mst'):
            for city in self:
                city.display_name = city.name
        else:
            return super()._compute_display_name()
