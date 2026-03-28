# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import api, Command, fields, models, SUPERUSER_ID


class ResCompany(models.Model):
    _inherit = 'res.company'

    external_id = fields.Char("External ID")
    bearer_token = fields.Char("Bearer token")
    connector_id = fields.Many2one('solt.api.connector', string='API connector')
    state_initial_load = fields.Selection([('not_executed', 'Not executed'), ('completed', 'Completed'), ], string="Initial load status", default="not_executed")

    # social media
    social_pinterest = fields.Char('Pinterest account', prefetch=False)
    social_blog = fields.Char('Blog', prefetch=False)

    @api.model_create_multi
    def create(self, vals_list):

        if self.env.context.get('exclud_contact_from_sync', False):
            # create missing partners
            no_partner_vals_list = [vals for vals in vals_list if vals.get('name') and not vals.get('partner_id')]
            if no_partner_vals_list:
                partners = self.env['res.partner'].with_context(default_parent_id=False).create([
                        {'name': vals['name'], 'is_company': True, 'image_1920': vals.get('logo'), 'email': vals.get('email'), 'phone': vals.get('phone'), 'website': vals.get('website'), 'vat': vals.get('vat'), 'country_id': vals.get('country_id'), 'x_exclud_from_sync': True} for
                        vals in no_partner_vals_list])
                # compute stored fields, for example address dependent fields
                partners.flush_model()
                for vals, partner in zip(no_partner_vals_list, partners):
                    vals['partner_id'] = partner.id

            for vals in vals_list:
                # Copy delegated fields from root to branches
                if parent := self.browse(vals.get('parent_id')):
                    for fname in self._get_company_root_delegated_field_names():
                        vals.setdefault(fname, self._fields[fname].convert_to_write(parent[fname], parent))

            self.env.registry.clear_cache()
            companies = super().create(vals_list)

            # The write is made on the user to set it automatically in the multi company group.
            if companies:
                (self.env.user | self.env['res.users'].browse(SUPERUSER_ID)).write({'company_ids': [Command.link(company.id) for company in companies], })

            # Make sure that the selected currencies are enabled
            companies.currency_id.sudo().filtered(lambda c: not c.active).active = True

            companies_needs_l10n = companies.filtered('country_id')
            if companies_needs_l10n:
                companies_needs_l10n.install_l10n_modules()

            return companies
        else:
            return super(ResCompany, self).create(vals_list)

    # def write(self, values):  #     for company in self:  #         if company.partner_id:  #             company.partner_id.write({'x_exclud_from_sync': True})  #     return super(ResCompany, self).write(values)
