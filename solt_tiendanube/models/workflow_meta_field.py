# -*- coding: utf-8 -*-

import logging
from odoo import models

_logger = logging.getLogger(__name__)

# Mapeo de owner_resource a modelos de Odoo
OWNER_RESOURCE_TO_ODOO_MODEL = {
    'product': 'product.template',
    'product_variant': 'product.product',
    'order': 'sale.order',
    'customer': 'res.partner',
    'category': 'product.category'
}

# Mapeo de value_type a tipos de campos de Odoo
VALUE_TYPE_TO_ODOO_FIELD = {
    'text': 'char',  # Campo de texto simple
    'text_list': 'selection',  # Lista de opciones (selection)
    'numeric': 'float',  # Numeric field (podria ser 'integer' as needed)
    'date': 'date'  # Campo de fecha
}

# Reverse mapping para conversion from Odoo
ODOO_FIELD_TO_VALUE_TYPE = {
    'char': 'text',
    'text': 'text',
    'selection': 'text_list',
    'float': 'numeric',
    'integer': 'numeric',
    'monetary': 'numeric',
    'date': 'date',
    'datetime': 'date'
}


class MetaField(models.Model):
    _name = 'ir.model.fields'
    _inherit = ['ir.model.fields', 'solt.integration.model.mixin']

    def get_odoo_model_from_owner_resource(self, owner_resource):
        """
        Converts the owner_resource from the endpoint to the corresponding Odoo model.
        """
        return OWNER_RESOURCE_TO_ODOO_MODEL.get(owner_resource)

    def get_odoo_field_type_from_value_type(self, value_type):
        """
        Converts the value_type from the endpoint to the Odoo field type.
        """
        return VALUE_TYPE_TO_ODOO_FIELD.get(value_type)

    def get_value_type_from_odoo_field(self, odoo_field_type):
        """
        Convierte un tipo de campo de Odoo al value_type del endpoint
        """
        return ODOO_FIELD_TO_VALUE_TYPE.get(odoo_field_type)

    def _transform_api_name_to_odoo(self, api_name, char_to_replace=' ', separator='_'):
        if not isinstance(api_name, str):
            return ""
        return f"x_{api_name.lower().replace(char_to_replace, separator)}"
