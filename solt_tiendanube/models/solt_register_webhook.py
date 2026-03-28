# -*- coding: utf-8 -*-

from datetime import datetime
import json
import logging
from odoo import models, fields, _, api, Command
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SoltRegisterWebhook(models.Model):
    _name = 'solt.register.webhook'
    _description = 'Registros de webhooks de Tiendanube'

    name = fields.Char("Nombre")
    event = fields.Char("Evento")
    webhook_url = fields.Char("Url", related="automation_id.url")
    active = fields.Boolean("Activo", default=False)
    automation_id = fields.Many2one('base.automation', 'Webhook', domain="[('trigger', '=', 'on_webhook'), ('active', 'in', [True, False]), ('connector_id', '!=', False)]")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    connector_id = fields.Many2one('solt.api.connector', related='automation_id.connector_id', string='Conector')
    is_connector_active = fields.Boolean(related="connector_id.active")

    _sql_constraints = [
        ('event_url_unique', 'UNIQUE(event, webhook_url)', 'Event and URL must be unique.'),
    ]

    def _register_webhook(self, connector):
        self.ensure_one()
        values = {
            "event": self.event,
            "url": self.automation_id.url
        }
        try:
            res = connector.execute_endpoint('WEBHOOK_CREATE', record=self, data=values)
            sync_values = {
                'x_state_sync': 'yes',
                'x_date_last_sync': datetime.now(),
                'x_store_external_id': self.env.company.external_id or '',
                'company_id': self.env.company.id,
                'active': True
            }
            res.get('values', {}).update(sync_values)
            self.write(res['values'])
            _logger.info(f"Registro de webhooks actualizado: {self.name}")

        except Exception as e:
            msg = _(f"Error al publicar webhook {self.event} para el conector {connector.name}: {str(e)}")
            _logger.error(msg)
            raise UserError(msg)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_automation_id(self):
        if any(connector.automation_id for connector in self):
            raise UserError(_('No puedes eliminar el Registro con un webhook configurado.'))

    def toggle_active(self):
        res = super().toggle_active()
        for record in self.with_context(active_test=False):
            wh_action = self._context.get('wh_action', False)
            sync_values = {
                'x_date_last_sync': datetime.now(),
                'x_store_external_id': self.env.company.external_id or '',
                'company_id': self.env.company.id
            }
            if wh_action and wh_action == 'public':
                values = {
                    "event": record.event,
                    "url": record.automation_id.url
                }
                try:
                    response = record.connector_id.execute_endpoint('WEBHOOK_CREATE', record=record, data=values)
                    if 'error' in response:
                        sync_values.update({'x_state_sync': 'error', 'active': False})
                        record.write(sync_values)
                        msg = f"Error: {str(response.get('error_message', ''))}"
                        _logger.error(msg)
                        raise UserError(msg)
                    else:
                        sync_values.update({'x_state_sync': 'yes', 'active': True})
                        response.get('values', {}).update(sync_values)
                        record.write(response['values'])
                        _logger.info(f"Webhook registration updated: {record.name}")

                except Exception as e:
                    msg = _(f"Error publishing webhook {record.event} for connector {record.connector_id.name}: {str(e)}")
                    _logger.error(msg)
                    raise UserError(msg)
            elif wh_action and wh_action == 'delete':
                try:
                    response = record.connector_id.execute_endpoint('WEBHOOK_DELETE', record=record)
                    if 'error' in response:
                        sync_values.update({'x_state_sync': 'error', 'active': False})
                        record.write(sync_values)
                        msg = f"Error: {str(response.get('error_message', ''))}"
                        _logger.error(msg)
                        raise UserError(msg)
                    else:
                        sync_values.update({'x_state_sync': 'no', 'active': False})
                        response.get('values', {}).update(sync_values)
                        record.write(response['values'])
                        _logger.info(f"Registro de webhooks actualizado: {record.name}")

                except Exception as e:
                    msg = _(f"Error al eliminar webhook {record.event} para el conector {record.connector_id.name}: {str(e)}")
                    _logger.error(msg)
                    raise UserError(msg)

        return res
