from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    price_subtotal = fields.Monetary(
        compute="_compute_totals",
        inverse="_inverse_price_subtotal",
        store=True,
        readonly=False,  # Override to make it writable
    )

    @api.depends("product_qty", "price_unit", "taxes_id", "currency_id")
    def _compute_totals(self):
        """Compute `price_subtotal` based on `price_unit` and `product_qty`."""
        for line in self:
            if line.product_qty:
                line.price_subtotal = line.price_unit * line.product_qty
            else:
                line.price_subtotal = 0.0

    def _inverse_price_subtotal(self):
        """Recalculate `price_unit` when `price_subtotal` is manually updated."""
        for line in self:
            if line.product_qty:
                line.price_unit = line.price_subtotal / line.product_qty
            else:
                raise UserError(_("Quantity must be greater than zero to calculate the unit price."))

    @api.onchange("price_unit", "product_qty")
    def _onchange_price_unit(self):
        """Recalculate `price_subtotal` when `price_unit` changes."""
        for line in self:
            if line.product_qty:
                line.price_subtotal = line.price_unit * line.product_qty

    @api.onchange("price_subtotal")
    def _onchange_price_subtotal(self):
        """Recalculate `price_unit` when `price_subtotal` changes."""
        for line in self:
            if line.product_qty:
                line.price_unit = line.price_subtotal / line.product_qty
