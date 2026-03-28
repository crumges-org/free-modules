# -*- coding: utf-8 -*-
import logging
import requests
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class TiendaNubeSyncController(http.Controller):

    @route(['/tiendanube/sync/install'], type='http', auth='public', methods=['POST'], csrf=False)
    def tiendanube_sync_install(self, **kwargs):
        """
        Controller that receives data from the middleware and executes the synchronization.
        """
        try:
            # Get webhook data
            sync_data = self._get_webhook_data()
            _logger.info(f"Synchronization data received: {sync_data}")
            # Validate required data
            if not self._validate_sync_data(sync_data):
                return request.make_response('Invalid data', status=400)
            # Execute the automated rule "UPDATE STORE" using its URL
            result = self._execute_store_update_automation(sync_data)
            if not result.get('success'):
                _logger.error(f"Store update error: {result.get('error_message')}")
                return request.make_response('Store update error', status=500)
            _logger.info(f"Store updated successfully: {result}")
            request.env.ref('solt_tiendanube.ir_cron_sync_tn_solt').sudo()._trigger()
            return request.make_response('OK')

        except Exception as e:
            error_msg = f"Synchronization error: {str(e)}"
            _logger.error(error_msg)
            return request.make_response('Internal server error', status=500)

    def _get_webhook_data(self):
        """
        Extracts the webhook data from the request.
        """
        if request.httprequest.content_type == 'application/json':
            return request.get_json_data()
        else:
            return request.httprequest.values

    def _validate_sync_data(self, sync_data):
        """
        Validates that the webhook data contains the required information.
        """
        required_fields = ['store_info', 'sync_token', 'odoo_version', 'callback_url']
        return all(field in sync_data for field in required_fields)

    def _execute_store_update_automation(self, sync_data):
        """
        Executes the automated rule "UPDATE STORE" using its URL.
        """
        try:
            # Search for the automated rule
            # base_automation = request.env['base.automation'].sudo().search([
            #     ('name', '=', 'UPDATE STORE'),
            #     ('active', '=', True)
            # ], limit=1)
            base_automation = request.env.ref('solt_tiendanube.tn_automation_update_store').sudo()
            if not base_automation:
                raise UserError("Automated rule 'UPDATE STORE' not found or inactive.")
            if not base_automation.url:
                raise UserError("The automated rule 'UPDATE STORE' does not have a configured URL.")
            _logger.info(f"Executing automated rule: {base_automation.name} at URL: {base_automation.url}")
            # Extract information
            store_info = sync_data.get('store_info', {})
            sync_token = sync_data.get('sync_token')
            # Prepare payload with the synchronization token
            payload = store_info.copy()
            payload['sync_token'] = sync_token
            payload['callback_url'] = sync_data.get('callback_url')
            # Simulate HTTP call to the webhook URL
            result = self._call_webhook_url(base_automation, payload)

            return {
                'success': True,
                'company_id': result.get('company_id'),
                'company_name': result.get('company_name'),
                'company_email': result.get('company_email'),
                'sync_token': sync_token
            }

        except Exception as e:
            _logger.error(f"Error executing automated rule: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'sync_token': sync_token
            }

    def _call_webhook_url(self, base_automation, payload):
        """
        Simulates an HTTP call to the webhook URL of the automated rule.
        """
        try:
            # Obtener la URL del webhook
            webhook_url = base_automation.url

            # Si la URL es relativa, construir la URL completa
            if webhook_url.startswith('/'):
                base_url = request.httprequest.host_url.rstrip('/')
                webhook_url = f"{base_url}{webhook_url}"

            _logger.info(f"Llamando webhook URL: {webhook_url}")

            # Preparar headers para la llamada
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo-Tiendanube-Integration',
                'X-Forwarded-For': request.httprequest.remote_addr,
                'X-Real-IP': request.httprequest.remote_addr,
            }

            # Add headers de autenticacion si es necesario
            if hasattr(base_automation, 'connector_id') and base_automation.connector_id:
                # Add headers connector specific si existen
                if hasattr(base_automation.connector_id, 'get_auth_headers'):
                    auth_headers = base_automation.connector_id.get_auth_headers()
                    headers.update(auth_headers)

            # Realizar la llamada HTTP
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=60  # Timeout longer para sincronizacion
            )

            _logger.info(f"Respuesta del webhook: {response.status_code}")

            if response.status_code == 200:
                request.env.cr.commit()
                # La llamada fue exitosa, ahora necesitamos obtener la empresa creada/actualizada
                company_info = self._get_company_info_from_payload(payload)
                return company_info
            else:
                error_msg = f"Error en webhook: {response.status_code} - {response.text}"
                _logger.error(error_msg)
                raise UserError(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conectividad al llamar webhook: {str(e)}"
            _logger.error(error_msg)
            raise UserError(error_msg)
        except Exception as e:
            error_msg = f"Error inesperado al llamar webhook: {str(e)}"
            _logger.error(error_msg)
            raise UserError(error_msg)

    def _get_company_info_from_payload(self, payload):
        """
        Get information de la empresa basandose en el payload
        """
        try:
            # Search company que deberia haberse creado/actualizada
            ResCompany = request.env['res.company'].sudo()

            # Buscar por nombre o email del payload
            company_id = ResCompany.search([
                '|',
                ('name', '=ilike', payload.get('name', '')),
                ('email', '=ilike', payload.get('email', ''))
            ], limit=1)

            if company_id:
                return {
                    'company_id': company_id.id,
                    'company_name': company_id.name,
                    'company_email': company_id.email,
                    'external_id': company_id.external_id,
                    'bearer_token': company_id.bearer_token
                }
            else:
                # Si no encontramos la empresa, buscar por sync_token
                company_id = ResCompany.search([
                    ('sync_token', '=', payload.get('sync_token'))
                ], limit=1)

                if company_id:
                    return {
                        'company_id': company_id.id,
                        'company_name': company_id.name,
                        'company_email': company_id.email,
                        'external_id': company_id.external_id,
                        'bearer_token': company_id.bearer_token
                    }
                else:
                    raise UserError("No se pudo encontrar la empresa creada/actualizada")

        except Exception as e:
            _logger.error(f"Error obteniendo informacion de empresa: {str(e)}")
            raise
