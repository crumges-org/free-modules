# coding: utf-8
from odoo import fields, models, tools


class CityDistrict(models.Model):
    _name = 'res.city.district'
    _description = 'City District'
    _rec_names_search = ['name', 'code', 'zip_code', 'city_id', 'state_id']

    name = fields.Char(string="Name", required=True, index=True)
    code = fields.Char(string="Code")
    city_id = fields.Many2one('res.city', string="City", required=True, ondelete='restrict')
    zip_code = fields.Char(string="Zip Code", index=True)
    state_id = fields.Many2one(related='city_id.state_id', string="State", readonly=True, store=True)
    country_id = fields.Many2one(related='city_id.country_id', string="Country", readonly=True, store=True)

    def init(self):
        if not tools.index_exists(self._cr, 'res_city_district_zip_code_country_index'):
            tools.create_index(self._cr, 'res_city_district_zip_code_country_index', self._table, ['zip_code', 'country_id'])
