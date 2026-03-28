# -*- coding: utf-8 -*-

import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'solt.integration.model.mixin', 'connector.sync.mixin']

    nube_google_shopping_category = fields.Char("Google Shopping", translate=True)
    nube_seo_title = fields.Char("SEO title", translate=True)
    nube_seo_description = fields.Char("SEO description", translate=True)
    nube_description = fields.Text(string='Description', sanitize=False, translate=True,)

    def process_category_hierarchy(self, category_parent_data, record=None):
        """Process the hierarchy of a product category.

        Args:
            category_parent_data: Category data from the API
            record: Current Odoo record (if any)

        Returns:
            Parent category ID or False
        """
        if not isinstance(category_parent_data, dict) or 'parent' not in category_parent_data:
            return False
        CategoryModel = self.env['product.category']
        # Parent
        parent_id = category_parent_data.get('parent')
        parent_odoo = False
        endpoint = self.env['solt.api.endpoint'].search([('code', '=', 'CATEG_SINGLE_GET')], limit=1)
        if parent_id and parent_id != 0:
            # Check if parent already exists in Odoo
            parent_odoo = CategoryModel.search([('x_external_id', '=', parent_id)], limit=1)

            if not parent_odoo:
                # Parent doesn't exist in Odoo, we need to create it
                # Call endpoint to retrieve parent data
                try:
                    parent_result = endpoint.execute_request(record=record, data={"id": parent_id})
                    # Parent is created/updated during its own call
                    if parent_result and 'values' in parent_result:
                        parent_values = parent_result['values']
                        parent_values['x_external_id'] = parent_id

                        parent_odoo = CategoryModel.search([('x_external_id', '=', parent_id)], limit=1)
                        if not parent_odoo:
                            parent_odoo = CategoryModel.with_context(not_execute_category_base_automation=True).create(parent_values)
                            _logger.info(f"Parent category created: {parent_id} -> {parent_odoo.id}")
                except Exception as e:
                    _logger.error(f"Error retrieving parent category {parent_id}: {str(e)}")
        else:
            parent_odoo = CategoryModel.search([('x_external_id', '=', category_parent_data.get('id'))], limit=1)
            if not parent_odoo:
                parent = category_parent_data.pop('parent', False)
                mapping_config = json.loads(endpoint.response_mapping)
                rm_parent = mapping_config.pop('parent_id', False)
                values_to_write = endpoint._process_simple_mapping_to_odoo(mapping_config, category_parent_data, record)
                parent_odoo = CategoryModel.with_context(not_execute_category_base_automation=True).create(values_to_write)
                _logger.info(f"Parent category created: {parent_id} -> {parent_odoo.id}")

        return parent_odoo and parent_odoo.id or False

    def _check_categories(self, x_exclud_from_sync):
        for record in self:
            if 'x_exclud_from_sync' in record and x_exclud_from_sync is True:
                products = self.env['product.template'].search([
                    ('x_exclud_from_sync', '=', False),
                    ('categ_ids', 'in', record.ids)
                ])

                if products:
                    template_names = products.mapped('display_name')
                    raise ValidationError(
                        _('Category "%s" cannot be excluded from synchronization because it is used'
                          ' in products that are not excluded: %s.') %
                        (record.name, ', '.join(template_names))
                    )

    def write(self, vals):
        if 'x_exclud_from_sync' in vals and vals.get('x_exclud_from_sync', False):
            self._check_categories(vals.get('x_exclud_from_sync'))
        return super(ProductCategory, self).write(vals)

