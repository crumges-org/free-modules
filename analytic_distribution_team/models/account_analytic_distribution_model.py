# -*- coding: utf-8 -*-
# Copyright 2025 Lune Makers SL
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).
from odoo import fields, models


class AccountAnalyticDistributionModel(models.Model):
    _inherit = 'account.analytic.distribution.model'

    team_id = fields.Many2one(
        comodel_name='crm.team',
        string='Sales Team',
        ondelete='cascade',
        help='If set, this rule only applies when the document (sale order '
             'or customer invoice) belongs to this sales team.',
    )

    def _get_default_search_domain_vals(self):
        """Inject ``team_id: False`` as a default search value.

        Without this, rules with ``team_id`` set would also match documents
        that do not provide a team at all (e.g. purchase orders, expenses),
        producing false positives. Same pattern used by the ``analytic``
        module for ``product_id`` and ``product_categ_id``.
        """
        return super()._get_default_search_domain_vals() | {
            'team_id': False,
        }
