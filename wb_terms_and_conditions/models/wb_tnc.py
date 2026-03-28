# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) Wan Buffer Services (<https://wanbuffer.com/>).
#
#    For Module Support : support@wanbuffer.com  or Call : +91 9638442270
#
##############################################################################
from odoo import models, fields,api

class WBTermsCondition(models.Model):
    _name = 'wb.terms.condition'
    _description = 'Terms and Conditions'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Title", required=True,tracking = True)
    term_type = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase')],
                                 string='Type', required=True,tracking = True)
    tnc_con = fields.Html(string="Terms & Conditions")
    company_ids = fields.Many2many('res.company', string="Companies")


    def write(self, vals):
        """Retrieve old `tnc_con`, update the record, and then propagate updates after `super` call."""
        for record in self:
            old_tnc_con = record.tnc_con
        result = super(WBTermsCondition, self).write(vals)
        if 'tnc_con' in vals:
            new_tnc_con = vals['tnc_con']
            sale_orders = self.env['sale.order'].search([
                ('terms_and_conditions_detail', '=', old_tnc_con),
                ('state', '!=', 'sale')
            ])
            purchase_orders = self.env['purchase.order'].search([
                ('terms_and_conditions_detail', '=', old_tnc_con),
                ('state', '!=', 'purchase')
            ])
            account_moves = self.env['account.move'].search([
                ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
                ('terms_and_conditions_detail', '=', old_tnc_con),
                ('state', '!=', 'posted')

            ])
            partners = self.env['res.partner'].search([
                ('sale_terms_detail', '=', old_tnc_con)
            ])
            purchase_partners = self.env['res.partner'].search([
                ('purchase_terms_detail', '=', old_tnc_con)
            ])

            sale_orders.write({'terms_and_conditions_detail': new_tnc_con})
            purchase_orders.write({'terms_and_conditions_detail': new_tnc_con})
            account_moves.write({'terms_and_conditions_detail': new_tnc_con})
            partners.write({'sale_terms_detail': new_tnc_con})
            purchase_partners.write({'purchase_terms_detail': new_tnc_con})

        return result


