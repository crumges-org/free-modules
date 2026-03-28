# -*- coding: utf-8 -*-

import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class WarehouseSyncMapping(models.Model):
    _name = 'solt.warehouse.sync.mapping'
    _description = 'Mapeador para sincronizar almacen'

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    response_body = fields.Json('Respuesta', default="{}")
    response_mapping = fields.Json('Mapeo de Respuesta', default="{}")
    tn_name = fields.Char('Nombre almacen externo')
    is_synchronized = fields.Boolean(compute='_compute_is_synchronized')

    @api.constrains('warehouse_id')
    def _check_required_request_field(self):
        for record in self:
            if record.warehouse_id:
                mappings = self.env['solt.warehouse.sync.mapping'].search([
                    ('warehouse_id', '=', record.warehouse_id.id),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id),
                ])
                if mappings:
                    raise ValidationError(_(f"El Warehouse {record.warehouse_id.name} ya se encuentra relacionado."))

    @api.depends('warehouse_id')
    def _compute_display_name(self):
        for record in self.sudo():
            display_name = '/'
            if record.warehouse_id:
                display_name = f'{record.warehouse_id.name} - {record.warehouse_id.x_external_id}'

            record.display_name = display_name

    @api.depends('warehouse_id')
    def _compute_is_synchronized(self):
        for record in self:
            record = record.with_company(record.company_id or self.env.comapny)
            record.is_synchronized = bool(record.warehouse_id and record.warehouse_id.x_external_id)

    def action_sync_warehouse(self):
        self.ensure_one()
        response_body = self.response_body
        response_mapping = self.response_mapping

        address = response_body.get('address')
        name = response_body.get('name')

        partner_vals = self.warehouse_id._get_or_create_partner_from_api(address, name)

        # update address of wh
        self.warehouse_id.partner_id.write({
            'company_id': partner_vals.get('company_id'),
            "x_state_sync": partner_vals.get('x_state_sync'),
            "x_date_last_sync": partner_vals.get('x_date_last_sync'),
            "x_store_external_id": partner_vals.get('x_store_external_id'),
            "x_exclud_from_sync": partner_vals.get('x_exclud_from_sync'),
            'region_id': partner_vals.get('region_id'),
        })

        self.warehouse_id.with_context(not_execute_warehouse_base_automation=True).write({
            "x_external_id": response_mapping.get('x_external_id'),
            "sequence": response_mapping.get('sequence'),
            "x_state_sync": "yes",
            "x_date_last_sync": fields.Datetime.now(),
            "x_store_external_id": response_mapping.get('x_store_external_id'),
            "x_exclud_from_sync": response_mapping.get('x_exclud_from_sync')
        })
        _logger.info(_(f"Almacen {self.warehouse_id.name}, sincronizado!"))
        return True

    def action_create_warehouse(self):
        self.ensure_one()

        response_body = self.response_body
        response_mapping = self.response_mapping

        address = response_body.get('address')
        name = response_body.get('name')

        partner_vals = self.warehouse_id._get_or_create_partner_from_api(address, name)
        partner = self.env['res.partner'].sudo().search(
            [('name', '=', name), ('company_id', 'in', [False, self.company_id.id])], limit=1)
        if not partner:
            partner = self.env['res.partner'].sudo().create(partner_vals)
        response_mapping['partner_id'] = partner.id
        response_mapping['x_date_last_sync'] = fields.Datetime.now()
        stock_warehouse_id = self.env['stock.warehouse'].sudo().with_context(
            not_execute_warehouse_base_automation=True).create(response_mapping)
        _logger.info(_(f"Warehouse {stock_warehouse_id.name}, created and synchronized!"))
        self.warehouse_id = stock_warehouse_id
        return True