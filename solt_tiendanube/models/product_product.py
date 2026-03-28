
from collections import defaultdict
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'solt.integration.model.mixin']

    product_depth = fields.Float('Profundidad', digits='Stock Weight')
    product_height = fields.Float('Altura', digits='Stock Weight')
    product_width = fields.Float('Ancho', digits='Stock Weight')
    x_external_id = fields.Char('ID externo', help="ID del record en el sistema externo.", readonly=True)
    x_store_external_id = fields.Char('ID Tienda externo', help="ID de la tienda en el sistema externo.", readonly=True)
    x_state_sync = fields.Selection([
        ('yes', 'Sincronizado'),
        ('no', 'No sincronizado'),
        ('error', 'Error'),
    ],'Synchronization state', help="Indica si fue sincronizado el record.", readonly=True)
    x_exclud_from_sync = fields.Boolean('Exclude from sync with external systems', help="Significa que no sera exportado a sistemas externos.")
    x_date_last_sync = fields.Datetime('Last synchronization', help="Indicates the date de la ultima sincronizacion.", readonly=True)
    promotional_price = fields.Float('Precio promocional', digits='Product Price')
    visible = fields.Boolean("Visible", default=True)
    product_brand_id = fields.Many2one(related='product_tmpl_id.product_brand_id', store=True, readonly=False)

    lst_price = fields.Float(
        'Sales Price', compute='_compute_product_lst_price', store=True,
        digits='Product Price', inverse='_set_product_lst_price',
        help="The sale price is managed from the product template. Click on the 'Configure Variants' button to set the extra attribute prices.")

    def write(self, vals):
        # If skip_product_image_create is in context, don't create an image entry
        # This is used when setting image_variant_1920 from solt.product.image
        if self.env.context.get('skip_product_image_create') and 'image_variant_1920' in vals:
            return super(ProductProduct, self).write(vals)

        # Check if variant image is being updated
        if 'image_variant_1920' in vals and vals['image_variant_1920']:
            for product in self:
                if product.product_tmpl_id.product_variant_count > 1:
                    # First, find all product images that include this variant
                    existing_images = self.env['solt.product.image'].search([
                        ('product_tmpl_id', '=', product.product_tmpl_id.id),
                        ('product_variant_ids', 'in', product.id)
                    ])
                    # Remove this variant from other images product_variant_ids
                    for image in existing_images:
                        variants = image.product_variant_ids - product
                        image.product_variant_ids = variants

                    # Create new image entry for this variant
                    sequence = self._get_next_sequence(product.product_tmpl_id.id)
                    self.env['solt.product.image'].create({
                        'name': product.display_name,
                        'sequence': sequence,
                        'image_1920': vals['image_variant_1920'],
                        'product_tmpl_id': product.product_tmpl_id.id,
                        'product_variant_ids': [(6, 0, [product.id])],  # Link only this variant
                    })

        res = super(ProductProduct, self).write(vals)
        return res

    @api.model
    def _get_next_sequence(self, template_id):
        """Get the next available sequence for a template's images"""
        last_seq = self.env['solt.product.image'].search([
            ('product_tmpl_id', '=', template_id)
        ], order='sequence desc', limit=1).sequence or 0
        return last_seq + 1

    def unlink(self):
        variant_ids = self.ids
        result = super(ProductProduct, self).unlink()

        # Remove the variant references in solt.product.image
        self.env['solt.product.image'].cleanup_deleted_variants(variant_ids)

        return result

    @api.model
    def _get_fields_for_api(self):
        return ['product_depth', 'product_height', 'product_width', 'promotional_price', 'barcode', 'default_code',
                'standard_price', 'volume', 'weight', 'lst_price']

    @api.model
    def _get_inventory_level_api(self):
        self.ensure_one()
        self = self.with_company(self.env.company)
        StockWarehouse = self.env['stock.warehouse'].sudo()
        if not self.is_storable:
            inventory_levels = StockWarehouse._get_default_inventory_level_api(type_product='service')
        else:
            if not self.stock_quant_ids:
                inventory_levels = StockWarehouse._get_default_inventory_level_api()
            else:
                inventory_levels = self._get_total_inventory_level_product_api()
        return inventory_levels

    def _get_total_inventory_level_product_api(self, warehouse_external_id=None):
        """
        Se asume que el producto tiene quants y es de tipo product
        :return:
        """
        inventory_level_dict = defaultdict(list)

        for q in self.stock_quant_ids:
            if q.warehouse_id and q.warehouse_id.x_external_id not in [False, ""] and q.location_id.usage in ['internal', 'transit']:
                inventory_level_dict[q.warehouse_id.x_external_id].append(q.quantity)

        if warehouse_external_id:
            data = inventory_level_dict.get(warehouse_external_id, [])
            inventory_level_dict = {warehouse_external_id: data}

        inventory_levels = [
            {
                "location_id": wh_external_id,
                "stock": int(sum(quantity_list))
            } for wh_external_id, quantity_list in inventory_level_dict.items()]

        return inventory_levels

    def _can_update_variant_cost(self):
        for variant in self:
            if variant.x_exclud_from_sync:
                raise UserError(
                    _("The product is excluded from synchronizacion with external systems"))
            if not variant.company_id:
                raise UserError(_("El producto no tiene configurado una empresa."))
            variant.company_id._check_external_config()

            if variant.x_external_id in [False, '']:
                raise UserError(_("El producto no ha sincronizado. Se debe sincronizar primeramente."))

            if variant.standard_price < 1:
                raise UserError(_("El costo debe ser mayor o igual a 1."))

    def action_sync_cost(self):
        self._can_update_variant_cost()
        if self:
            product_tmpl_ids = self.mapped('product_tmpl_id')
            self[0].company_id.with_context(product_id=product_tmpl_ids.ids)._sync_variants_cost(0, 50)
        else:
            _logger.info((_("No products selected to update the cost.")))
