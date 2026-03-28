# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'solt.integration.model.mixin', 'connector.sync.mixin']

    def _check_carrier_details_compliance(self):
        """ Check that a picking has a `carrier_tracking_ref`.
        This allows to block a picking to be validated as done if the `carrier_tracking_ref` is
        missing.

        :raise: UserError if `carrier_id` or `carrier_tracking_ref` is missing
        """
        tnube_pickings_sudo = self.sudo().filtered(
            lambda p: p.sale_id
            and p.sale_id.x_external_id
            and p.sale_id.origin
            and 'Tiendanube' in p.sale_id.origin.split(' ')
            and p.location_dest_id.usage == 'customer'
        )  # In sudo mode to read the field on sale.order
        for picking_sudo in tnube_pickings_sudo:
            if not picking_sudo.carrier_id.name:
                raise UserError(_(
                    "You need to assign a carrier to this delivery."
                ))
            if not picking_sudo.carrier_tracking_ref:
                raise UserError(_(
                    "Since the current carrier doesn't automatically provide a tracking reference, "
                    "you need to set one manually."
                ))
        return super()._check_carrier_details_compliance()

    def _check_sales_order_line_completion(self):
        """ Check that all stock moves related to a sales order line are set done at the same time.

        This allows to block a confirmation of a stock picking linked to an TN sales order if a
        product's components are not all shipped together. Its components should come in a
        single package. Furthermore, the customer would expect all the components to be delivered
        at once rather than received only a fraction of a product.

        :raise: UserError if a stock move is set done while other moves related to the same TN
                sales order line are not
        """
        for picking in self:
            # To assess the completion of a sales order line, we group related moves together and
            # sum the total demand and done quantities.
            sales_order_lines_completion = {}
            for move in picking.move_ids.filtered('sale_line_id.fulfillmen_external_id'):
                completion = sales_order_lines_completion.setdefault(move.sale_line_id, [0, 0])
                completion[0] += move.product_uom_qty
                completion[1] += move.quantity

            # Check that all sales order lines are either entirely shipped or not shipped at all
            for sales_order_line, completion in sales_order_lines_completion.items():
                demand_qty, done_qty = completion
                completion_ratio = done_qty / demand_qty if demand_qty else 0
                if 0 < completion_ratio < 1:  # The completion ratio must be either 0% or 100%
                    raise UserError(_(
                        "Products delivered to TN customers must have their respective parts in"
                        " the same package. Operations related to the product %s were not all "
                        "confirmed at once.",
                        sales_order_line.product_id.display_name
                    ))

    def write(self, vals):
        pickings = self
        if 'date_done' in vals:
            tnube_pickings_sudo = self.sudo().filtered(
                lambda p: p.sale_id
                          and p.sale_id.x_external_id
                          and p.sale_id.origin
                          and 'Tiendanube' in p.sale_id.origin.split(' ')
                          and p.location_dest_id.usage == 'customer'
            )
            tnube_pickings_sudo._check_sales_order_line_completion()
            for picking_sudo in tnube_pickings_sudo:
                if not picking_sudo.carrier_id.name:
                    raise UserError(_(
                        "You need to assign a carrier to this delivery."
                    ))
                if not picking_sudo.carrier_tracking_ref:
                    raise UserError(_(
                        "Since the current carrier doesn't automatically provide a tracking reference, "
                        "you need to set one manually."
                    ))

            super(StockPicking, tnube_pickings_sudo).write(vals)
            pickings -= tnube_pickings_sudo
        return super(StockPicking, pickings).write(vals)