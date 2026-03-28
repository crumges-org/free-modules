# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ServerAction(models.Model):
    _inherit = "ir.actions.server"

    DEFAULT_PYTHON_CODE = """# Available variables:
    #  - env: environment on which the action is triggered
    #  - model: model of the record on which the action is triggered; is a void recordset
    #  - record: record on which the action is triggered; may be void
    #  - records: recordset of all records on which the action is triggered in multi-mode; may be void
    #  - time, datetime, dateutil, timezone: useful Python libraries
    #  - float_compare: utility function to compare floats based on specific precision
    #  - b64encode, b64decode: functions to encode/decode binary data
    #  - log: log(message, level='info'): logging function to record debug information in ir.logging table
    #  - _logger: _logger.info(message): logger to emit messages in server logs
    #  - UserError: exception class for raising user-facing warning messages
    #  - Command: x2many commands namespace
    # To return an action, assign: action = {...}\n\n\n\n"""

    connector_id = fields.Many2one('solt.api.connector', string='API Connector', prefetch=False, help="API Connector linked to this server action")
    use_for_initial_import = fields.Boolean(default=False, string="Use for initial import", help="Mark when this server action is part of the initial import flow")
    last_import_date = fields.Datetime('Last import', readonly=True)
    importing_state = fields.Selection([('idle', 'Idle'), ('scheduled', 'Scheduled'), ('running', 'Running'), ('done', 'Completed'), ('error', 'Error')], string='Import status', default='idle', readonly=True)
    import_result = fields.Text('Import result', readonly=True)
    # Campos para exportación inicial
    use_for_initial_export = fields.Boolean(default=False, string="Use for initial export", help="Mark when this server action is part of the initial export flow")
    last_export_date = fields.Datetime('Last export', readonly=True)
    exporting_state = fields.Selection([('idle', 'Idle'), ('scheduled', 'Scheduled'), ('running', 'Running'), ('done', 'Completed'), ('error', 'Error')], string='Export status', default='idle', readonly=True)
    export_result = fields.Text('Export result', readonly=True)
    code = fields.Text(string='Python Code', groups='base.group_system,solt_api_connector.group_api_integration_manager', default=DEFAULT_PYTHON_CODE, help="Write Python code that the action will execute. Some variables are "
                                                                                                                                                            "available for use; help about python expression is given in the help tab.")

    def _get_eval_context(self, action=None):
        eval_context = super()._get_eval_context(action)
        if action and action.state == "code" and action.base_automation_id:
            eval_context["base_automation"] = action.base_automation_id
        return eval_context

    def execute_initial_import(self):
        """Programa la ejecución de la importación via cron"""
        self.ensure_one()
        if not self.connector_id:
            raise UserError(_("You must set the connector before running the import."))
        if not self.use_for_initial_import:
            raise UserError(_("Enable 'Use for initial import'."))

            # Actualizar el estado a programado
        self.write({'importing_state': 'scheduled', 'import_result': False})
        cron = self.env.ref('solt_api_connector.ir_cron_data_initial_import_check')
        cron.with_context(server_action_id=self.id).method_direct_trigger()

        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': _('Import scheduled'), 'message': _('The import of %s was scheduled and will run in the background.') % self.model_id.name, 'sticky': False, 'type': 'info', }}

    def cron_execute_initial_imports(self, automatic=False):
        """Método para ser llamado por el cron job"""
        cron = self.env.ref('solt_api_connector.ir_cron_data_initial_import_check')
        server_action_id = cron.server_action_to_import_id.id if cron.server_action_to_import_id else False

        if server_action_id:
            # Ejecutar solo para la acción específica
            action = self.browse(server_action_id)
            if action.exists() and action.use_for_initial_import:
                result = action._process_initial_import()
                _logger.info(_("Import action '%s': %s") % (action.name, result))
        else:
            actions = self.sudo().search([('use_for_initial_import', '=', True), ('connector_id', '!=', False), ('importing_state', 'in', ['idle', 'done', 'error'])], order="id asc")
            for action in actions:
                try:
                    result = action._process_initial_import()
                    _logger.info(_("Import action '%s': %s") % (action.name, result))
                except Exception as e:
                    _logger.error(_("Error in import action '%s': %s") % (action.name, str(e)))

        if automatic:
            # auto-commit for batch processing
            self._cr.commit()

    def _process_initial_import(self):
        """Procesa la importación inicial desde la API externa"""
        self.ensure_one()
        self.write({'importing_state': 'running'})
        result = ''

        try:
            self.run()
            result = _("Import completed successfully.")

            self.write({'importing_state': 'done', 'last_import_date': fields.Datetime.now(), 'import_result': result})

        except Exception as e:
            _logger.error("Error during initial import: %s", str(e))
            result = _("Error during import: %s") % str(e)
            self.write({'importing_state': 'error', 'import_result': result})
        return result

    # Metodos para exportación inicial
    def execute_initial_export(self):
        """Programa la ejecución de la exportación via cron"""
        self.ensure_one()
        if not self.connector_id:
            raise UserError(_("You must set the connector before running the export."))
        if not self.use_for_initial_export:
            raise UserError(_("Enable 'Use for initial export'."))

        # Actualizar el estado a programado
        self.write({'exporting_state': 'scheduled', 'export_result': False})
        cron = self.env.ref('solt_api_connector.ir_cron_data_initial_export_check')
        cron.with_context(server_action_export_id=self.id).method_direct_trigger()

        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': _('Export scheduled'), 'message': _('The export of %s was scheduled and will run in the background.') % self.model_id.name, 'sticky': False, 'type': 'info', }}

    def cron_execute_initial_exports(self, automatic=False):
        """Método para ser llamado por el cron job de exportación"""
        cron = self.env.ref('solt_api_connector.ir_cron_data_initial_export_check')
        server_action_id = cron.server_action_to_export_id.id if cron.server_action_to_export_id else False

        if server_action_id:
            # Ejecutar solo para la acción específica
            action = self.browse(server_action_id)
            if action.exists() and action.use_for_initial_export:
                result = action._process_initial_export()
                _logger.info(_("Export action '%s': %s") % (action.name, result))
        else:
            actions = self.sudo().search([('use_for_initial_export', '=', True), ('connector_id', '!=', False), ('exporting_state', 'in', ['idle', 'done', 'error'])], order="id asc")
            for action in actions:
                try:
                    result = action._process_initial_export()
                    _logger.info(_("Export action '%s': %s") % (action.name, result))
                except Exception as e:
                    _logger.error(_("Error in export action '%s': %s") % (action.name, str(e)))

        if automatic:
            # auto-commit for batch processing
            self._cr.commit()

    def _process_initial_export(self):
        """Procesa la exportación inicial hacia la API externa"""
        self.ensure_one()
        self.write({'exporting_state': 'running'})
        result = ''

        try:
            self.run()
            result = _("Export completed successfully.")

            self.write({'exporting_state': 'done', 'last_export_date': fields.Datetime.now(), 'export_result': result})

        except Exception as e:
            _logger.error("Initial export error: %s", str(e))
            result = _("Error during export: %s") % str(e)
            self.write({'exporting_state': 'error', 'export_result': result})
        return result
