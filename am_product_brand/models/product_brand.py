# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'
    _order = 'sequence, name'

    name = fields.Char(string='Brand Name', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    image = fields.Image(string='Image', max_width=256, max_height=256)
    image_128 = fields.Image(string='Image 128', related='image', max_width=128, max_height=128, store=True)
    
    description = fields.Text(string='Description', translate=True)
    
    product_count = fields.Integer(
        string='Products Count',
        compute='_compute_product_count'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    color = fields.Integer(string='Color', default=0)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Brand name must be unique per company!'),
    ]

    @api.depends('name')
    def _compute_product_count(self):
        for brand in self:
            brand.product_count = self.env['product.template'].search_count([
                ('brand_id', '=', brand.id)
            ])

    def action_view_products(self):
        """View products of this brand"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Products - {self.name}',
            'res_model': 'product.template',
            'view_mode': 'kanban,list,form',
            'domain': [('brand_id', '=', self.id)],
            'context': {'default_brand_id': self.id},
        }
