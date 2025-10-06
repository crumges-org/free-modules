# Powered by Sensible Consulting Services
# -*- coding: utf-8 -*-
# © 2025 Sensible Consulting Services (<https://sensiblecs.com/>)
from odoo import fields, models
from odoo.tools import float_round

class SblDynamicPortal(models.Model):
    _name = 'sbl.dynamic.portal'
    _description = 'Dynamic Portal'
    _inherit = ['image.mixin']

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sbl_model_id = fields.Many2one('ir.model', string='Model')
    sbl_model_name = fields.Char(related='sbl_model_id.model', string='Model Name')
    sbl_domain = fields.Char('Domain')
    sbl_report_id = fields.Many2one('ir.actions.report', string='Report', help='Display as detailed view')
    sbl_field_line = fields.One2many('sbl.dynamic.portal.line', 'sbl_dynamic_portal_id', string='Fields')
    sbl_sortby_ids = fields.Many2many('ir.model.fields', 'sbl_dynamic_portal_sortby_rel', string='Sort By', domain="[('model_id', '=', sbl_model_id), \
        ('store', '=', True), \
        ('ttype', 'in', ['man2one', 'char', 'boolean', 'date', 'datetime', 'float', 'integer', 'selection'])\
    ]")

    _sql_constraints = [
        ('obj_name_uniq', 'unique (name)', 'Each model must have a unique name.'),
        ('obj_sbl_model_id_uniq', 'unique (sbl_model_id)', 'Each model must be unique.'),
    ]

    def sbl_return_field_value(self, record, line, lang):
        data = ''
        if line.sbl_ttype == 'many2one':
            data = record[line.sbl_field_id.name].display_name
        elif line.sbl_ttype == 'monetary':
            data = self.sbl_return_monetary_value(record, record[line.sbl_field_id.name])
        elif line.sbl_ttype == 'date':
            data = self.sbl_return_date_value(record[line.sbl_field_id.name], lang)
        elif line.sbl_ttype == 'datetime':
            data = self.sbl_return_datetime_value(record[line.sbl_field_id.name], lang)
        elif line.sbl_ttype == 'selection':
            data = self.sbl_return_selection_value(record, line.sbl_field_id.name)
        elif line.sbl_ttype == 'float':
            if line.sbl_display_currency:
                data = self.sbl_return_monetary_value(record, record[line.sbl_field_id.name])
            else:
                data = float_round(record[line.sbl_field_id.name], precision_digits=2)
        else:
            data = record[line.sbl_field_id.name]
        return data

    def sbl_return_monetary_value(self, record, amount):
        currency = self.env.company.currency_id
        if hasattr(record, 'currency_id') and record.currency_id:
            currency = record.currency_id
        return currency.format(amount)

    def sbl_return_date_value(self, date, lang):
        return date.strftime(lang.date_format) if date else date

    def sbl_return_datetime_value(self, date, lang):
        datetime_format = lang.date_format + ' ' + lang.time_format
        return date.strftime(datetime_format) if date else date

    def sbl_return_selection_value(self, record, field):
        selection_value = record[field]
        if record._fields[field].related:
            related = record._fields[field].related
            related_parts = related.split('.')
            related_record = record[related_parts[0]]
            return dict(related_record._fields[related_parts[1]].selection).get(selection_value)
        else:
            return dict(record._fields[field].selection).get(selection_value)