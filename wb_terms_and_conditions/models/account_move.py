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


class AccountMove(models.Model):
    _inherit = 'account.move'

    tnc_id = fields.Many2one(
        'wb.terms.condition',
        string="Terms and Conditions",
        domain="[('term_type', '=', term_type_domain), '|', ('company_ids', '=', False), ('company_ids', 'in', [company_id])]",
        help="Select applicable Terms & Conditions.",tracking = True
    )
    terms_and_conditions_detail = fields.Html(string="Details")
    show_in_report = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        required=True, default='yes', string='Show on Report?',tracking = True
    )

    term_type_domain = fields.Selection(
        selection=[('sale', 'Sales'), ('purchase', 'Purchase')],
        compute="_compute_term_type_domain",tracking = True,
        store=False
    )

    @api.depends('move_type')
    def _compute_term_type_domain(self):
        for record in self:
            if record.move_type in ['out_invoice', 'out_refund']:   # Sales Invoice or Customer Credit Note
                record.term_type_domain = 'sale'
            elif record.move_type in ['in_invoice', 'in_refund']:   # Vendor Bill or Vendor Credit Note
                record.term_type_domain = 'purchase'
            else:
                record.term_type_domain = False

    @api.onchange('partner_id')
    def _onchange_partner_terms(self):
        if self.partner_id:
            if self.move_type in ['out_invoice', 'out_refund']:
                self.tnc_id = self.partner_id.sale_term_condition_id.id or False
                self.terms_and_conditions_detail = self.partner_id.sale_terms_detail or ''
            elif self.move_type in ['in_invoice', 'in_refund']:
                self.tnc_id = self.partner_id.purchase_term_condition_id.id or False
                self.terms_and_conditions_detail = self.partner_id.purchase_terms_detail or ''
        else:
            self.tnc_id = False
            self.terms_and_conditions_detail = ''

    @api.onchange('tnc_id')
    def _onchange_tnc_id(self):
        self.terms_and_conditions_detail = self.tnc_id.tnc_con if self.tnc_id else ''
