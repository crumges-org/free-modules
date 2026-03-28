# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Technical field to hide country specific fields in company form view
    country_code = fields.Char(related='country_id.code', depends=['country_id'], compute_sudo=True)
    # == Address ==
    street_name = fields.Char('Street Name', compute='_compute_address', inverse='_inverse_street_name')
    street_number = fields.Char('House', compute='_compute_address', inverse='_inverse_street_number')
    street_number2 = fields.Char('Door', compute='_compute_address', inverse='_inverse_street_number2')
    l10n_mx_locality = fields.Char(string="Locality Name", compute='_compute_address', inverse='_inverse_l10n_mx_locality')
    l10n_mx_locality_id = fields.Many2one(comodel_name='res.locality', string="Locality", compute='_compute_address', inverse='_inverse_l10n_mx_locality_id',
                                          help="Optional attribute used in the XML that serves to define the locality where the domicile is located.")
    l10n_mx_colony = fields.Char(string="Colony Name", compute='_compute_address', inverse='_inverse_l10n_mx_colony')
    l10n_mx_colony_code = fields.Char(string="Colony Code", compute='_compute_address', inverse='_inverse_l10n_mx_colony_code',
                                      help="Note: Only use this field if this partner is the company address or if it is a branch office.\n"
                                           "Colony code that will be used in the CFDI with the external trade as Emitter colony. It must be a code "
                                           "from the SAT catalog.")
    district_id = fields.Many2one('res.city.district', string="District", compute='_compute_address', inverse='_inverse_district_id')
    city_id = fields.Many2one(comodel_name='res.city', string='City ID', compute='_compute_address', inverse='_inverse_city_id')
    country_enforce_districts = fields.Boolean(string="Enforce Districts", related='partner_id.country_enforce_districts', readonly=True)
    country_enforce_localities = fields.Boolean(string="Enforce Localities", related='partner_id.country_enforce_localities', readonly=True)
    country_enforce_cities = fields.Boolean(related='partner_id.country_enforce_cities', readonly=True)

    def _inverse_street_name(self):
        for company in self:
            company.partner_id.street_name = company.street_name

    def _inverse_street_number(self):
        for company in self:
            company.partner_id.street_number = company.street_number

    def _inverse_street_number2(self):
        for company in self:
            company.partner_id.street_number2 = company.street_number2

    def _inverse_city_id(self):
        for company in self:
            company.partner_id.city_id = company.city_id.id

    def _inverse_l10n_mx_locality(self):
        for company in self:
            company.partner_id.l10n_mx_locality = company.l10n_mx_locality

    def _inverse_l10n_mx_locality_id(self):
        for company in self:
            company.partner_id.l10n_mx_locality_id = company.l10n_mx_locality_id.id

    def _inverse_l10n_mx_colony(self):
        for company in self:
            company.partner_id.l10n_mx_colony = company.l10n_mx_colony

    def _inverse_l10n_mx_colony_code(self):
        for company in self:
            company.partner_id.l10n_mx_colony_code = company.l10n_mx_colony_code

    def _inverse_district_id(self):
        for company in self:
            company.partner_id.district_id = company.district_id.id

    def _get_company_address_field_names(self):
        return super()._get_company_address_field_names() + ['l10n_mx_locality', 'l10n_mx_locality_id', 'l10n_mx_colony', 'l10n_mx_colony_code', 'district_id', 'city_id']

    @api.model
    def default_get(self, default_fields):
        values = super().default_get(default_fields)
        values['country_id'] = self.env.ref('base.mx').id
        return values

    @api.onchange('district_id')
    def _onchange_district_id(self):
        if self.country_enforce_districts and self.district_id and self.zip != self.district_id.zip_code:
            self.zip = self.district_id.zip_code
            self.l10n_mx_colony = self.district_id.name
            self.l10n_mx_colony_code = self.district_id.code or ''
            self.city_id = self.district_id.city_id.id
            self.city = self.district_id.city_id.name
            self.state_id = self.district_id.city_id.state_id.id
            self.country_id = self.district_id.city_id.state_id.country_id.id

    @api.onchange('zip')
    def _onchange_zip(self):
        country = self.country_id or self.env.company.country_id
        if self.zip and self.country_enforce_districts and (not self.district_id or self.zip != self.district_id.zip_code):
            districts = self.env['res.city.district'].search([
                ('zip_code', '=', self.zip),
                ('city_id.state_id.country_id', '=', country.id),
            ])
            if not districts.exists():
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _('The zip code does not exists.'),
                    }
                }
            district = districts[0]
            self.district_id = district.id
            self.l10n_mx_colony = district.name
            self.l10n_mx_colony_code = district.code or ''
            self.city_id = district.city_id.id
            self.city = district.city_id.name
            self.state_id = district.city_id.state_id.id
            self.country_id = district.city_id.state_id.country_id.id

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id and self.country_enforce_cities and (not self.city_id or self.state_id != self.city_id.state_id):
            cities = self.env['res.city'].search([('state_id', '=', self.state_id.id)])
            city = cities[0]
            self.city_id = city.id
            self.city = city.name

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id and self.country_enforce_districts and (not self.district_id or self.city_id != self.district_id.city_id):
            districts = self.env['res.city.district'].search([
                ('city_id', '=', self.state_id.id),
            ])
            district = districts[0]
            self.district_id = district.id
            self.l10n_mx_colony = district.name
            self.l10n_mx_colony_code = district.code or ''

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        country_district_label = self.env.company.country_id.district_label
        if country_district_label:
            for node in arch.iterfind(".//field[@name='l10_mx_colony']"):
                node.set("string", country_district_label)
                node.set("placeholder", f"{country_district_label}...")
            for node in arch.iterfind(".//field[@name='district_id']"):
                node.set("string", country_district_label)
                node.set("placeholder", f"{country_district_label}...")
        for node in arch.iterfind(".//field[@name='city_id']"):
            node.set("string", _('Municipality'))
            node.set("placeholder", f"{_('Municipality')}...")
        for node in arch.iterfind(".//field[@name='city']"):
            node.set("string", _('Municipality'))
            node.set("placeholder", f"{_('Municipality')}...")
        return arch, view
