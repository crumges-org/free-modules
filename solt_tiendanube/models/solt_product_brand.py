# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SoltProductBrand(models.Model):
    _name = 'solt.product.brand'
    _inherit = ['mail.thread', 'image.mixin', 'solt.integration.model.mixin']
    _description = 'Product Brand'

    name = fields.Char("Name", required=True)
    description = fields.Text(translate=True)
    product_ids = fields.One2many(
        "product.template", "product_brand_id", string="Products"
    )
    products_count = fields.Integer(
        string="Cantidad de productos", compute="_compute_products_count"
    )
    company_id = fields.Many2one('res.company', string='Company')

    @api.constrains('name', 'company_id')
    def _check_name_unique_per_company(self):
        for record in self:
            domain = [
                ('name', '=', record.name),
                ('company_id', '=', record.company_id.id if record.company_id else False),
                ('id', '!=', record.id),
            ]
            if self.search_count(domain) > 1:
                raise ValidationError('The brand name must be unique per company.')

    @api.depends("product_ids")
    def _compute_products_count(self):
        groups = self.env["product.template"].read_group(
            [("product_brand_id", "in", self.ids)],
            ["product_brand_id"],
            ["product_brand_id"],
            lazy=False,
        )
        data = {group["product_brand_id"][0]: group["__count"] for group in groups}
        for brand in self:
            brand.products_count = data.get(brand.id, 0)
