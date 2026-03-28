# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.config_id.use_product_brand:
            result.append('product.brand')
        return result

    def _loader_params_product_brand(self):
        domain = [('active', '=', True)]
        if self.config_id.available_brand_ids:
            domain.append(('id', 'in', self.config_id.available_brand_ids.ids))
        return {
            'search_params': {
                'domain': domain,
                'fields': ['id', 'name', 'code', 'sequence', 'image_128', 'color'],
                'order': 'sequence, name',
            }
        }

    def _get_pos_ui_product_brand(self, params):
        return self.env['product.brand'].search_read(**params['search_params'])
