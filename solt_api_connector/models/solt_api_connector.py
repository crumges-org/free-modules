# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
import base64
import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SoltApiConnector(models.Model):
    _name = 'solt.api.connector'
    _description = 'API Connector'

    name = fields.Char('Name', required=True)
    base_url = fields.Char('Base URL', required=True, help="Base API URL (e.g. https://api.example.com)")
    active = fields.Boolean('Active', default=True)
    auth_type = fields.Selection([('none', 'No authentication'), ('basic', 'Basic authentication'), ('bearer', 'Bearer token'), ('api_key', 'API key'), ], string='Authentication type', default='none', required=True)
    username = fields.Char('Username', help="Used for Basic authentication")
    password = fields.Char('Password', help="Used for Basic authentication")
    token = fields.Char('Token', help="Used for Bearer or API key auth")
    api_key_name = fields.Char('API key name', help="Parameter name for the API key")
    api_key_in = fields.Selection([('header', 'Header'), ('query', 'Query parameter')], string='API key location', default='header')
    timeout = fields.Integer('Timeout (seconds)', default=30)
    headers = fields.Json('Extra headers', help="JSON structure with extra headers")
    endpoint_ids = fields.One2many('solt.api.endpoint', 'connector_id', string='Endpoints')
    automation_ids = fields.One2many('base.automation', 'connector_id', string='Automations', domain=['|', ('active', '=', True), ('active', '=', False)], context={'active_test': False}, help="Automation rules associated with this connector")
    company_ids = fields.One2many('res.company', 'connector_id', string='Companies', help="Companies linked to this connector")
    call_log_count = fields.Integer(string='Call logs', compute='_compute_call_log_count')
    meta_field_ids = fields.One2many('solt.api.meta.fields', 'connector_id', string="Meta fields")
    ini_import_acion_server_ids = fields.One2many('ir.actions.server', 'connector_id', domain=[('use_for_initial_import', '=', True)], string='Initial import actions')
    company_count = fields.Integer(compute="_compute_company_count", string="Companies with connector")
    company_sync_count = fields.Integer(compute="_compute_company_count", string="Companies with external config")
    ini_export_action_server_ids = fields.One2many('ir.actions.server', 'connector_id', string='Initial export actions', domain=[('use_for_initial_export', '=', True)], help="Server actions used for first-time exports")

    @api.depends()
    def _compute_call_log_count(self):
        """Calculates the number of call logs for this connector"""
        for connector in self:
            connector.call_log_count = self.env['solt.api.call.log'].search_count([('connector_id', '=', connector.id)])

    @api.depends('company_ids')
    def _compute_company_count(self):
        for connector in self:
            connector.company_count = len(connector.company_ids)
            connector.company_sync_count = len(connector.company_ids.filtered(lambda c: c.external_id and c.bearer_token))

    def action_view_call_logs(self):
        """Opens the call logs view filtered by this connector"""
        self.ensure_one()
        return {'name': _('API Call Logs'), 'type': 'ir.actions.act_window', 'res_model': 'solt.api.call.log', 'view_mode': 'list,form', 'domain': [('connector_id', '=', self.id)], 'context': {'default_connector_id': self.id}, 'target': 'current', }

    @api.model
    def execute_endpoint(self, endpoint_code, record=None, params=None, data=None):
        """Executes an endpoint given its code and a dictionary of arguments"""
        endpoint = self.env['solt.api.endpoint'].search([('code', '=', endpoint_code)], limit=1)
        if not endpoint:
            raise ValidationError(_("Endpoint not found: %s") % endpoint_code)
        try:
            response = endpoint.execute_request(record, params, data)
        except Exception as e:
            _logger.error(f"Error processing response: {str(e)}")
            raise UserError(str(e))
        return response

    def _get_auth_headers(self):
        """Prepares the authentication headers according to the configured type"""
        headers = {}
        if self.auth_type == 'basic':
            if not self.username or not self.password:
                raise ValidationError(_("Username and password are required for Basic authentication."))
            auth_str = f"{self.username}:{self.password}"
            headers['Authorization'] = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        elif self.auth_type == 'bearer':
            if not self.token:
                raise ValidationError(_("Token is required for Bearer authentication."))
            headers['Authorization'] = f"Bearer {self.token}"
        elif self.auth_type == 'api_key' and self.api_key_in == 'header':
            if not self.token or not self.api_key_name:
                raise ValidationError(_("API key name and value are required."))
            headers[self.api_key_name] = self.token
        # Add extra headers if they exist
        if self.headers:
            headers.update(json.loads(self.headers))
        return headers

    def _prepare_api_url(self, endpoint):
        """Prepares the full URL including the base URL and the endpoint"""
        if endpoint.startswith('https://') or endpoint.startswith('http://'):
            return endpoint.rstrip('/')
        base = self.base_url.rstrip('/')
        endpoint_path = endpoint.lstrip('/')
        return f"{base}/{endpoint_path}"

    def test_connection(self):
        """Tests the basic connection to the API"""
        try:
            headers = self._get_auth_headers()
            response = requests.get(self.base_url, headers=headers, timeout=self.timeout)
            if 200 <= response.status_code < 300:
                return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': _('Connection successful'), 'message': _('The API connection was established successfully.'), 'sticky': False, 'type': 'success', }}
            else:
                return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': _('Connection error'), 'message': _('API responded with code: %s - %s') % (response.status_code, response.text), 'sticky': True, 'type': 'warning', }}
        except Exception as e:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': _('Connection error'), 'message': str(e), 'sticky': True, 'type': 'danger', }}

    def action_all_active(self):
        for connector in self.with_context(active_test=False):
            connector.automation_ids.filtered(lambda a: not a.active).toggle_active()
        return True

    def action_all_inactive(self):
        for connector in self.with_context(active_test=False):
            connector.automation_ids.filtered(lambda a: a.active).toggle_active()
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active(self):
        if any(connector.active for connector in self):
            raise UserError(_('You cannot delete an active API connector.'))

    def toggle_active(self):
        res = super().toggle_active()
        # Propagate active state to children
        for connector in self.with_context(active_test=False):
            connector.automation_ids.active = connector.active
        return res

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ['form']:
            for field in self._fields.keys():
                if field not in models.MAGIC_COLUMNS + ['active']:
                    field_node = next(iter(arch.xpath(f'//field[@name="{field}"]')), None)
                    if field_node is not None:
                        field_node.attrib['readonly'] = "not active"
        return arch, view

    def action_create_all_meta_fields(self):
        self.ensure_one()
        if self.meta_field_ids:
            for meta_field_id in self.meta_field_ids:
                meta_field_id.action_create_meta_fields()

    def unlink(self):
        for connector in self:
            # delete ini_import_acion_server_ids
            ini_import_acion_server_ids = self.env['ir.actions.server'].with_context(active_test=False).search([('connector_id', '=', connector.id), ('use_for_initial_import', '=', True)])
            ini_import_acion_server_ids.unlink()
            # delete meta fields config
            meta_field_ids = self.env['solt.api.meta.fields'].with_context(active_test=False).search([('connector_id', '=', connector.id)])
            meta_field_ids.unlink()

            # delete automations config
            automation_ids = self.env['base.automation'].with_context(active_test=False).search([('connector_id', '=', connector.id)])
            automation_ids.unlink()

            # delete ini_export_action_server_ids
            ini_export_action_server_ids = self.env['ir.actions.server'].with_context(active_test=False).search([('connector_id', '=', connector.id), ('use_for_initial_export', '=', True)])
            ini_export_action_server_ids.unlink()
        return super(SoltApiConnector, self).unlink()
