# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
from odoo import api, fields, models


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    connector_id = fields.Many2one('solt.api.connector', string='Connector')
    endpoint_id = fields.Many2one('solt.api.endpoint', string='Endpoint')
    sync_direction = fields.Selection([('to_store', 'To external store'), ('from_store', 'From external store'), ], string='Sync direction', default='to_store')
    is_api_sync = fields.Boolean(string='Is API Sync', compute='_compute_is_api_sync', store=True, prefetch=False)
    sequence = fields.Integer(string="Sequence", default=10)

    @api.depends('trigger', 'trigger_field_ids', 'trg_selection_field_id', 'trg_field_ref')
    def _compute_filter_domain(self):
        for record in self:
            if record.connector_id and record.trigger not in ['on_state_set', 'on_priority_set', 'on_user_set', 'on_archive', 'on_unarchive']:
                trigger_fields_count = len(record.trigger_field_ids)
                if trigger_fields_count in [0, 1] and not record.filter_domain:
                    record.filter_domain = False
            else:
                super(BaseAutomation, self)._compute_filter_domain()

    @api.depends('connector_id')
    def _compute_is_api_sync(self):
        for record in self:
            record.is_api_sync = bool(record.connector_id)

    def toggle_active(self):
        return super(BaseAutomation, self).toggle_active()

    def _get_trigger_fields(self, record):
        """Return the trigger fields that have been modified on ``record``.
        Optionally exclude computed fields when requested via context."""
        self_sudo = self.sudo()
        _fields = []
        modified_fields = []
        ignore_computed = self._context.get('ignore_computed_fields', False)
        if not self_sudo.trigger_field_ids:
            # Every field is an implicit trigger
            fields_list = list(record._fields.keys())
        else:
            fields_list = self_sudo.trigger_field_ids.mapped('name')

        if self._context.get('old_values', None) is None:
            return modified_fields
        # note: old_vals are in the record format
        old_vals = self._context['old_values'].get(record.id, {})

        def differ(name):
            return name in old_vals and record[name] != old_vals[name]

        for field in fields_list:
            if field in models.MAGIC_COLUMNS:
                continue

            # Skip computed fields when requested
            if ignore_computed and field in record._fields:
                field_obj = record._fields[field]
                if field_obj.compute and not field_obj.store:
                    continue

            if differ(field):
                modified_fields.append(field)

        return modified_fields
