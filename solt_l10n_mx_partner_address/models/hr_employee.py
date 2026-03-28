# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models, _


class HrEmployeePrivate(models.Model):
    _inherit = "hr.employee"

    private_locality = fields.Char(string="Locality Name", groups="hr.group_hr_user")
    private_locality_id = fields.Many2one(comodel_name='res.locality', string="Locality", groups="hr.group_hr_user",
                                          help="Optional attribute used in the XML that serves to define the locality where the domicile is located.")
    private_colony = fields.Char(string="Colony Name", groups="hr.group_hr_user")
    private_colony_code = fields.Char(string="Colony Code", groups="hr.group_hr_user",
                                      help="Colony code that will be used in the CFDI. It must be a code "
                                           "from the SAT catalog.")
    private_street_number = fields.Char('House', groups="hr.group_hr_user")
    private_street_number2 = fields.Char('Door', groups="hr.group_hr_user")
    private_city_id = fields.Many2one(comodel_name='res.city', string='City ID', groups="hr.group_hr_user")

    country_enforce_districts = fields.Boolean(string="Enforce Districts", compute='_compute_enforce', readonly=True, prefetch=False)
    country_enforce_localities = fields.Boolean(string="Enforce Localities", compute='_compute_enforce', readonly=True, prefetch=False)
    country_enforce_cities = fields.Boolean(related=False, compute='_compute_enforce', readonly=True, prefetch=False)
    private_district_id = fields.Many2one('res.city.district', string="District", prefetch=False)

    @api.depends('private_country_id')
    @api.onchange('private_country_id')
    def _compute_enforce(self):
        country = self.env.company.country_id
        for employee in self:
            employee.country_enforce_districts = employee.private_country_id.enforce_districts or (not employee.private_country_id and country.enforce_districts)
            employee.country_enforce_localities = employee.private_country_id.enforce_localities or (not employee.private_country_id and country.enforce_localities)
            employee.country_enforce_cities = employee.private_country_id.enforce_cities or (not employee.private_country_id and country.enforce_cities)

    @api.model
    def default_get(self, default_fields):
        values = super().default_get(default_fields)
        values['private_country_id'] = self.env.company.country_id.id or self.env.ref('base.mx').id
        return values

    @api.onchange('private_district_id')
    def _onchange_district_id(self):
        if self.country_enforce_districts and self.private_district_id and self.private_zip != self.private_district_id.zip_code:
            self.private_zip = self.private_district_id.zip_code
            self.private_colony = self.private_district_id.name
            self.private_colony_code = self.private_district_id.code or ''
            self.private_city_id = self.private_district_id.city_id.id
            self.private_city = self.private_district_id.city_id.name
            self.private_state_id = self.private_district_id.city_id.state_id.id
            self.private_country_id = self.private_district_id.city_id.state_id.country_id.id

    @api.onchange('private_zip')
    def _onchange_private_zip(self):
        country = self.private_country_id or self.env.company.country_id
        if self.private_zip and self.country_enforce_districts and (not self.private_district_id or self.private_zip != self.private_district_id.zip_code):
            districts = self.env['res.city.district'].search([
                ('zip_code', '=', self.private_zip),
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
            self.private_district_id = district.id
            self.private_colony = district.name
            self.private_colony_code = district.code or ''
            self.private_city_id = district.city_id.id
            self.private_city = district.city_id.name
            self.private_state_id = district.city_id.state_id.id
            self.private_country_id = district.city_id.state_id.country_id.id

    @api.onchange('private_state_id')
    def _onchange_state_id(self):
        if self.private_state_id and self.country_enforce_cities and (not self.private_city_id or self.private_state_id != self.private_city_id.state_id):
            cities = self.env['res.city'].search([('state_id', '=', self.private_state_id.id)])
            city = cities[0]
            self.private_city_id = city.id
            self.private_city = city.name

    @api.onchange('private_city_id')
    def _onchange_private_city_id(self):
        if self.private_city_id and self.country_enforce_districts and (not self.private_district_id or self.private_city_id != self.private_district_id.city_id):
            districts = self.env['res.city.district'].search([
                ('city_id', '=', self.private_state_id.id),
            ])
            district = districts[0]
            self.private_district_id = district.id
            self.private_colony = district.name
            self.private_colony_code = district.code or ''

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        country_district_label = self.env.company.country_id.district_label
        if country_district_label:
            for node in arch.iterfind(".//field[@name='private_colony']"):
                node.set("string", country_district_label)
                node.set("placeholder", f"{country_district_label}...")
            for node in arch.iterfind(".//field[@name='private_district_id']"):
                node.set("string", country_district_label)
                node.set("placeholder", f"{country_district_label}...")
        for node in arch.iterfind(".//field[@name='private_city_id']"):
            node.set("string", _('Municipality'))
            node.set("placeholder", f"{_('Municipality')}...")
        for node in arch.iterfind(".//field[@name='private_city']"):
            node.set("string", _('Municipality'))
            node.set("placeholder", f"{_('Municipality')}...")
        return arch, view
