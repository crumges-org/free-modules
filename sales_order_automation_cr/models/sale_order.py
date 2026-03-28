# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by CandidRoot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        if self.env.user.so_auto_complete:
            for order in self:
                if order.picking_ids:
                    for picking_id in self.picking_ids:
                        picking_id.action_assign()
                        picking_id.button_validate()

                if not order.invoice_ids:
                    order._create_invoices()
                if order.invoice_ids:
                    for invoice in order.invoice_ids:
                        invoice.action_post()
                        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=order.invoice_ids.ids).create({
                            'group_payment': True,
                        })._create_payments()
        
        return res