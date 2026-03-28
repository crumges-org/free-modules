# -*- coding: utf-8 -*-

import logging
from odoo import models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    def _check_product_attribute_values(self, x_exclud_from_sync):
        for attribute in self:
            if 'x_exclud_from_sync' in attribute and x_exclud_from_sync is True:
                attribute_line = attribute.attribute_line_ids.filtered(lambda l: l.value_count > 1)
                if attribute_line:
                    template_names = attribute_line.mapped('product_tmpl_id.display_name')
                    raise ValidationError(
                        _('Attribute "%s" cannot be excluded from synchronization because it is used in products'
                          ' with more than one value: %s.') %
                        (attribute.name, ', '.join(template_names))
                    )

    def write(self, vals):
        if 'x_exclud_from_sync' in vals and vals.get('x_exclud_from_sync', False):
            self._check_product_attribute_values(vals.get('x_exclud_from_sync'))
        return super(ProductAttribute, self).write(vals)