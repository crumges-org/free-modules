import base64
import json
import logging
import re

import requests

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class SoltApiEndpoint(models.Model):
    _name = 'solt.api.endpoint'
    _description = 'API Endpoint'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    connector_id = fields.Many2one('solt.api.connector', string='API Connector', required=True, ondelete='cascade')
    endpoint_path = fields.Char('Endpoint path', required=True, help="Endpoint path. You can use variables such as {{variable}}")
    method = fields.Selection([('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('PATCH', 'PATCH'), ('DELETE', 'DELETE')], string='HTTP method', default='GET', required=True)
    model_id = fields.Many2one('ir.model', string='Odoo model')
    request_mapping = fields.Json('Request mapping', help="""Defines how Odoo data is transformed into the external API payload.

Request format (Odoo → API):
{
  "api_field": "fixed_value",                       # Constant value
  "other_field": {"field": "odoo_field.subfield"},  # Odoo field (dot notation)
  "number_data": {"field": "odoo_field", "type": "float"},  # Type conversion
  "custom_data": {"field": "odoo_field", "transform": "value.upper()"},  # Transformation
  "param": {"payload": "param_name"},          # Payload/parameter value
  "items": {                                       # one2many/array support
    "source": "line_ids",
    "items": [
      {"name": {"field": "name"}, "qty": {"field": "quantity"}}
    ]
  }
}
""", default="{}")

    response_mapping = fields.Json('Response mapping', help="""Defines how API responses are transformed into Odoo data.

Response format (API → Odoo):
{
  "odoo_field": "data['field_name']",             # Direct Python expression
  "other_field": "data.get('field', 'default')",  # With defaults
  "date_field": "fields.Date.to_date(data['date'])",  # Type conversion
  "partner_id": "env['res.partner'].search([('ref', '=', data['client_id'])], limit=1).id",  # Relational field
  "state": "'paid' if float(data['amount']) > 0 else 'draft'",  # Conditional expression
  "line_ids": "[{'product_id': env['product.product'].search([('default_code', '=', item['code'])], limit=1).id, 'quantity': float(item['qty'])} for item in data.get('items', [])]"  # one2many
}

Expressions can access:
- data: response data
- env: Odoo environment
- record: current record (for updates)
- fields: Odoo fields helper for conversions
- plus datetime, json, re, etc.
""", default="{}")

    request_param = fields.Json('Request parameters', help="JSON definition for additional request parameters", default="{}")
    headers = fields.Json('Extra headers', help="Additional headers in JSON format")
    pagination_enabled = fields.Boolean('Enable pagination', default=False)
    pagination_param = fields.Char('Page parameter', default='page')
    pagination_size_param = fields.Char('Page size parameter', default='limit')
    pagination_size = fields.Integer('Page size', default=100)
    sequence = fields.Integer(string="Sequence", default=10)
    check_required_request_field = fields.Boolean("Validate required fields")
    required_request_field = fields.Json("Required fields", help="API fields that must be sent in the request. Comma-separated char field with API field names")
    request_as_array = fields.Boolean('Send request as array', default=False, help="When enabled, the request will be sent as a raw array based on the mapping configuration")

    _sql_constraints = [('code_unique', 'UNIQUE(code)', 'Endpoint code must be unique.'), ]

    @api.constrains('required_request_field')
    def _check_required_request_field(self):
        for record in self:
            if record.required_request_field and record.check_required_request_field:
                if not record.request_mapping:
                    raise ValidationError(_(f"El endpoint {record.code}, tiene configurado los campos requeridos que debe tener la Solicitud, "
                                            f"pero no se encuentra una configuración en el Mapeo de la Solicitud"))
                mapping_config = json.loads(record.request_mapping)
                required_request_field = json.loads(record.required_request_field)
                missing_api_fields = []
                for api_field in required_request_field.keys():
                    if api_field.strip() not in mapping_config:
                        missing_api_fields.append(api_field)
                if missing_api_fields:
                    raise ValidationError(_(f"El endpoint {record.code}, tiene configurado los campos requeridos que debe tener la Solicitud, "
                                            f"pero se encontraron los campos siguientes: {','.join(missing_api_fields)} sin configurar en el Mapeo de la Solicitud."))

    @api.constrains('request_param')
    def _check_request_param(self):
        return True

    @api.constrains('request_as_array')
    def _check_request_as_array(self):
        for endpoint in self:
            if endpoint.request_as_array:
                if not endpoint.request_mapping:
                    raise ValidationError(_(f"El endpoint {endpoint.code}, tiene configurado realizar el Request como un array de jsons, "
                                            f"pero no se encuentra una configuración en el Mapeo de la Solicitud."))
                mapping_config = json.loads(endpoint.request_mapping)
                is_request_as_array = False
                for field_key, field_config in mapping_config.items():
                    if isinstance(field_config, dict) and 'source' in field_config:
                        is_request_as_array = True
                        break
                if not is_request_as_array and 'array_source' not in mapping_config:
                    raise ValidationError(_(f"El endpoint {endpoint.code}, tiene configurado realizar el Request como un array de jsons, "
                                            f"pero no tiene configurado correctamente el Mapeo de la Solicitud. "
                                            f"No se encuentran las propiedades source o array_source."))

    # prepare request data Odoo → API
    def _prepare_request_data(self, record=None, data=None):
        """Prepares data to send according to the configured format"""
        if not data:
            data = {}
        if not self.request_mapping:
            return {}
        try:
            mapping_config = json.loads(self.request_mapping)

            # Check PUT context to send only modified fields
            modified_fields = self._context.get('modified_fields', [])
            if modified_fields and self.method == 'PUT':
                required_api_field = {}
                if self.required_request_field:
                    required_api_field = json.loads(self.required_request_field)
                modified_fields = set(modified_fields + list(required_api_field.values()))
                filtered_mapping = {}
                for field_key, field_config in mapping_config.items():
                    should_include = False
                    if 'field' in field_config:
                        odoo_field_root = field_config['field'].split('.')[0]
                        if odoo_field_root in modified_fields:
                            should_include = True
                    elif 'source' in field_config and field_config['source'] in modified_fields:
                        should_include = True
                    elif 'expression' in field_config:
                        expression = field_config['expression']
                        field_patterns = [r'record\.(\w+)', r'item\.(\w+)', r'\.(\w+)', ]
                        found_fields = set()
                        for pattern in field_patterns:
                            matches = re.findall(pattern, expression)
                            found_fields.update(matches)

                        if found_fields.intersection(modified_fields):
                            should_include = True
                        elif required_api_field and field_key in required_api_field:
                            if required_api_field[field_key] in modified_fields:
                                should_include = True
                    if should_include:
                        filtered_mapping[field_key] = field_config
                if filtered_mapping:
                    mapping_config = filtered_mapping

            # Formato de array de json
            if self.request_as_array:
                return self._prepare_array_request_data(mapping_config, record, data)
            return self._process_compact_mapping_to_api(mapping_config, record, data)
        except Exception as e:
            _logger.error(f"Error in _prepare_request_data: {str(e)}")
            raise UserError(_("Error preparing request data: %s") % e)

    def _process_compact_mapping_to_api(self, mapping_config, record=None, data=None, eval_context=None):
        """Processes compact mapping from Odoo to external API"""
        result = {}
        if eval_context is None or not eval_context:
            eval_context = self._get_eval_context(data, record)
        else:
            eval_context = eval_context
        for field_key, field_config in mapping_config.items():
            try:
                if not isinstance(field_config, dict):
                    result[field_key] = field_config
                    continue
                if 'field' in field_config and record:
                    field_value = self._get_field_value(record, field_config['field'])
                    if field_value is not None and 'type' in field_config:
                        field_value = self._convert_field_value(field_value, field_config['type'])
                    if field_value is not None and 'transform' in field_config:
                        field_value = self._apply_transform(field_value, field_config['transform'], eval_context)
                    if field_value is not None:
                        result[field_key] = field_value
                elif 'payload' in field_config and data:
                    result[field_key] = data.get(field_config['payload'])
                elif 'source' in field_config and 'items' in field_config and record:
                    result[field_key] = self._process_one2many_field(record, field_config, eval_context)
                elif 'expression' in field_config:
                    # Soporte para expresiones Python directas
                    result[field_key] = safe_eval(field_config['expression'], eval_context)
            except Exception as e:
                _logger.error(f"Error procesando campo '{field_key}': {str(e)}")
        return result

    def _get_field_value(self, record, field_path):
        """Gets the value of a field from an Odoo record"""
        field_value = record
        path_parts = field_path.split('.')
        for idx, field_name in enumerate(path_parts):
            if not field_value or not hasattr(field_value, field_name):
                return None
            # Obtener el campo y su tipo
            field_obj = None
            if hasattr(field_value, '_fields') and field_name in field_value._fields:
                field_obj = field_value._fields[field_name]
            # Obtener el valor del campo
            field_value = getattr(field_value, field_name)
            if idx == len(path_parts) - 1:
                if isinstance(field_value, models.BaseModel):
                    # many2one
                    if field_obj and field_obj.type == 'many2one' and len(field_value) == 1:
                        return field_value.id
                    # one2many y many2many
                    elif field_obj and field_obj.type in ('one2many', 'many2many'):
                        return field_value.ids
                    else:
                        return field_value
                    return field_value
                else:
                    return field_value
        return field_value

    def _apply_transform(self, value, transform_code, eval_context):
        """Applies a transformation to a value"""
        ctx = dict(eval_context)
        ctx['value'] = value
        try:
            return safe_eval(transform_code, ctx)
        except Exception as e:
            _logger.error(f"Error al aplicar transformación '{transform_code}': {str(e)}")
            return value

    def _process_one2many_field(self, record, field_config, eval_context):
        """Processes a one2many/many2many field"""
        source_records = getattr(record, field_config['source'], [])
        if not source_records:
            return []

        item_template = field_config['items'][0] if field_config['items'] else {}
        items_result = []
        for item_record in source_records:
            item_data = {}
            current_context = eval_context.copy()
            current_context['item'] = item_record
            current_context['record'] = record  # Mantener record padre
            for item_key, item_config in item_template.items():
                try:
                    if isinstance(item_config, dict):
                        if 'expression' in item_config:
                            item_data[item_key] = safe_eval(item_config['expression'], current_context)
                        elif 'field' in item_config:
                            # Manejar campos con prefijo 'item.'
                            if item_config['field'].startswith('item.'):
                                # Campo del item actual
                                field_name = item_config['field'][5:]  # Remover 'item.'
                                item_value = self._get_field_value(item_record, field_name)
                            else:
                                # Campo del record principal o del item según contexto
                                try:
                                    item_value = self._get_field_value(record, item_config['field'])
                                except:
                                    item_value = self._get_field_value(item_record, item_config['field'])
                            if item_value is not None and 'type' in item_config:
                                item_value = self._convert_field_value(item_value, item_config['type'])
                            if item_value is not None and 'transform' in item_config:
                                item_value = self._apply_transform(item_value, item_config['transform'], current_context)
                            if item_value is not None:
                                item_data[item_key] = item_value
                        elif 'source' in item_config and 'items' in item_config:
                            item_data[item_key] = self._process_one2many_field(item_record, item_config, current_context)
                    else:
                        item_data[item_key] = item_config
                except Exception as e:
                    _logger.error(f"Error procesando sub-campo '{item_key}' en array anidado: {str(e)}")
            if item_data:
                items_result.append(item_data)
        return items_result

    def _prepare_array_request_data(self, mapping_config, record=None, data=None):
        """Prepares data for requests requiring direct array format"""
        try:
            # Verificar si hay configuración de array_source (array simple)
            if 'array_source' in mapping_config:
                return self._prepare_simple_array_request(mapping_config, record, data)

            # Si no hay array_source, procesar como estructura compleja
            return self._prepare_complex_array_request(mapping_config, record, data)

        except Exception as e:
            _logger.error(f"Error en _prepare_array_request_data: {str(e)}")
            raise UserError(_("Error al preparar datos de array: %s") % e)

    def _prepare_simple_array_request(self, mapping_config, record=None, data=None):
        """Prepares simple array based on array_source"""
        array_source = mapping_config.get('array_source')
        item_mapping = mapping_config.get('item_mapping', {})

        if not array_source or not record:
            return []

        # Obtener los registros fuente
        source_records = getattr(record, array_source, [])
        if not source_records:
            return []

        result = []
        base_eval_context = self._get_eval_context(data, record)
        for item_record in source_records:
            item_data = {}
            current_context = base_eval_context.copy()
            current_context['item'] = item_record  # Adicionar el item actual al contexto
            current_context['record'] = record  # Mantener record padre
            try:
                item_data = self._process_compact_mapping_to_api(item_mapping, item_record, data, eval_context=current_context)
            except Exception as e:
                _logger.error(f"Error procesando campo {array_source} en array item: {str(e)}")
                continue

            if item_data:
                result.append(item_data)

        return result

    def _prepare_complex_array_request(self, mapping_config, record=None, data=None):
        """Prepares complex structure with multiple objects and nested arrays"""
        if not record:
            return []

        result = {}
        base_eval_context = self._get_eval_context(data, record)
        base_eval_context['record'] = record

        # Procesar todos los campos de mapeo
        for field_key, field_config in mapping_config.items():
            try:
                if isinstance(field_config, dict):
                    if 'expression' in field_config:
                        # Expresión directa
                        result[field_key] = safe_eval(field_config['expression'], base_eval_context)
                    elif 'field' in field_config:
                        # Campo simple del record principal
                        field_value = self._get_field_value(record, field_config['field'])
                        if field_value is not None and 'type' in field_config:
                            field_value = self._convert_field_value(field_value, field_config['type'])
                        if field_value is not None and 'transform' in field_config:
                            field_value = self._apply_transform(field_value, field_config['transform'], base_eval_context)
                        if field_value is not None:
                            result[field_key] = field_value
                    elif 'source' in field_config and 'items' in field_config:
                        # Array anidado - procesar
                        result[field_key] = self._process_one2many_field(record, field_config, base_eval_context)
                else:
                    result[field_key] = field_config
            except Exception as e:
                _logger.error(f"Error procesando campo '{field_key}' en estructura compleja: {str(e)}")

        return [result]

    # process response data API → Odoo
    def _process_response(self, response_data, target_record=None):
        """Processes the API response according to the configured mapping"""
        if not self.model_id or not self.response_mapping:
            return {'raw_response': response_data}
        try:
            mapping_config = json.loads(self.response_mapping)

            # response_data es una list. Ej: Response de un metodo GET que devuelve un listado de data
            # sin paginacion
            if isinstance(response_data, list):
                _logger.info(f"Processing direct list response with {len(response_data)} elements")
                processed_items = []

                for item in response_data:
                    values_to_write = self._process_simple_mapping_to_odoo(mapping_config, item, target_record)
                    if values_to_write:
                        processed_items.append(values_to_write)

                return {'raw_response': response_data, 'values': processed_items, }
            # response_data es una list con paginacion
            elif isinstance(response_data, dict):
                result_list = None
                result_key = None

                for key, value in response_data.items():
                    if isinstance(value, list) and value and key in ["items"]:
                        result_list = value
                        result_key = key
                        break

                if result_list and result_key:
                    _logger.info(f"Processing paginated response with {len(result_list)} elements in key '{result_key}'")
                    processed_items = []

                    for item in result_list:
                        values_to_write = self._process_simple_mapping_to_odoo(mapping_config, item, target_record)
                        if values_to_write:
                            processed_items.append(values_to_write)

                    return {'raw_response': response_data, 'values': processed_items, }
                # es un dict simple
                else:
                    values_to_write = self._process_simple_mapping_to_odoo(mapping_config, response_data, target_record)
                    return {'raw_response': response_data, 'values': values_to_write}
            else:
                _logger.warning(f"Unsupported response type: {type(response_data)}")
                return {'raw_response': response_data, 'error': True, 'error_message': 'Unsupported response type'}

        except Exception as e:
            _logger.error(f"Error procesando respuesta: {str(e)}")
            return {'raw_response': response_data, 'error': str(e)}

    def _process_simple_mapping_to_odoo(self, mapping_config, api_data, target_record=None):
        """Processes simple mapping from external API to Odoo using Python expressions"""
        result = {}
        eval_context = self._get_eval_context(api_data, target_record)
        eval_context['data'] = api_data
        for odoo_field, expression in mapping_config.items():
            try:
                if isinstance(expression, str):
                    result[odoo_field] = safe_eval(expression, eval_context)
                elif isinstance(expression, dict) and 'source' in expression:
                    api_value = self._get_api_value(api_data, expression['source'])
                    if api_value is not None and 'type' in expression:
                        api_value = self._convert_field_value(api_value, expression['type'])
                    if api_value is not None and 'transform' in expression:
                        api_value = self._apply_transform(api_value, expression['transform'], eval_context)
                    if 'relation' in expression and isinstance(expression['relation'], dict):
                        api_value = self._process_relation_field(expression['relation'], api_value)
                    if api_value is not None:
                        result[odoo_field] = api_value
            except Exception as e:
                _logger.error(f"Error procesando campo '{odoo_field}': {str(e)}")
        return result

    def _get_api_value(self, api_data, source_path):
        """Gets the value of a field from the API data"""
        value = api_data
        for key in source_path.split('.'):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def _process_relation_field(self, relation_config, api_value):
        """Processes a relational field (many2one)"""
        model_name = relation_config.get('model')
        field_name = relation_config.get('field', 'id')
        create_if_missing = relation_config.get('create', False)
        if not model_name or not api_value:
            return None
        related_model = self.env[model_name]
        related_record = related_model.search([(field_name, '=', api_value)], limit=1)
        if related_record:
            return related_record.id
        elif create_if_missing:
            create_vals = {field_name: api_value}
            if hasattr(related_model, 'name') and 'name' not in create_vals:
                create_vals['name'] = api_value
            new_record = related_model.create(create_vals)
            return new_record.id
        return None

    def _convert_field_value(self, value, target_type):
        """Converts a value to the specified type"""
        try:
            if target_type == 'string':
                return str(value)
            elif target_type == 'integer':
                return int(float(value))
            elif target_type == 'float':
                return float(value)
            elif target_type == 'boolean':
                return value.lower() in ('true', 't', 'yes', 'y', '1') if isinstance(value, str) else bool(value)
            elif target_type == 'date':
                return fields.Date.to_date(value) if isinstance(value, str) else value
            elif target_type == 'datetime':
                return fields.Datetime.to_datetime(value) if isinstance(value, str) else value
        except Exception as e:
            _logger.error(f"Error convirtiendo valor '{value}' a tipo '{target_type}': {str(e)}")
        return value

    # utils methods
    def _get_eval_context(self, data=None, record=None):
        """Obtains the context for expression evaluation"""
        model_name = self.model_id.sudo().model if self.model_id else self._context.get('active_model')
        model = self.env[model_name] if model_name else None

        def execute_function(func_name, *args, **kwargs):
            if record and hasattr(record, func_name):
                func = getattr(record, func_name)
                return func(*args, **kwargs)
            elif hasattr(self, func_name):
                func = getattr(self, func_name)
                return func(*args, **kwargs)
            elif model is not None and hasattr(model, func_name):
                func = getattr(model, func_name)
                return func(*args, **kwargs)
            else:
                raise UserError(_("Function '%s' not found in evaluation context.") % func_name)

        return {'env':    self.env, 'model': model, 'record': record, 'uid': self._uid, 'user': self.env.user, 'time': tools.safe_eval.time, 'datetime': tools.safe_eval.datetime, 'dateutil': tools.safe_eval.dateutil, 'payload': data, 'data': data, 'Command': fields.Command,
                'method': execute_function, 'float_compare': float_compare, 'b64encode': base64.b64encode, 'b64decode': base64.b64decode, }

    def _prepare_endpoint_path(self, record=None, data=None):
        """Prepares the endpoint path by evaluating variables in {}"""
        if not self.endpoint_path:
            return ''
        endpoint_path = self.endpoint_path.strip()
        eval_context = self._get_eval_context(data, record)
        for expr in re.findall(r'\{(.*?)\}', endpoint_path):
            try:
                value = safe_eval(expr.strip(), eval_context)
                endpoint_path = endpoint_path.replace(f'{{{expr}}}', str(value) if value is not None else '')
            except Exception as e:
                _logger.error(f"Error evaluating expression '{expr}' in endpoint_path: {str(e)}")
                raise UserError(_("Error evaluating endpoint path: %s") % e)
        return endpoint_path

    def _get_auth_headers(self, data=None, record=None):
        """Gets the connector's authentication headers and evaluates them in the context"""
        headers = self.connector_id._get_auth_headers()
        if self.headers:
            try:
                custom_headers = json.loads(self.headers)
                eval_context = self._get_eval_context(data, record)
                for key, value in custom_headers.items():
                    custom_headers[key] = safe_eval(value, eval_context)
                headers.update(custom_headers)
            except Exception as e:
                _logger.error(f"Error evaluating custom headers: {str(e)}")
                raise UserError(_("Error evaluating custom headers: %s") % e)
        return headers

    def execute_request(self, record=None, params=None, data=None, request_data=None):
        """Executes a request to the API according to the endpoint configuration"""
        # Si es GET y la paginación está habilitada, usar el método de paginación
        if self.method == 'GET' and self.pagination_enabled:
            return self._execute_paginated_request(record, params, data)

        # Caso normal sin paginación
        start_time = fields.Datetime.now()
        if not request_data:
            request_data = self._prepare_request_data(record, data)
        elif request_data and not isinstance(request_data, dict) and not isinstance(request_data, list):
            request_data = self._prepare_request_data(record, data)
        else:
            request_data = request_data
        endpoint_params = {}
        if self.request_param:
            endpoint_params = json.loads(self.request_param)
        request_params = params or {}
        request_params = {**request_params, **endpoint_params}
        connector = self.connector_id
        url = connector._prepare_api_url(self._prepare_endpoint_path(record, data))
        headers = self._get_auth_headers(data, record)
        log_vals = {'connector_id': connector.id, 'endpoint_id': self.id, 'request_url': url, 'request_method': self.method, 'request_headers': json.dumps(headers), 'request_params': json.dumps(request_params),
                'request_body':     json.dumps(request_data) if request_data else False, }
        try:
            _logger.info(f"Request: {request_data}")
            response = self._send_request(url, request_params, request_data, headers, connector.timeout)
            end_time = fields.Datetime.now()
            status_code = response.status_code
            log_vals.update({'response_code': status_code, 'response_body': response.text, 'success': 200 <= status_code < 300, 'duration': (end_time - start_time).total_seconds(), })
            self.env['solt.api.call.log'].create(log_vals)
            try:
                response_data = response.json() if response.text else {}
            except ValueError:
                response_data = {'text': response.text}
            if 200 <= status_code < 300:
                result = self._process_response(response_data, record)
                result['status_code'] = status_code
                return result
            else:
                return {'status_code': status_code, 'error': True, 'error_message': _(f"Error en la llamada a la API: Código {status_code}, Descripcion {response_data.get('description')}, Mensaje {response_data.get('message', '')}"), 'raw_response': response_data}
        except requests.exceptions.RequestException as e:
            end_time = fields.Datetime.now()
            log_vals.update({'response_code': 0, 'response_body': str(e), 'success': False, 'duration': (end_time - start_time).total_seconds(), })
            self.env['solt.api.call.log'].create(log_vals)
            raise UserError(_("Error de conexión: %s") % str(e))

    def _send_request(self, url, params, data, headers, timeout):
        """Sends the HTTP request according to the configured method"""
        if self.method == 'GET':
            return requests.get(url, params=params, headers=headers, timeout=timeout)
        elif self.method == 'POST':
            return requests.post(url, params=params, json=data, headers=headers, timeout=timeout)
        elif self.method == 'PUT':
            return requests.put(url, params=params, json=data, headers=headers, timeout=timeout)
        elif self.method == 'PATCH':
            return requests.patch(url, params=params, json=data, headers=headers, timeout=timeout)
        elif self.method == 'DELETE':
            return requests.delete(url, params=params, headers=headers, timeout=timeout)
        else:
            raise ValidationError(_("Método HTTP no soportado."))

    # pagination methods
    def _execute_paginated_request(self, record=None, params=None, data=None):
        """Executes paginated requests to the API and combines the results"""
        start_time = fields.Datetime.now()
        all_results = []  # Lista para almacenar todos los resultados
        current_page = 1
        has_more_pages = True
        combined_response = None

        request_data = self._prepare_request_data(record, data)
        endpoint_params = {}
        if self.request_param:
            endpoint_params = json.loads(self.request_param)
        request_params = params or {}
        request_params = {**request_params, **endpoint_params}
        connector = self.connector_id
        url = connector._prepare_api_url(self._prepare_endpoint_path(record, data))
        headers = self._get_auth_headers(data, record)

        # Añadir los parámetros de paginación iniciales
        if self.pagination_param:
            request_params[self.pagination_param] = current_page
        if self.pagination_size_param and self.pagination_size:
            request_params[self.pagination_size_param] = self.pagination_size

        while has_more_pages:
            log_vals = {'connector_id': connector.id, 'endpoint_id': self.id, 'request_url': url, 'request_method': self.method, 'request_headers': json.dumps(headers), 'request_params': json.dumps(request_params),
                    'request_body':     json.dumps(request_data) if request_data else False, }

            try:
                page_start_time = fields.Datetime.now()
                response = self._send_request(url, request_params, request_data, headers, connector.timeout)
                page_end_time = fields.Datetime.now()

                log_vals.update({'response_code': response.status_code, 'response_body': response.text, 'success': 200 <= response.status_code < 300, 'duration': (page_end_time - page_start_time).total_seconds(), })
                self.env['solt.api.call.log'].create(log_vals)

                if 200 <= response.status_code < 300:
                    response_data = response.json() if response.text else {}

                    # Procesar la respuesta para extraer resultados y determinar si hay más páginas
                    page_results, has_more_pages = self._extract_page_results(response_data)

                    # Añadir resultados a la lista acumulada
                    if page_results:
                        all_results.extend(page_results)

                    # Guardar la primera respuesta completa para procesamiento posterior
                    if current_page == 1:
                        combined_response = response_data

                    # Si hay más páginas, actualizar el número de página para la siguiente solicitud
                    if has_more_pages:
                        current_page += 1
                        if self.pagination_param:
                            request_params[self.pagination_param] = current_page
                elif response.status_code == 404 and combined_response is not None:
                    _logger.error(_("Error en la llamada a la API (página %s): Código %s - %s") % (current_page, response.status_code, response.text))
                    has_more_pages = False
                else:
                    raise UserError(_("Error en la llamada a la API (página %s): Código %s - %s") % (current_page, response.status_code, response.text))

            except requests.exceptions.RequestException as e:
                page_end_time = fields.Datetime.now()
                log_vals.update({'response_code': 0, 'response_body': str(e), 'success': False, 'duration': (page_end_time - page_start_time).total_seconds(), })
                self.env['solt.api.call.log'].create(log_vals)
                raise UserError(_("Error de conexión en página %s: %s") % (current_page, str(e)))

        # Combinar todos los resultados en la estructura de respuesta original
        if combined_response is not None:
            combined_response = self._combine_paginated_results(combined_response, all_results)
        else:
            # Si no hay respuesta combinada pero hay resultados, crear una estructura básica
            combined_response = {"items": all_results} if all_results else {}

        end_time = fields.Datetime.now()
        _logger.info(f"Solicitud paginada completada. Total páginas: {current_page}, "
                     f"Tiempo total: {(end_time - start_time).total_seconds()} segundos, "
                     f"Total elementos: {len(all_results)}")

        # Procesar la respuesta combinada
        return self._process_response(combined_response, record)

    def _extract_page_results(self, response_data):
        """
        Extrae los resultados de una página y determina si hay más páginas
        Retorna: (page_results list, has_more_pages)

        Este método debe adaptarse según cómo la API específica maneja la paginación
        """
        # Determinar dónde están los resultados en la respuesta
        # Esto depende de la estructura de respuesta de la API
        results = []
        has_more = False

        if isinstance(response_data, list):
            results = response_data
            # Asumir que hay más páginas si el número de resultados es igual al tamaño de página
            has_more = len(results) >= self.pagination_size if self.pagination_size else False

        return results, has_more

    def _combine_paginated_results(self, first_response, all_results):
        """
        Combina todos los resultados paginados en la estructura de la primera respuesta
        """
        if isinstance(first_response, list) and first_response:
            combined_response = dict(first_response[0])
        else:
            combined_response = dict(first_response)  # Copia la estructura original

        # Si no encontramos una clave estándar, buscar la primera lista
        for key, value in combined_response.items():
            if isinstance(value, list) and key in ['items']:
                combined_response[key] = all_results
                return combined_response

        # Si no hay estructura clara, añadir los resultados bajo una clave genérica
        combined_response["items"] = all_results
        return combined_response
