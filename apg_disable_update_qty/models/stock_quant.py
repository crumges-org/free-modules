# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import ValidationError

class StockChangeProductQty(models.TransientModel):
    _inherit = 'stock.change.product.qty'

    def change_product_qty(self):
        res = super(StockChangeProductQty, self).change_product_qty()
        if not self.env.user.has_group("apg_disable_update_qty.group_onhand_qty_user"):
            raise ValidationError(
                _("You don't have access rights for update on hand quantity!"))
        return res
