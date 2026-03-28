# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    l10n_mx_code = fields.Char('Code MX',
                               help="Code of country defined by the SAT in the catalog for the CFDI version 4.0 and new complements. "
                                    "It will be used in the CFDI to indicate the country reference.")
    enforce_districts = fields.Boolean(
        'Enforce Districts',
        help="Check this box to ensure every address created in that country has a 'District' chosen "
             "in the list of the City's districts."
    )
    enforce_localities = fields.Boolean(
        'Enforce Localities',
        help="Check this box to ensure every address created in that country has a 'Locality' chosen "
             "in the list of the City's Localities."
    )
    district_label = fields.Char(
        'District Label', translate=True, prefetch=True,
        help="Use this field if you want to change vat label.",
    )

    @api.onchange('enforce_cities')
    def _onchange_enforce_cities(self):
        if not self.enforce_cities:
            self.enforce_districts = False
            self.enforce_localities = False