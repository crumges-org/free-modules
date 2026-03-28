# -*- coding: utf-8 -*-

from odoo import api, models, _


class SoltApiMetaFields(models.Model):
    _inherit = 'solt.api.meta.fields'

    @api.model
    def _get_default_meta_field_mapping(self):
        # Meta Field Model: additional custom fields need to be added here
        new_field_definition = []
        if self and self.model == 'ir.model.fields':
            new_field_definition = [{
                "name": "x_key",
                "ttype": "char",
                'state': 'manual',
                "field_description": "Original field name in the external system",
                "help": _("Field name: customer-type."),
                "readonly": True
            }]

        return super(SoltApiMetaFields, self)._get_default_meta_field_mapping() + new_field_definition