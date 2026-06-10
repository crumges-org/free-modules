# -*- coding: utf-8 -*-
# Copyright 2025 Lune Makers SL
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).
from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('order_id.partner_id', 'order_id.team_id', 'product_id')
    def _compute_analytic_distribution(self):
        """Override the standard computation to inject the sales team
        into the matcher arguments. Unlike ``account.move.line``,
        ``sale.order.line`` does not expose a dedicated hook
        (``_get_analytic_distribution_arguments``) in core, so the
        method has to be reimplemented here.

        Keep this method in sync with
        ``odoo/addons/sale/models/sale_order_line.py`` on Odoo upgrades.
        """
        for line in self:
            if not line.display_type:
                distribution = line.env['account.analytic.distribution.model']._get_distribution({
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_id.categ_id.id,
                    "partner_id": line.order_id.partner_id.id,
                    "partner_category_id": line.order_id.partner_id.category_id.ids,
                    "company_id": line.company_id.id,
                    "team_id": line.order_id.team_id.id,
                })
                line.analytic_distribution = distribution or line.analytic_distribution
