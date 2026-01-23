from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    """
    Inherits the product.category model to add a barcode prefix field,
    which is used to generate barcodes for products based on their category.
    """
    _inherit = 'product.category'

    #: Numeric prefix used for generating product barcodes (must be unique and max 3 digits)
    prefix_barcode = fields.Char(
        string="Barcode Prefix",
        size=3,
        help="Numeric prefix (max 3 digits) used to generate barcodes for products in this category."
    )

    # Ensure the prefix is unique across all categories
    _sql_constraints = [
        (
            'prefix_barcode_unique',
            'unique(prefix_barcode)',
            'This barcode prefix already exists! Please choose a unique one.'
        )
    ]

    @api.constrains('prefix_barcode')
    def _barcode_constrains(self):
        """
        Validates that the barcode prefix is:
        - Numeric only
        - Exactly 3 digits in length (if provided)
        Raises:
            ValidationError: If the value doesn't meet the constraints.
        """
        for record in self:
            if record.prefix_barcode:
                # Check if the prefix is numeric
                if not record.prefix_barcode.isnumeric():
                    raise ValidationError("Barcode prefix must be numeric (digits only).")

                # Check that the prefix is exactly 3 digits
                if len(record.prefix_barcode) != 3:
                    raise ValidationError("Barcode prefix must be exactly 3 digits.")
