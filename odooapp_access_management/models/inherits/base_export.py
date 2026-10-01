"""Export and import enforcement.

Hiding the Export item in the cog menu is not a restriction: ``/web/export/csv``
and ``/web/export/xlsx`` stay reachable, and ``export_data`` is an RPC-callable
model method. Both HTTP routes funnel through ``export_data``, so guarding it
covers the browser, the endpoints and the API in one place - which is the whole
point of enforcing rather than hiding.

``load`` is the matching entry point for import, and both of the ``base_import``
model methods route through it.
"""

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError


class Base(models.AbstractModel):
    _inherit = 'base'

    # ------------------------------------------------------------------
    # Export (features B5, C11, H5)
    # ------------------------------------------------------------------

    def export_data(self, fields_to_export):
        """Block the export, or strip the fields that may not leave."""
        if not self.env.su:
            self._aam_check_export()
            fields_to_export = self._aam_filter_exported_fields(fields_to_export)
        result = super().export_data(fields_to_export)
        self._aam_postprocess_export(fields_to_export, result.get('datas') or [])
        return result

    def _aam_postprocess_export(self, fields_to_export, rows):
        """Called with the columns that were exported and their rows. Does nothing here.

        ``rows`` is a list of lists in the order of ``fields_to_export``; a
        module that redacts exported values changes it in place.
        """

    def _aam_check_export(self):
        policy = self.env['aam.policy'].get_policy()
        entry = policy['models'].get(self._name, {})
        if policy['globals'].get('hide_export') or entry.get('hide_export'):
            self.env['aam.audit.log']._log(
                'denial', model_name=self._name, operation='export')
            raise AccessError(_(
                "You are not allowed to export %s records.",
                self.env['ir.model']._get(self._name).name or self._name))

    def _aam_filter_exported_fields(self, fields_to_export):
        """Drop fields marked no-export, and any that are hidden outright.

        An invisible field must not reappear in a spreadsheet - that would be a
        neat way around the whole restriction.
        """
        blocked = self._aam_unexportable_fields()
        if not blocked:
            return fields_to_export
        kept = []
        for spec in fields_to_export:
            # A spec may be 'name' or a dotted path like 'partner_id/name'.
            root = str(spec).replace('.', '/').split('/')[0]
            if root not in blocked:
                kept.append(spec)
        return kept

    @api.model
    def _aam_unexportable_fields(self):
        policy = self.env['aam.policy'].get_policy()
        entries = policy['fields'].get(self._name, {})
        return {
            name for name, entry in entries.items()
            if entry.get('no_export') or entry.get('invisible')
        }

    # ------------------------------------------------------------------
    # Import (features B6, H4)
    # ------------------------------------------------------------------

    @api.model
    def load(self, fields, data):
        if not self.env.su:
            self._aam_check_import()
        return super().load(fields, data)

    @api.model
    def _aam_check_import(self):
        policy = self.env['aam.policy'].get_policy()
        entry = policy['models'].get(self._name, {})
        if policy['globals'].get('hide_import') or entry.get('hide_import'):
            self.env['aam.audit.log']._log(
                'denial', model_name=self._name, operation='import')
            raise UserError(_(
                "You are not allowed to import %s records.",
                self.env['ir.model']._get(self._name).name or self._name))
