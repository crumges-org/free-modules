# -*- coding: utf-8 -*-
import datetime
import logging

from odoo import models, fields, Command, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Respartner(models.Model):
    _name = 'res.partner'
    _inherit = ['solt.integration.model.mixin', 'connector.sync.mixin', 'res.partner']

    region_id = fields.Many2one('solt.region', 'Region')
    nube_id_default_address = fields.Char("External address ID", translate=True, help="ID externo de la direccion principal")
    x_exclud_from_sync = fields.Boolean("Exclude from sync", default=False, help="Si esta marcado, este registro no se sincronizara con la tienda.")

    def _check_has_billing_info(self, billing_fields, data):
        return any(bool(data.get(bfield)) is True for bfield in billing_fields)

    def prepare_contact_lines(self, data, billing_address=False):
        if not isinstance(data, dict):
            return data
        commands = []
        Partner = self.env['res.partner'].sudo()

        # campos de la direccion de facturacion
        billing_fields = [field for field in data.keys() if field.startswith('billing_')]
        # check los datos de la direcciones
        if 'addresses' not in data and not self._check_has_billing_info(billing_fields, data):
            return commands
        id_default_address = data.get('default_address', {}).get('id', '')

        # prepare shipping contacts lines
        addresses_list = data.pop('addresses', False)
        # si billing_address es false, revisa las dir. de fact y entrega
        if addresses_list and not billing_address:
            for address_dict in addresses_list:
                if address_dict['id'] == id_default_address:
                    continue
                country_id = self._get_country_from_api(address_dict)
                state_id = self._get_state_from_api(address_dict)
                country = self.env['res.country'].browse(country_id)

                if country.enforce_cities:
                    city_id = self._get_city_from_api(address_dict)
                    city = self.env['res.city'].browse(city_id).name
                else:
                    city_id = False
                    city = address_dict.get('city', '')

                if country.enforce_localities:
                    locality_id = self._get_locality_from_api(address_dict)
                    l10n_mx_locality = self.env['res.locality'].browse(locality_id)
                    l10n_mx_locality = l10n_mx_locality.name
                else:
                    locality_id = False
                    l10n_mx_locality = address_dict.get('locality', '')
                values = {
                    'type': 'delivery',
                    'name': self.convert_translated_field_to_odoo_format(address_dict.get('name')) if address_dict.get('name', False) else address_dict.get('address'),
                    'email': address_dict.get('email', ''),
                    'phone': address_dict.get('phone', ''),
                    'street_name': address_dict.get('address', ''),
                    'zip': address_dict.get('zipcode', ''),
                    'city_id': city_id,
                    'city': city,
                    'state_id': state_id,
                    'country_id': country_id,
                    'l10n_mx_locality_id': locality_id,
                    'l10n_mx_locality': l10n_mx_locality,
                    'street_number': address_dict.get('floor', ''),
                    'street_number2': address_dict.get('number', ''),
                }
                # Check if a contact exists
                existing_address = False
                name = address_dict.get('name', '') or address_dict.get('address', '')
                if address_dict.get('id'):
                    existing_address = Partner.with_company(self.env.company).search([
                        ('x_external_id', '=', address_dict.get('id')), ('type', '=', 'delivery')], limit=1)
                if not existing_address:
                    existing_address = Partner.with_company(self.env.company).search([
                        ('type', '=', 'delivery'), ('parent_id', '=', self.id), '|', ('name', '=', name), ('street_name', '=', name)], limit=1)
                sync_vals = {
                    'x_external_id': address_dict.get('id'),
                    "x_exclud_from_sync": False,
                    'x_state_sync': 'yes',
                    'x_date_last_sync': datetime.datetime.now(),
                    'x_store_external_id': self.env.company.external_id,
                    'company_id': self.env.company.id
                }
                if existing_address:
                    commands.append(Command.update(existing_address.id, sync_vals))
                else:
                    values = {**values, **sync_vals}
                    commands.append(Command.create(values))
        if self._check_has_billing_info(billing_fields, data):
            country_id = self._get_country_from_api(data, type='invoice')
            state_id = self._get_state_from_api(data, type='invoice')
            country = self.env['res.country'].browse(country_id)

            if country.enforce_cities:
                city_id = self._get_city_from_api(data, type='invoice')
                city = self.env['res.city'].browse(city_id).name
            else:
                city_id = False
                city = data.get('billing_city', '')

            if country.enforce_localities:
                locality_id = self._get_locality_from_api(data, type='invoice')
                l10n_mx_locality = self.env['res.locality'].browse(locality_id)
                l10n_mx_locality = l10n_mx_locality.name
            else:
                locality_id = False
                l10n_mx_locality = data.get('billing_locality', '')
            name = self.convert_translated_field_to_odoo_format(data.get('billing_name')) if data.get(
                'billing_name', False) else data.get('billing_address')
            default_street_name = data.get('billing_address', '')
            default_street_number = data.get('billing_floor', '')
            default_street_number2 = data.get('billing_number', '')
            default_zip = data.get('billing_zipcode', '')
            bvalues = {
                'type': 'invoice',
                'name': name,
                'phone': data.get('billing_phone', ''),
                'street_name': default_street_name,
                'zip': default_zip,
                'city_id': city_id,
                'city': city,
                'state_id': state_id,
                'country_id': country_id,
                'l10n_mx_locality_id': locality_id,
                'l10n_mx_locality': l10n_mx_locality,
                'street_number': default_street_number,
                'street_number2': default_street_number2,
            }

            # Check if a billing address exists for this partner
            existing_billing = False
            bname = data.get('billing_name', '')
            if bname in ['No informado', '', None, False]:
                bname = ''
            if self:
                existing_billing = self.env['res.partner'].search([
                    *self.env['res.partner']._check_company_domain(self.env.company),
                    ('parent_id', '=', self.id),
                    ('type', '=', 'invoice'),
                    ('name', '=', bname),
                    ('street_name', '=', default_street_name),
                    ('street_number', '=', default_street_number),
                    ('street_number2', '=', default_street_number2),
                    ('zip', '=', default_zip),
                    ('city', '=', city),
                    ('l10n_mx_locality', '=', l10n_mx_locality),
                    ('country_id', '=', country_id),
                    ('state_id', '=', state_id),
                ], limit=1)
                # existing_billing = Partner.with_company(self.env.company).search([
                #     ('parent_id', '=', self.id),
                #     ('type', '=', 'invoice'),
                #     ('x_state_sync', 'in', ['yes', 'no', 'error']),
                # ], limit=1)
                # if not existing_billing:
                #     existing_billing = Partner.with_company(self.env.company).search([
                #         ('parent_id', '=', self.id),
                #         ('type', '=', 'invoice'),
                #         '|',
                #         ('name', '=', bname),
                #         ('street_name', '=', bname)
                #     ], limit=1)
            sync_vals = {
                "x_exclud_from_sync": False,
                'x_state_sync': 'yes',
                'x_date_last_sync': datetime.datetime.now(),
                'x_store_external_id': self.env.company.external_id,
                'company_id': self.env.company.id
            }
            if existing_billing:
                commands.append(Command.update(existing_billing.id, sync_vals))
            else:
                bvalues.update(sync_vals)
                commands.append(Command.create(bvalues))
        return commands

    def _prepare_address_values(self, field_name=None, type='delivery', action='create'):
        self.ensure_one()
        values = {}
        if self.country_id.enforce_cities:
            city = self.city_id and self.city_id.name
        else:
            city = self.city
        if self.country_id.enforce_localities:
            locality = self.self.l10n_mx_locality_id and self.l10n_mx_locality_id.name
        else:
            locality = self.l10n_mx_locality
        if type == 'delivery':
            values = {
                "name": self.name or "",
                "address": self.street_name or "",
                "city": city or "",
                "country": self.country_code or "",
                "province": self.state_id and self.state_id.name or "",
                "locality": locality or "",
                "zipcode": self.zip or "",
                "floor": self.street_number,
                "number": self.street_number2,
                "phone": self.phone or "",
            }
        elif type == 'invoice':
            values = {
                "billing_name": self.name or "",
                "billing_address": self.street_name or "",
                "billing_city": city or "",
                "billing_country": self.country_code or "",
                "billing_province": self.state_id and self.state_id.name or "",
                "billing_locality": locality or "",
                "billing_zipcode": self.zip or "",
                "billing_floor": self.street_number,
                "billing_number": self.street_number2,
                "billing_phone": self.phone or "",
            }
        if action == 'update':
            values['id'] = self.x_external_id

        if field_name is not None:
            return values.get(field_name)

        return values

    def prepare_shipping_address_api(self, field_value, default=False, action='create'):
        """
        Preparar las direcciones principal y de entregas
        :param field_value:
        :return: lista de direcciones
        """
        self.ensure_one()
        addresses = []
        child_ids = None
        if isinstance(field_value, list) and field_value:
            child_ids = self.env['res.partner'].browse(field_value)
        if not child_ids and not isinstance(field_value, list) or isinstance(field_value, models.BaseModel) and len(field_value) == 0:
            child_ids = self.child_ids
        if not child_ids and not default:
            return addresses

        # preparar la primera direccion
        values = self._prepare_address_values()
        if default:
            if 'id' in values:
                id = values.pop('id')
            addresses = values
        else:
            # prepare the other address
            # addresses.append(values)
            for address in child_ids.filtered(lambda p: p.type == 'delivery' and not p.x_exclud_from_sync):
                values = address._prepare_address_values(action=action)
                addresses.append(values)

        return addresses

    def _get_billing_address_field_for_api(self, field_value, field):
        self.ensure_one()
        child_ids = None
        value = False
        if isinstance(field_value, list) and field_value:
            child_ids = self.env['res.partner'].browse(field_value)
        if not child_ids and not isinstance(field_value, list) or isinstance(field_value, models.BaseModel) and len(
                field_value) == 0:
            child_ids = self.child_ids

        if not child_ids:
            return value
        invoice_child = child_ids.filtered(lambda p: p.type == 'invoice')
        if invoice_child:
            values = invoice_child[0]._prepare_address_values(type='invoice')
            value = values.get(field, False)
        return value

    def _get_country_from_api(self, data, type='delivery'):
        Country = self.env['res.country'].sudo()
        if not isinstance(data, dict) and not isinstance(data, str):
            return False
        if isinstance(data, dict) and type == 'contact':
            code = data.get('code', '')
            name = data.get('name', 'name')

        if isinstance(data, dict) and type == 'delivery':
            code = data.get('country', '')
            name = data.get('country', '')

        if isinstance(data, dict) and type == 'invoice':
            code = data.get('billing_country', '')
            name = data.get('billing_country', '')

        country_id = Country.search(['|', ('name', '=ilike', name), ('code', '=ilike', code)], limit=1)
        if not country_id and name and code:
            country_id = Country.with_context(tracking_disable=True).create({
                'name': name,
                'code': code
            })

        return country_id and country_id.id or False

    def _get_state_from_api(self, data, type='delivery'):
        State = self.env['res.country.state'].sudo()
        if not isinstance(data, dict) and not isinstance(data, str):
            return False
        if isinstance(data, dict) and type == 'contact':
            code = data.get('code', '')
            name = data.get('name', 'name')

        if isinstance(data, dict) and type == 'delivery':
            code = data.get('province', '')
            name = data.get('province', '')

        if isinstance(data, dict) and type == 'invoice':
            code = data.get('billing_province', '')
            name = data.get('billing_province', '')

        country_id = self._get_country_from_api(data, type=type)
        if not country_id or not name:
            return False

        state_id = State.search([('country_id', '=', country_id), '|', ('name', '=ilike', name), ('code', '=ilike', code)], limit=1)
        if not state_id:
            state_id = State.with_context(tracking_disable=True).create({
                'name': name,
                'code': code,
                'country_id': country_id
            })

        return state_id.id

    def _get_city_from_api(self, data, type='delivery'):
        City = self.env['res.city'].sudo()
        if not isinstance(data, dict):
            return False
        if type in ['delivery', 'contact']:
            name = data.get('city', '')

        if type == 'invoice':
            name = data.get('billing_city', '')

        country = self._get_country_from_api(data, type=type)
        if not country or not name:
            return False
        state = self._get_state_from_api(data, type=type)

        city_id = City.search([
            ('country_id', '=', country), ('state_id', 'in', [state, False]), ('name', '=ilike', name)
        ], limit=1)
        if not city_id:
            city_id = City.with_context(tracking_disable=True).create({
                'name': name,
                'country_id': country,
                'state_id': state
            })

        return city_id.id

    def _get_locality_from_api(self, data, type='delivery'):
        Locality = self.env['res.locality'].sudo()
        if not isinstance(data, dict):
            return False
        if type in ['delivery', 'contact']:
            name = data.get('locality', '')

        if type == 'invoice':
            name = data.get('billing_locality', '')

        country = self._get_country_from_api(data, type=type)
        state = self._get_state_from_api(data, type=type)
        if not name or not country or not state:
            return False

        locality_id = Locality.search([
            ('country_id', '=', country), ('state_id', '=', state), ('name', '=ilike', name)
        ], limit=1)
        if not locality_id:
            locality_id = Locality.with_context(tracking_disable=True).create({
                'name': name,
                'country_id': country,
                'state_id': state
            })
        return locality_id.id

    def _check_partner_addresses(self):
        """
        Valida si el partner tiene una sola direccion de facturacion/entrega
        :return:
        """
        self.ensure_one()
        if self.child_ids:
            invoice_childs = self.child_ids.filtered(lambda p: p.type == 'invoice')
            if len(invoice_childs) > 1:
                raise UserError(_(f"Customer {self.name} no puede tener more than una billing address."))
            if self.parent_id and self.type in ['invoice', 'delivery']:
                raise UserError(_(f"Address de facturacion/entrega {self.name}, no puede tener direcciones hijas."))

    def unlink(self):
        childs = self.child_ids
        res = super(Respartner, self).unlink()
        if childs:
            childs.write({'x_exclud_from_sync': True})
            childs.unlink()
        return res

    def _find_or_create_partners_from_data(self, data, shipping_address=None):
        """ Find or create the contact and delivery partners based on the provided data.

        :param dict data: The customer data to find or create the partners from.
        :return: The contact, delivery and invoice partners, as `res.partner` records. When the contact
                 partner acts as delivery and invoice partner, the records are the same.
        :rtype: tuple[record of `res.partner`, record of `res.partner`, record of `res.partner`]
        """
        if not isinstance(data, dict):
            return data

        # contact info
        name = data.get('name')
        email = data.get('email', '')
        vat = data.get('identification', '')
        phone = data.get('phone', '')
        x_external_id = data.get('id', '')
        note = data.get('note', '')

        # default address
        if 'default_address' in data:  # customer data
            default_shipping_address_info = data.get('default_address', {})
        else:  # shipping address
            default_shipping_address_info = data

        default_name = default_shipping_address_info.get('name', '') or name  # if not name we use the name of contact
        default_phone = default_shipping_address_info.get('phone', '') or ''
        default_street_name = default_shipping_address_info.get('address', '') or ''
        default_zip = default_shipping_address_info.get('zipcode', '') or ''
        default_street_number = default_shipping_address_info.get('floor', '') or ''
        default_street_number2 = default_shipping_address_info.get('number', '') or ''

        country_id = self._get_country_from_api(default_shipping_address_info)
        state_id = self._get_state_from_api(default_shipping_address_info)
        country = self.env['res.country'].browse(country_id)
        if country.enforce_cities:
            city_id = self._get_city_from_api(default_shipping_address_info)
            city = self.env['res.city'].browse(city_id).name
        else:
            city_id = False
            city = default_shipping_address_info.get('city', '')

        if country.enforce_localities:
            locality_id = self._get_locality_from_api(default_shipping_address_info)
            l10n_mx_locality = self.env['res.locality'].browse(locality_id)
            l10n_mx_locality = l10n_mx_locality.name
        else:
            locality_id = False
            l10n_mx_locality = default_shipping_address_info.get('locality', '')

        default_city_id = city_id
        default_city = city
        default_state_id = state_id
        default_country_id = country_id
        default_l10n_mx_locality_id = locality_id
        default_l10n_mx_locality = l10n_mx_locality

        partner_vals = {
            'name': default_name,
            'phone': phone or default_phone,
            'street_name': default_street_name,
            'zip': default_zip,
            'city_id': default_city_id,
            'city': default_city,
            'state_id': default_state_id,
            'country_id': default_country_id,
            'l10n_mx_locality_id': default_l10n_mx_locality_id,
            'l10n_mx_locality': default_l10n_mx_locality,
            'street_number': default_street_number,
            'street_number2': default_street_number2,
            'customer_rank': 1,
        }
        sync_vals = {
            "x_exclud_from_sync": False,
            'x_state_sync': 'yes',
            'x_date_last_sync': datetime.datetime.now(),
            'x_store_external_id': self.env.company.external_id,
            'company_id': self.env.company.id
        }

        # The contact partner is searched based on all the personal information and only if the
        # email is provided. A match thus only occurs if the customer had already made a
        # previous order and if the personal information provided by the API did not change in the
        # meantime. If there is no match, a new contact partner is created. This behavior is
        # preferred over updating the personal information with new values because it allows using
        # the correct contact details when invoicing the customer for an earlier order, should there
        # be a change in the personal information.
        contact = self.env['res.partner'].search([
            *self.env['res.partner']._check_company_domain(self.env.company),
            ('type', '=', 'contact'),
            ('name', '=', name),
            ('email', '=', email),
        ], limit=1) if email and name else None  # Don't match random partners.
        if not contact:
            partner_vals['name'] = name
            partner_vals['email'] = email
            partner_vals['phone'] = phone
            partner_vals['comment'] = note
            contact = self.env['res.partner'].with_context(tracking_disable=True, not_execute_base_automation=True).create({
                'x_external_id': x_external_id,
                "vat": vat,
                **partner_vals, **sync_vals
            })
        else:
            contact.with_context(not_execute_base_automation=True).write({
                "phone": phone,
                "vat": vat,
                "comment": note,
                **sync_vals
            })

        # The contact partner acts as delivery partner if the address is strictly equal to that of
        # the contact partner. If not, a delivery partner is created.
        delivery = contact if (
                contact.name == default_name
                and contact.street_name == default_street_name
                and contact.street_number == default_street_number
                and contact.street_number2 == default_street_number2
                and contact.zip == default_zip
                and contact.city == default_city
                and contact.l10n_mx_locality == default_l10n_mx_locality
                and contact.country_id.id == default_country_id
                and contact.state_id.id == default_state_id
        ) else None
        if not delivery:
            delivery = self.env['res.partner'].search([
                *self.env['res.partner']._check_company_domain(self.env.company),
                ('parent_id', '=', contact.id),
                ('type', '=', 'delivery'),
                ('name', '=', default_name),
                ('street_name', '=', default_street_name),
                ('street_number', '=', default_street_number),
                ('street_number2', '=', default_street_number2),
                ('zip', '=', default_zip),
                ('city', '=', default_city),
                ('l10n_mx_locality', '=', default_l10n_mx_locality),
                ('country_id', '=', default_country_id),
                ('state_id', '=', default_state_id),
            ], limit=1)
        default_street2 = ''
        default_ref = ''
        if shipping_address and "customs" in shipping_address:
            customs = shipping_address.get('customs')
            default_ref = customs.get('reference', '')
            default_street2 = customs.get('between_streets', '')
            partner_vals.update({
                'street2': ','.join([default_ref, default_street2]),
                # 'ref': default_ref,
            })
        if not delivery:
            delivery = self.env['res.partner'].with_context(tracking_disable=True, not_execute_base_automation=True).create({
                'type': 'delivery',
                'parent_id': contact.id,
                **partner_vals, **sync_vals
            })
        else:
            delivery.with_context(not_execute_base_automation=True).write({
                'street2': ','.join([default_ref, default_street2]),
                # 'ref': default_ref,
                **sync_vals
            })

        # The contact partner acts as invoice partner if the address is strictly equal to that of
        # the contact partner. If not, a invoice partner is created.
        invoice = self.env['res.partner']
        if 'billing_name' in data and data.get('billing_name', '') not in ['No informado', '', None, False]:
            country_id = self._get_country_from_api(data, type='invoice')
            state_id = self._get_state_from_api(data, type='invoice')
            country = self.env['res.country'].browse(country_id)

            if country.enforce_cities:
                city_id = self._get_city_from_api(data, type='invoice')
                city = self.env['res.city'].browse(city_id).name
            else:
                city_id = False
                city = data.get('city', '')

            if country.enforce_localities:
                locality_id = self._get_locality_from_api(data, type='invoice')
                l10n_mx_locality = self.env['res.locality'].browse(locality_id)
                l10n_mx_locality = l10n_mx_locality.name
            else:
                locality_id = False
                l10n_mx_locality = data.get('billing_locality', '')
            default_name = data.get('billing_name') or ''
            default_phone = data.get('billing_phone', '') or ''
            default_street_name = data.get('billing_address', '') or ''
            default_zip = data.get('billing_zipcode', '') or ''
            default_street_number = data.get('billing_floor', '') or ''
            default_street_number2 = data.get('billing_number', '') or ''
            default_city_id = city_id
            default_city = city
            default_state_id = state_id
            default_country_id = country_id
            default_l10n_mx_locality_id = locality_id
            default_l10n_mx_locality = l10n_mx_locality
            partner_vals = {
                'name': default_name,
                'phone': default_phone,
                'street_name': default_street_name,
                'zip': default_zip,
                'city_id': default_city_id,
                'city': default_city,
                'state_id': default_state_id,
                'country_id': default_country_id,
                'l10n_mx_locality_id': default_l10n_mx_locality_id,
                'l10n_mx_locality': default_l10n_mx_locality,
                'street_number': default_street_number,
                'street_number2': default_street_number2,
                'customer_rank': 1,
            }
            invoice = contact if (
                    (contact.name == default_name or default_name in contact.name.split(' '))
                    and contact.street_name == default_street_name
                    and contact.street_number == default_street_number
                    and contact.street_number2 == default_street_number2
                    and contact.zip == default_zip
                    and contact.city == default_city
                    and contact.l10n_mx_locality == default_l10n_mx_locality
                    and contact.country_id.id == default_country_id
                    and contact.state_id.id == default_state_id
            ) else None
            if not invoice:
                invoice = self.env['res.partner'].search([
                    *self.env['res.partner']._check_company_domain(self.env.company),
                    ('parent_id', '=', contact.id),
                    ('type', '=', 'invoice'),
                    ('name', '=', default_name),
                    ('street_name', '=', default_street_name),
                    ('street_number', '=', default_street_number),
                    ('street_number2', '=', default_street_number2),
                    ('zip', '=', default_zip),
                    ('city', '=', default_city),
                    ('l10n_mx_locality', '=', default_l10n_mx_locality),
                    ('country_id', '=', default_country_id),
                    ('state_id', '=', default_state_id),
                ], limit=1)
            if not invoice:
                invoice = self.env['res.partner'].with_context(tracking_disable=True, not_execute_base_automation=True).create({
                    'type': 'invoice',
                    'parent_id': contact.id,
                    **partner_vals, **sync_vals
                })
            else:
                invoice.with_context(not_execute_base_automation=True).write({**sync_vals})

        return contact, delivery, invoice
