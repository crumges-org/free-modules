# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) Wan Buffer Services (<https://wanbuffer.com/>).
#
#    For Module Support : support@wanbuffer.com  or Call : +91 9638442270
#
##############################################################################

from odoo import api, fields, models


class SaleOrder(models.Model):
    """Inherit Sale Order to add Terms and Conditions functionality."""
    _inherit = 'sale.order'

    terms_and_conditions_id = fields.Many2one(
        'wb.terms.condition',
        string="Sales Terms and Conditions",
        help="Select the terms and conditions to apply to this sale order.",tracking = True
    )
    show_in_report = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        required=True,
        default='yes',
        string='Display in Reports?',
        help="Show these terms and conditions on printed reports by default.",tracking=True)

    terms_and_conditions_detail = fields.Html(
        string="Terms and Conditions Detail",
        help="The text of the terms and conditions for this sale order.")

    @api.onchange('partner_id')
    def _onchange_partner_terms_and_conditions(self):
        """Auto-fill T&C fields from partner defaults."""
        if self.partner_id:
            self.terms_and_conditions_id = self.partner_id.sale_term_condition_id.id if self.partner_id.sale_term_condition_id else False
            self.terms_and_conditions_detail = self.partner_id.sale_terms_detail or ''
        else:
            self.terms_and_conditions_id = False
            self.terms_and_conditions_detail = ''

    @api.onchange('terms_and_conditions_id')
    def _onchange_terms_and_conditions(self):
        """Update T&C detail when T&C is changed."""
        if self.terms_and_conditions_id:
            self.terms_and_conditions_detail = self.terms_and_conditions_id.tnc_con or ''
        else:
            self.terms_and_conditions_detail = ''






