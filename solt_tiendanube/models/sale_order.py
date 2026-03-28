# -*- coding: utf-8 -*-

import logging

import dateutil.parser
from datetime import datetime, timedelta
import pytz

from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.solt_tiendanube import const

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'solt.integration.model.mixin', 'connector.sync.mixin']

    order_number = fields.Char("Doc. Ext. Order", help="El numero de orden")
    new_version_id = fields.Many2one('sale.order', 'New version', copy=False, readonly=True, tracking=True)
    payment_method_id = fields.Many2one(
        string="Payment method", comodel_name='payment.method'
    )

    # Multi Warehouse fields
    can_use_sale_multi_stock = fields.Boolean(compute='_compute_use_sale_multi_stock')
    warehouse_ids = fields.Many2many(
        'stock.warehouse', string='Warehouse', required=False,
        compute='_compute_warehouse_id', store=True, readonly=False, precompute=True,
        check_company=True)

    @api.depends_context('company', 'uid')
    @api.depends('company_id')
    def _compute_use_sale_multi_stock(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.can_use_sale_multi_stock = order.company_id.use_sale_multi_stock or self.env.company.use_sale_multi_stock

    @api.depends('user_id', 'company_id')
    def _compute_warehouse_id(self):
        super(SaleOrder, self)._compute_warehouse_id()
        for order in self:
            if order.warehouse_id and not order.warehouse_ids:
                order.warehouse_ids = [(4, order.warehouse_id.id)]
            else:
                order.warehouse_ids = []

    @api.onchange("commitment_date")
    def _onchange_commitment_date(self):
        """Actualizar líneas de pedido sin la fecha de entrega
        con la fecha de entrega de la orden de venta"""
        result = super()._onchange_commitment_date() or {}
        if "warning" not in result and self.can_use_sale_multi_stock:
            for line in self.order_line:
                if not line.commitment_date:
                    line.commitment_date = self.commitment_date
        return result

    def _find_or_create_partners_from_data(self, data, type='contact'):
        if not data:
            return False, False, False
        if type in ['contact', 'invoice']:
            contact, delivery, invoice = self.env['res.partner'].sudo()._find_or_create_partners_from_data(data.get("customer", {}))
        else:
            contact, delivery, invoice = self.env['res.partner'].sudo()._find_or_create_partners_from_data(data.get("customer", {}), data.get("shipping_address", {}))
        return contact and contact.id or False, delivery and delivery.id or False, invoice and invoice.id or contact and contact.id

    def _find_fiscal_position_from_data(self, data):
        if not data:
            return False

        contact, delivery, invoice = self.env['res.partner'].sudo()._find_or_create_partners_from_data(data.get("customer", {}))
        fiscal_position = self.env['account.fiscal.position'].with_company(
            self.env.company
        )._get_fiscal_position(contact, delivery)
        return fiscal_position and fiscal_position.id or False

    def convert(self, date_time):
        format = DEFAULT_SERVER_DATETIME_FORMAT  # The format
        now_utc = datetime.now(pytz.timezone('UTC'))
        if not self.env.user.tz:
            raise UserError('Select user timezone.')
        now_timezone = now_utc.astimezone(pytz.timezone(self.env.user.tz))
        UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(format), format) - datetime.strptime(
            now_timezone.strftime(format), format)
        local_datetime = datetime.strptime(date_time, format)
        result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
        return result_utc_datetime.strftime(format)

    def _get_date_from_data(self, date_data):
        date = False
        if date_data:
            date_order = dateutil.parser.parse(date_data)
            date_str = date_order.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            date = self.convert(date_str)

        return date

    def _find_matching_product(self, internal_reference, product_ext_id, variant_ext_id, shipping=False):
        """ Encuentra el producto correspondiente para una referencia interna determinada.

        If no product is found para la referencia interna dada, se buscara el producto por
        el id externo e id de la variante
        se lanza una excepcion

        :param str internal_reference: La referencia interna del producto a buscar.
        :param str product_ext_id: El id externo de producto.
        :param str variant_ext_id: El id externo de la varinate del producto.
        :param bool shipping: Buscar el producto de envio.
        :return: El producto encontrado.
        :rtype: record of `product.product`
        """
        company = self.company_id or self.env.company
        if shipping:
            product = self.env['product.product'].search([
                *self.env['product.product']._check_company_domain(company),
                ('default_code', '=', internal_reference),
            ], limit=1)
            if not product:
                product = self.env['product.product'].sudo().create(
                    {
                        'name': _('Tiendanube Shipping'),
                        'type': 'service',
                        'invoice_policy': 'order',
                        'list_price': 0.0,
                        'company_id': company.id,
                        'taxes_id': None,
                        'default_code': internal_reference,
                        'sale_ok': False,
                        'purchase_ok': False,
                    })
                # product = self.env.ref('solt_tiendanube.shipping_product', raise_if_not_found=False)
        else:
            product = self.env['product.product'].search([
                *self.env['product.product']._check_company_domain(company),
                ('product_tmpl_id.x_external_id', '=', product_ext_id),
                ('x_external_id', '=', variant_ext_id),
            ], limit=1)

        return product

    def _prepare_order_lines_values(self, order_data):

        def convert_to_order_line_values(**kwargs_):
            """ Convertir y completar un diccionario de valores para cumplir con los campos de `sale.order.line`.

            :param dict kwargs_: Los valores a convertir y completar.
            :return: Los valores completados.
            :rtype: dict
            """
            quantity_ = kwargs_.get('quantity', 1)
            return {
                'name': kwargs_.get('description', ''),
                'product_id': kwargs_.get('product_id'),
                'price_unit': kwargs_.get('price_unit'),
                'tax_id': [(6, 0, kwargs_.get('tax_ids', []))],
                'product_uom_qty': quantity_,
                'product_uom': kwargs_.get('product_uom'),
                'display_type': kwargs_.get('display_type', False),
                'x_external_id': kwargs_.get('x_external_id', ''),
                'multi_warehouse_id': kwargs_.get('warehouse_id', False),
                'fulfillmen_external_id': kwargs_.get('fulfillmen_external_id', ''),
                'customer_lead': kwargs_.get('customer_lead', float(0)),
                'commitment_date': kwargs_.get('commitment_date', False),
            }
        if not order_data:
            return []

        currency = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', order_data['currency'])], limit=1
        )
        contact_partner, delivery_partner, invoice_partner = self.env['res.partner'].sudo()._find_or_create_partners_from_data(order_data.get("customer", {}))
        fiscal_position = self.env['account.fiscal.position'].with_company(
            self.env.company
        )._get_fiscal_position(contact_partner, delivery_partner)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        order_lines_values = []
        format = DEFAULT_SERVER_DATETIME_FORMAT
        date_order = order_data.get('created_at')
        converted_date_order = self._get_date_from_data(date_order)
        fulfillments_data = order_data.get("fulfillments")
        for fulfillment in fulfillments_data:
            # Prepare the values for the product line.
            items_data = fulfillment.get('line_items')
            fulfillmen_external_id = fulfillment.get('id')
            shipping_data = fulfillment.get('shipping')
            commited_date = shipping_data.get('max_delivery_date')
            if not commited_date:
                commited_date = date_order
            converted_commited_date = self._get_date_from_data(commited_date)
            customer_lead = (datetime.strptime(converted_commited_date, format) - datetime.strptime(converted_date_order, format)).days
            for item_data in items_data:
                sku = item_data.get('sku', '')
                x_external_id = item_data['external_id']
                quantity = item_data['quantity']
                x_product_id = item_data.get('product', {}).get('product_id')
                variant_id = item_data.get('variant', {}).get('variant_id')
                product_id = self._find_matching_product(
                    sku, x_product_id, variant_id, shipping=False
                )
                sales_price = float(item_data.get('unit_price', {}).get('value', 0.0))
                if not product_id:
                    _logger.error(_(f"Product not found with ID {x_product_id} y ID Variant {variant_id}."))
                description = product_id.display_name if product_id else ''
                # get warehouse
                warehouse_id = self.env['sale.order.line']._get_warehouse_from_data(fulfillment.get('assigned_location'))
                if product_id:
                    order_lines_values.append(Command.create(convert_to_order_line_values(
                        product_id=product_id.id,
                        product_uom=product_id.uom_id.id,
                        description=description,
                        price_unit=sales_price,
                        tax_ids=[],
                        quantity=quantity,
                        x_external_id=x_external_id,
                        warehouse_id=warehouse_id,
                        fulfillmen_external_id=fulfillmen_external_id,
                        customer_lead=customer_lead,
                        commitment_date=converted_commited_date,
                    )))

            # Prepare the values for the delivery charges.
            shipping_code = shipping_data.get('carrier', {}).get('name')
            shipping_product = self._find_matching_product(
                shipping_code, None, None, shipping=True
            )
            if shipping_product and shipping_code:
                consumer_cost = float(shipping_data.get('consumer_cost', {}).get('value', 0.0)) if shipping_data.get(
                    'consumer_cost') else 0.0
                shipping_cost_owner = float(shipping_data.get('merchant_cost', {}).get('value', 0.0)) if shipping_data.get(
                    'merchant_cost') else 0.0

                shipping_price = consumer_cost if not float_is_zero(consumer_cost,
                                                                    precision_digits=precision) else shipping_cost_owner

                # ship_discount
                order_lines_values.append(Command.create(convert_to_order_line_values(
                    product_id=shipping_product.id,
                    description=_(
                        "[%s] Delivery cost", shipping_code
                    ),
                    product_uom=shipping_product.uom_id.id,
                    price_unit=shipping_price,
                    tax_ids=[],
                    quantity=1,
                )))
                # get or create the carrier
                carrier_id = self._find_or_create_carrier_from_data(fulfillment)
                _logger.info(f"Delivery carrier {carrier_id or False}")

        # discount line
        total_fixed_amount_discount = float(order_data.get('discount', 0.0)) if order_data.get('discount') else 0.0
        if not float_is_zero(total_fixed_amount_discount, precision_digits=precision):
            discount_product = self._get_discount_product()
            coupon_discount_data = order_data.get('coupon')
            promotional_discount_data = order_data.get('promotional_discount')
            discount_gateway = float(order_data.get('discount_gateway', 0.0)) if order_data.get('discount_gateway') else 0.0
            discount_coupon = float(order_data.get('discount_coupon', 0.0)) if order_data.get('discount_coupon') else 0.0
            discount_coupon_code = []
            coupon_free_shipping = False
            for coupon_data in coupon_discount_data:
                code = coupon_data.get('code', '')
                type = coupon_data.get('type', '')
                value = float(coupon_data.get('value', '0'))
                if code:
                    discount_coupon_code.append(code)
                if type == 'shipping' and float_is_zero(value, precision_digits=precision):
                    coupon_free_shipping = True
            if discount_coupon_code:
                name = _(f"Coupon discounts: {','.join(discount_coupon_code)}")
                if coupon_free_shipping:
                    shipping_cost_owner = float(order_data.get('shipping_cost_owner')) if order_data.get(
                        'shipping_cost_owner') else 0.0
                    discount_coupon += shipping_cost_owner
                order_lines_values.append(Command.create(self._prepare_discount_line_values(
                    product=discount_product,
                    amount=discount_coupon,
                    taxes=self.env['account.tax'],
                    description=name
                )))

            # promo
            discount_promo_code = []
            promo_total_discount = float(promotional_discount_data.get('total_discount_amount', 0.0))
            for promo_data in promotional_discount_data.get("promotions_applied", []):
                discount_script_type = promo_data.get('discount_script_type', '')
                total_discount_amount = float(promo_data.get('total_discount_amount', 0.0)) if promo_data.get('total_discount_amount') else 0.0
                scope_value_name = promo_data.get('scope_value_name')
                name = f"[{discount_script_type}] {scope_value_name}"
                discount_promo_code.append(name)
            if discount_promo_code:
                promo_discounts = '\n'.join(discount_promo_code)
                promo_name = _(f"Promo discounts: {promo_discounts}")
                order_lines_values.append(Command.create(self._prepare_discount_line_values(
                    product=discount_product,
                    amount=promo_total_discount,
                    taxes=self.env['account.tax'],
                    description=promo_name
                )))

            if not float_is_zero(discount_gateway, precision_digits=precision):
                gateway_name = order_data.get('gateway_name')
                name = f"Discount by {gateway_name}"

                order_lines_values.append(Command.create(self._prepare_discount_line_values(
                        product=discount_product,
                        amount=discount_gateway,
                        taxes=self.env['account.tax'],
                        description=name
                    )))

        return order_lines_values

    def _prepare_discount_line_values(self, product, amount, taxes, description=None):
        vals = {
            'product_id': product.id,
            'sequence': 999,
            'price_unit': -amount,
            'tax_id': [Command.set(taxes.ids)],
            'display_type': False,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id

        }
        if description:
            vals['name'] = description

        return vals

    def _get_discount_product(self):
        """Return product. Product used for line de descuento"""
        company_id = self.company_id or self.env.company
        discount_product = company_id.sale_discount_product_id
        if not discount_product:
            if (
                self.env['product.product'].has_access('create')
                and company_id.has_access('write')
                and company_id._filtered_access('write')
                and company_id.check_field_access_rights('write', ['sale_discount_product_id'])
            ):
                company_id.sale_discount_product_id = self.env['product.product'].create(
                    {
                        'name': _('Discount'),
                        'type': 'service',
                        'invoice_policy': 'order',
                        'list_price': 0.0,
                        'company_id': company_id.id,
                        'taxes_id': None,
                    }
                )
            else:
                raise ValidationError(_(
                    "There does not seem to be any discount product configured for this company yet."
                    " You can either use a per-line discount, or ask an administrator to grant the"
                    " discount the first time."
                ))
            discount_product = company_id.sale_discount_product_id
        return discount_product

    def format_origin(self, order_ref_data):
        if not order_ref_data:
            return ''
        return _(f"Tiendanube Order {order_ref_data}")

    def _find_warehouse_from_data(self, fulfillments_data, type='single'):
        if not isinstance(fulfillments_data, list) or isinstance(fulfillments_data, dict):
            return False

        if isinstance(fulfillments_data, list):
            data = fulfillments_data
        if isinstance(fulfillments_data, dict):
            data = [fulfillments_data]

        if type == 'single':
            val = data[0]
            assigned_location = val.get("assigned_location")
            warehouse_id = self.env['stock.warehouse'].sudo().with_company(self.env.company).search([
                ('x_external_id', '=', assigned_location.get('location_id'))
            ])
            if not warehouse_id:
                _logger.info(
                    _(f"Warehouse not found with ID {assigned_location.get('location_id')} for the company {self.env.company.name}"))
            return warehouse_id and warehouse_id.id or False
        else:
            warehouse_ids = []
            for val in data:
                assigned_location = val.get("assigned_location")
                warehouse_id = self.env['stock.warehouse'].sudo().with_company(self.env.company).search([
                    ('x_external_id', '=', assigned_location.get('location_id'))
                ])
                if not warehouse_id:
                    _logger.info(
                        _(f"Warehouse not found with ID {assigned_location.get('location_id')} for the company {self.env.company.name}"))
                    continue
                warehouse_ids.append(warehouse_id.id)
            return [Command.set(warehouse_ids)]

    def _find_or_create_carrier_from_data(self, fulfillments_data):
        if not isinstance(fulfillments_data, list) and not isinstance(fulfillments_data, dict):
            return False

        if isinstance(fulfillments_data, list):
            data = fulfillments_data
        if isinstance(fulfillments_data, dict):
            data = [fulfillments_data]

        val = data[0]
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        shipping_data = val.get("shipping")
        carrier_data = shipping_data.get('carrier')
        option_data = shipping_data.get('option')
        name = carrier_data.get('name') + '-' + option_data.get('name')
        x_external_id = carrier_data.get('carrier_id') if carrier_data.get('carrier_id') else ''
        shipping_code = option_data.get("name")
        shipping_product = self._find_matching_product(
            shipping_code, None, None, shipping=True
        )
        consumer_cost = float(shipping_data.get('consumer_cost', {}).get('value', 0.0)) if shipping_data.get(
            'consumer_cost') else 0.0
        shipping_cost_owner = float(shipping_data.get('merchant_cost', {}).get('value', 0.0)) if shipping_data.get(
            'merchant_cost') else 0.0

        shipping_price = consumer_cost if not float_is_zero(consumer_cost,
                                                            precision_digits=precision) else shipping_cost_owner
        values = {
            'name': name,
            'x_external_id': x_external_id,
            'company_id': self.env.company.id,
            "x_state_sync": 'yes',
            "x_date_last_sync": datetime.now(),
            "x_store_external_id": self.env.company.external_id,
            'product_id': shipping_product.id,
            'fixed_price': shipping_price
        }
        carrier_id = self.env['delivery.carrier'].sudo().with_company(self.env.company).search([
            '|', ('name', '=', name), ('x_external_id', '=', x_external_id)
        ])
        if not carrier_id:
            try:
                carrier_id = self.env['delivery.carrier'].sudo().create(values)
            except Exception as e:
                _logger.error(f"Error al crear delivery carrier: {e}")

        return carrier_id.id

    def tiendanube_sync_picking_from_order(self, order_response_dict):
        """
        Sincroniza los pickings de la orden de venta
        :param order_response_dict:
        :return:
        """
        self.ensure_one()

        if not isinstance(order_response_dict, dict):
            return False

        fulfillment_sync = []
        picking_to_valiate = self.env['stock.picking']
        for order_line in self.order_line.filtered(
                lambda l: l.product_id.type != 'service' and not l.display_type
        ):
            order_data = order_response_dict[self.x_external_id]
            shipping_status = order_data.get('shipping_status')
            nube_picking = self.env['stock.picking'].sudo().search([('sale_id', '=', self.id), ('location_id.warehouse_id', '=', order_line.warehouse_id.id)])
            if not nube_picking:
                _logger.info(_(f"Picks not created for order {self.name} with origin {self.origin}"))
                continue

            fulfillments_data = order_data.get("fulfillments")

            # get the fulfillment
            found_fulfillment = {}
            for fulfillment in fulfillments_data:
                if order_line.fulfillmen_external_id == fulfillment.get('id'):
                    found_fulfillment = fulfillment
                    break

            if found_fulfillment:
                if found_fulfillment.get('id') not in fulfillment_sync:
                    shipping_data = found_fulfillment.get("shipping")
                    carrier_data = shipping_data.get('carrier')
                    option_data = shipping_data.get('option')
                    name = carrier_data.get('name') + '-' + option_data.get('name')
                    x_external_id = carrier_data.get('carrier_id') if carrier_data.get('carrier_id') else ''
                    carrier_id = self.env['delivery.carrier'].sudo().with_company(self.env.company).search([
                        ('name', '=', name), ('x_external_id', '=', x_external_id)
                    ])

                    vals_to_update = {
                        'carrier_id': carrier_id and carrier_id.id or False,
                        'carrier_tracking_ref': found_fulfillment.get('tracking_info', {}).get('code', ''),
                        'x_external_id': found_fulfillment.get('id'),
                        "x_state_sync": 'yes',
                        "x_date_last_sync": datetime.now(),
                        "x_store_external_id": self.env.company.external_id,
                    }

                    # update the picking
                    nube_picking.sudo().write(vals_to_update)
                    fulfillment_sync.append(found_fulfillment.get('id'))

                fulfillment_status = found_fulfillment.get('status')
                if nube_picking.state not in ['cancel', 'done'] and (shipping_status == 'shipped' or shipping_status == 'partially_fulfilled' and const.STATUS_TO_SYNCHRONIZE[fulfillment_status] == 'DISPATCHED'):
                    stock_move = self.env['stock.move'].search([('sale_line_id', '=', order_line.id)])
                    stock_move._set_quantity_done(order_line.product_uom_qty)
                    stock_move.picked = True
                    picking_to_valiate |= nube_picking

        if picking_to_valiate:
            _logger.info(f"Validar las entregas {','.join(picking_to_valiate.mapped('name'))}")
            picking_to_valiate.button_validate()

    def tiendanube_create_initial_stock_quants_from_order(self, order_response_dict):
        """
        Crea los quants iniciales cuando se importa una orden de venta
        :param order_response_dict:
        :return:
        """
        self.ensure_one()

        if not isinstance(order_response_dict, dict):
            return False

        values_to_create = []
        StockQuant = self.env['stock.quant'].sudo()
        quant_ids = self.env['stock.quant'].sudo()
        for order_line in self.order_line.filtered(
                lambda l: l.product_id.type != 'service' and not l.display_type
        ):
            order_data = order_response_dict[self.x_external_id]
            fulfillments_data = order_data.get("fulfillments")

            # get the fulfillment
            found_fulfillment = {}
            for fulfillment in fulfillments_data:
                if order_line.fulfillmen_external_id == fulfillment.get('id'):
                    found_fulfillment = fulfillment
                    break

            if found_fulfillment:
                items_data = fulfillment.get('line_items')
                for item_data in items_data:
                    sku = item_data.get('sku', '')
                    x_product_id = item_data.get('product', {}).get('product_id')
                    variant_id = item_data.get('variant', {}).get('variant_id')
                    product_id = self._find_matching_product(
                        sku, x_product_id, variant_id, shipping=False
                    )
                    if order_line.product_id == product_id:
                        stock = 0
                        quantity = item_data['quantity']

                        # get warehouse
                        warehouse_id = self.env['sale.order.line']._get_warehouse_from_data(
                            fulfillment.get('assigned_location'))
                        # get the inventory level
                        warehouse_id = self.env['stock.warehouse'].sudo().browse(warehouse_id)
                        vals = {
                            'inventory_quantity': float(quantity),
                            'product_id': product_id.id,
                            'location_id': warehouse_id.lot_stock_id.id,
                        }
                        values_to_create.append(vals)

        if values_to_create:
            quants = StockQuant.with_context(not_execute_quants_base_automation=True).create(values_to_create)
            quant_ids |= quants
        if quant_ids:
            quant_ids.with_context(
                inventory_name=f"Initial import desde Tienda {self.env.company.name}").action_apply_inventory()

    def action_new_version(self, values):
        """
        En TN se puede modificar una orden mientras se encuentre en el estado inicial UNPACKED
        En Odoo las ordenes de TN se crean y se confirman
        Cuando se modifique una orden en TN en Odoo se va a cancelar la orden asociada
        y se va a crear una nueva orden con los nuevos cambios
        :param values: dict con los nuevos valores de la orden nueva
        :return: record
        """
        self.ensure_one()
        if self.state not in ['sale']:
            raise UserError(_("A new version will only be created for a confirmed order."))
        values['origin'] = self.name
        new_order_id = self.copy(values)
        if new_order_id:
            message = _("This order is a new version of the order with folio %s.",
                self._get_html_link())
            new_order_id.message_post(body=message)

            # cancel parent order
            self.new_version_id = new_order_id
            self._action_cancel()
        return new_order_id

    def _find_or_create_payment_method_from_data(self, order_data):
        if not isinstance(order_data, dict):
            return False

        gateway = order_data.get('gateway')
        gateway_id = str(order_data.get('gateway_id')) if order_data.get('gateway_id') else ''
        gateway_name = order_data.get('gateway_name')
        x_store_external_id = self.env.company.external_id

        domain = [('x_store_external_id', '=', x_store_external_id)]
        if gateway_id:
            domain.append(('x_external_id', '=', gateway_id))
        if not gateway or gateway in ['not-provided', 'offline']:
            domain.append(('code', '=', gateway))
            domain.append('|')
            domain.append(('name', '=', gateway_name))
            domain.append(('name', '=', 'No proporcionado'))

        odoo_gateway_id = self.env['payment.method'].sudo().search(domain, limit=1)
        if not odoo_gateway_id:
            if gateway == 'not-provided':
                gateway_name = 'No proporcionado'
            payment_details_ref = order_data.get('payment_details', {}).get('credit_card_company', '')
            vals = {
                'active': True,
                'name': gateway_name + '-' + payment_details_ref.upper() if payment_details_ref else gateway_name,
                'code': gateway,
                'x_external_id': gateway_id,
                "x_state_sync": 'yes',
                "x_date_last_sync": datetime.now(),
                "x_store_external_id": x_store_external_id,
            }
            odoo_gateway_id = self.env['payment.method'].sudo().create(vals)

        return odoo_gateway_id.id

    def _prepare_invoice(self):
        values = super(SaleOrder, self)._prepare_invoice()
        values['payment_method_id'] = self.payment_method_id and self.payment_method_id.id or False
        values['invoice_origin'] += f'-TN#{self.order_number}'

        return values

    def _generate_delivered_invoices(self):
        """ Generate invoices as normal for sale order.

        :return: The generated invoices.
        :rtype: recordset of `account.move`
        """
        generated_invoices = self.env['account.move']

        for order in self:
            delivered_wizard = order.env['sale.advance.payment.inv'].create({
                'sale_order_ids': order,
                'advance_payment_method': 'delivered',
                'fixed_amount': order.amount_paid,
            })
            generated_invoices |= delivered_wizard._create_invoices(order)

        return generated_invoices





