# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) Wan Buffer Services (<https://wanbuffer.com/>).
#
#    For Module Support : support@wanbuffer.com  or Call : +91 9638442270
#
##############################################################################

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    sale_term_condition_id = fields.Many2one(
        'wb.terms.condition',
        string="Sales Terms & Conditions",tracking = True)
    sale_terms_detail = fields.Html(string="Sales Terms Detail")

    purchase_term_condition_id = fields.Many2one(
        'wb.terms.condition',
        string="Purchase Terms & Conditions")
    purchase_terms_detail = fields.Html(string="Purchase Terms Detail",)

    def write(self, vals):
        """Retrieve old terms, update the record, then propagate updates after `super` call."""
        old_terms_map = {}

        for record in self:
            old_terms_map[record.id] = {
                'sale': record.sale_terms_detail,
                'purchase': record.purchase_terms_detail
            }

        # Execute the write operation first
        result = super(ResPartner, self).write(vals)

        # After write, update related records using previous values
        if 'sale_terms_detail' in vals or 'purchase_terms_detail' in vals:
            for record in self:
                old_sale_tnc = old_terms_map.get(record.id, {}).get('sale', False)
                old_purchase_tnc = old_terms_map.get(record.id, {}).get('purchase', False)

                new_sale_tnc = vals.get('sale_terms_detail', False)
                new_purchase_tnc = vals.get('purchase_terms_detail', False)

                if old_sale_tnc:
                    sale_orders = self.env['sale.order'].search([
                        ('terms_and_conditions_detail', '=', old_sale_tnc),
                        ('state', '!=', 'sale')
                    ])
                    account_moves = self.env['account.move'].search([
                        ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
                        ('terms_and_conditions_detail', '=', old_sale_tnc),
                        ('state', '!=', 'posted')
                    ])

                    if new_sale_tnc:
                        sale_orders.write({'terms_and_conditions_detail': new_sale_tnc})
                        account_moves.write({'terms_and_conditions_detail': new_sale_tnc})

                if old_purchase_tnc:
                    purchase_orders = self.env['purchase.order'].search([
                        ('terms_and_conditions_detail', '=', old_purchase_tnc),
                        ('state', '!=', 'purchase')
                    ])
                    account_moves = self.env['account.move'].search([
                        ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
                        ('terms_and_conditions_detail', '=', old_purchase_tnc),
                        ('state', '!=', 'posted')
                    ])
                    if new_purchase_tnc:
                        purchase_orders.write({'terms_and_conditions_detail': new_purchase_tnc})
                        account_moves.write({'terms_and_conditions_detail': new_sale_tnc})

        return result



    @api.onchange('sale_term_condition_id')
    def _onchange_sale_term_condition_id(self):
        self.sale_terms_detail = self.sale_term_condition_id.tnc_con if self.sale_term_condition_id else ''

    @api.onchange('purchase_term_condition_id')
    def _onchange_purchase_term_condition_id(self):
        self.purchase_terms_detail = self.purchase_term_condition_id.tnc_con if self.purchase_term_condition_id else ''
