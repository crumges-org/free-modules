# -*- coding: utf-8 -*-
import json
import logging
import time
from datetime import datetime

import requests

from odoo import models, fields, _, api
from odoo.addons.solt_tiendanube import utils
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    callback_url = fields.Char(string='Callback URL', help="URL to send synchronization status callbacks", prefetch=False)
    sync_token = fields.Char(string='Sync Token', help="Unique token for synchronization", index=True, prefetch=False)
    use_sale_multi_stock = fields.Boolean(string='Use multi warehouse in Sales Orders', readonly=False)

    def _sync_inventory(self, offset, limit):
        """ Sincronizar la disponibilidad del inventario de los productos vendidos en TN.

        Si se llama en un conjunto de registros vacio, se sincronizan los productos de todas las tiendas activas

        Note: Este metodo es llamado por el cron `ir_cron_sync_tn_inventory`.

        :return: None
        """
        self = self or self.search([])
        stores = self.filtered(lambda c: c.bearer_token and c.external_id and c.connector_id and c.connector_id.active)
        if not stores:
            return

        _logger.info(
            'Starting Cron: Sync Inventory with the parameters [{}|{}]'.format(offset, limit)
        )

        # start time
        start_time = time.time()

        try:
            for company in stores:
                _logger.info(f"Store: {company.name}")
                count_updated = 0
                offset_arg = offset
                model_name = 'product.template'
                domain = [
                    ('type', '=', 'consu'),
                    ('is_storable', '=', True),
                    ('x_external_id', 'not in', ['', False]),
                    ('x_exclud_from_sync', '=', False),
                    ('company_id', '=', company.id)
                ]
                limit_max = self.env[model_name].with_company(company).search_count(domain)

                endpoint = self.env['solt.api.endpoint'].search([
                    ('code', '=', 'PRODUCT_VARIANT_STOCK_PRICE_PATCH'),
                    ('connector_id', '=', company.connector_id.id)
                ], limit=1)
                if not endpoint:
                    raise UserError(_(f"Endpoint PRODUCT_VARIANT_STOCK_PRICE_PATCH is not configured!"))
                request_mapping_config = json.loads(endpoint.request_mapping)
                if not request_mapping_config:
                    raise UserError(_(f"Endpoint PRODUCT_VARIANT_STOCK_PRICE_PATCH is misconfigured!"))

                while True:
                    records_paginated = utils.search_paginated(self.env, model_name, company, domain, limit_max=limit_max, offset=offset_arg, limit=limit)
                    # Process records for the current page
                    products = records_paginated['records']
                    total_products = records_paginated['total_records']
                    _logger.info("Total of products to process. Total: {}".format(len(products)))

                    # prepare request mapping
                    request_data = []
                    for producto in products:
                        request_data += endpoint._prepare_array_request_data(request_mapping_config, producto, data={})

                    if request_data and products:
                        response = endpoint.with_company(company).execute_request(request_data=request_data)
                        _logger.info('PRODUCT_VARIANT_STOCK_PRICE_PATCH')
                        _logger.info(response)
                        if 200 <= response.get('status_code') < 300:
                            _logger.info(f"Updated stock of a total of products {len(products)}")
                        else:
                            _logger.error(
                                f"Error updating product stock: {response.get('error_message', '')}")

                    count_updated += len(products)
                    if count_updated < total_products:
                        offset_arg += limit
                        _logger.info(
                            u'Updated {} records of {}'.format(count_updated, total_products))
                    else:
                        _logger.info(
                            u'Updated {} records of {}'.format(
                                count_updated, total_products)
                        )
                        break
        except Exception as e:
            _logger.error("Exception: {}".format(e))

        # calculate elapsed time
        elapsed_time = time.time() - start_time
        hours, rem = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(rem, 60)

        # log
        _logger.info(
            'End Cron: Sync Inventory with the parameters [{}|{}], time: {:0>2}:{:0>2}:{:05.2f}'.format(
                offset, limit, int(hours), int(minutes), seconds))

    def _check_external_config(self):
        """
        Valida si la empresa esta configurada correctamente con TN
        :return: ValidationError or True
        """
        self.ensure_one()
        if not self.bearer_token or not self.external_id:
            raise ValidationError(_(f"La empresa {self.name} no tiene configurado una tienda."))
        return True

    def _sync_variants_cost(self, offset, limit):
        """ Sincronizar el costo de los productos vendidos en TN.

        Si se llama en un conjunto de registros vacio, se sincronizan los productos de todas las tiendas activas

        Note: Este metodo es llamado por el cron `ir_cron_sync_tn_variant_cost`.

        :return: None
        """

        self = self or self.search([])
        stores = self.filtered(lambda c: c.bearer_token and c.external_id and c.connector_id and c.connector_id.active)
        if not stores:
            return

        product_id = self.env.context.get('product_id')

        _logger.info(
            'Starting Cron: Tiendanube sync variants cost with the parameters [{}|{}]'.format(offset, limit)
        )

        # start time
        start_time = time.time()

        try:
            for company in stores:
                _logger.info(f"Store: {company.name}")
                count_updated = 0
                offset_arg = offset
                model_name = 'product.template'
                if product_id:
                    domain = [('id', 'in', product_id)]
                else:
                    domain = [
                        ('x_external_id', 'not in', ['', False]),
                        ('x_exclud_from_sync', '=', False),
                        ('company_id', '=', company.id)
                    ]
                limit_max = self.env[model_name].with_company(company).search_count(domain)

                while True:
                    records_paginated = utils.search_paginated(self.env, model_name, company, domain, limit_max=limit_max, offset=offset_arg, limit=limit)
                    # Process records for the current page
                    products = records_paginated['records']
                    total_products = records_paginated['total_records']
                    _logger.info("Total of products to process. Total: {}".format(len(products)))

                    for product in products:
                        if product.product_variant_count == 1:
                            code = 'VARIANTE_PRODUCT_SINGLE_UPDATE'
                        else:
                            code = 'VARIANT_PRODUCT_ALL_UPDATE_PATCH'

                        endpoint = self.env['solt.api.endpoint'].search([
                            ('code', '=', code),
                            ('connector_id', '=', company.connector_id.id)
                        ], limit=1)
                        if not endpoint:
                            raise UserError(_(f"Endpoint {code} is not configured!"))
                        response = {}
                        if code == 'VARIANTE_PRODUCT_SINGLE_UPDATE':
                            product_variant_id = self.env['product.product'].search([('product_tmpl_id', '=', product.id)])
                            response = endpoint.with_context(modified_fields=['standard_price']).execute_request(record=product_variant_id)
                        else:
                            request_data = []
                            for variant in product.product_variant_ids:
                                if variant.standard_price > 1:
                                    val = {
                                        'id': variant.x_external_id,
                                        'cost': variant.standard_price,
                                        'values': [variant.convert_translated_field_to_api_format(av.name) for av in variant.product_template_attribute_value_ids],
                                    }
                                    request_data.append(val)
                            if request_data:
                                response = endpoint.execute_request(record=product, request_data=request_data)

                        _logger.info(response)
                        sync_vals = {
                            'x_state_sync': 'yes',
                            'x_exclud_from_sync': False,
                            'x_date_last_sync': fields.Datetime.now()
                        }
                        if response and 200 <= response.get('status_code') < 300:
                            _logger.info(f"Updated cost of the product {product.name}")
                            values = response.get('values')
                            if values and isinstance(values, dict):
                                product.write(sync_vals)
                            if isinstance(values, list):
                                sync_vals = {
                                    'x_state_sync': 'yes',
                                    'x_exclud_from_sync': False,
                                    'x_date_last_sync': fields.Datetime.now()
                                }
                                product.product_variant_ids.write(sync_vals)
                                product.write(sync_vals)
                        else:
                            _logger.error(
                                f"Error updating product {product.name} cost: {response.get('error_message', '')}")

                    count_updated += len(products)
                    if count_updated < total_products:
                        offset_arg += limit
                        _logger.info(
                            u'Updated {} records of {}'.format(count_updated, total_products))
                    else:
                        _logger.info(
                            u'Updated {} records of {}'.format(
                                count_updated, total_products)
                        )
                        break
        except Exception as e:
            _logger.error("Exception: {}".format(e))

        # calculate elapsed time
        elapsed_time = time.time() - start_time
        hours, rem = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(rem, 60)

        # log
        _logger.info(
            'End Cron: Tiendanube sync variants cost with the parameters [{}|{}], time: {:0>2}:{:0>2}:{:05.2f}'.format(
                offset, limit, int(hours), int(minutes), seconds))

    @api.model
    def _sync_solt_install(self):
        for company in self.search([('connector_id', '!=', False)]):
            try:
                company._send_callback()
            except Exception as e:
                _logger.error(f"Error syncing Solt installation for company {company.name}: {str(e)}")

    def _send_callback(self):
        """
        Envia el callback al middleware
        """

        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo-Tiendanube-Integration'
            }
            callback_url = self.callback_url or 'https://tiendanube.soltein.net/tiendanube/sync/callback'
            response = requests.post(
                callback_url,
                json=self._prepare_callback_data(),
                headers=headers,
                timeout=60
            )

            if response.status_code == 200:
                _logger.info(f"Callback enviado exitosamente a: {callback_url}")
            else:
                _logger.error(f"Error enviando callback: {response.status_code} - {response.text}")

        except Exception as e:
            _logger.error(f"Error enviando callback: {str(e)}")

    def _prepare_callback_data(self):
        """
        Prepara los datos para enviar al callback del middleware
        """
        db_info = self._get_database_info()
        # Obtener informacion de modulos instalados
        modules_info = self._get_installed_modules_info()
        sync_token = self.sync_token or db_info.get('uid')
        try:
            # Obtener informacion de la base de datos
            callback_data = {
                'sync_token': sync_token,
                'db_name': db_info.get('db_name'),
                'uid': db_info.get('uid'),
                'success':'success',
                'timestamp': datetime.now().isoformat(),
                'company_id': self.id,
                'company_name': self.name,
                'company_email': self.email,
                'external_id': self.external_id,
                'modules_count': modules_info.get('count', 0),
                'modules_list': modules_info.get('modules', [])
            }
            return callback_data

        except Exception as e:
            _logger.error(f"Error preparando datos de callback: {str(e)}")
            return {
                'sync_token': sync_token,
                'success': False,
                'error_message': f"Error preparando callback: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }

    def _get_database_info(self):
        """
        Get information de la base de datos actual
        """
        try:
            # Obtener el nombre de la base de datos
            db_name = self.env.cr.dbname
            # Obtener el UUID de la base de datos
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            db_uuid = IrConfigParam.get_param('database.uuid')
            return {
                'db_name': db_name,
                'uid': db_uuid
            }
        except Exception as e:
            _logger.error(f"Error obteniendo informacion de base de datos: {str(e)}")
            return {
                'db_name': 'unknown',
                'uid': 1
            }

    def _get_installed_modules_info(self):
        """
        Get information about installed modules.
        """
        try:
            # Search for Soltein related modules
            soltein_modules = self.env['ir.module.module'].sudo().search([
                ('author', 'ilike', 'Soltein SA de CV'),
                ('state', '=', 'installed')
            ])
            modules_list = []
            for module in soltein_modules:
                modules_list.append({
                    'name': module.name,
                    'display_name': module.shortdesc or module.name,
                    'version': module.latest_version or '1.0',
                    'category': module.category_id.name if module.category_id else 'Uncategorized'
                })

            return {
                'count': len(modules_list),
                'modules': modules_list
            }

        except Exception as e:
            _logger.error(f"Error getting modules information: {str(e)}")
            return {
                'count': 0,
                'modules': []
            }
