from odoo import models, fields, api
import random


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    #: Barcode prefix based on product category (inherited from category)
    prefix_barcode = fields.Char(
        string="Barcode Prefix",
        related='categ_id.prefix_barcode',
        help="Prefix for the barcode, inherited from the product category."
    )

    @api.onchange('categ_id')
    def onchange_categ_id(self):
        """
        On category change, automatically generate a unique barcode using the category prefix.
        Ensures barcode uniqueness within the system.
        """
        unique = False
        while not unique:
            # Generate a random 5-digit number
            barcode = str(random.randint(10000, 99999))

            if self.prefix_barcode:
                # Combine prefix and random number
                full_barcode = self.prefix_barcode + barcode

                # Check if the full barcode is unique among all products
                existing_barcodes = self.env['product.template'].search([]).mapped('barcode')
                if full_barcode not in existing_barcodes:
                    self.barcode = full_barcode
                    unique = True
            else:
                # No prefix available; clear the barcode
                self.barcode = ''
                unique = True

    def name_get(self):
        """
        Override default name_get to return just the name of the product template.

        Returns:
            list: List of tuples with format (record.id, record.name)
        """
        result = []
        for record in self:
            name = record.name
            result.append((record.id, name))
        return result


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def name_get(self):
        """
        Override default name_get to return just the name of the product variant.

        Returns:
            list: List of tuples with format (record.id, record.name)
        """
        result = []
        for record in self:
            name = record.name
            result.append((record.id, name))
        return result
