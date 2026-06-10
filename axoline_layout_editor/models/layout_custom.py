# Part of Axoline Layout Editor. See LICENSE file for full copyright and licensing details.

import json
import uuid

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

DEFAULT_LAYOUT = {
    'version': 1,
    'blocks': [],
}

MODEL_FIELD_MAP = {
    'account.move': {
        'partner': 'partner_id',
        'partner_shipping': 'partner_shipping_id',
        'date': 'invoice_date',
        'number': 'name',
        'reference': 'ref',
        'salesperson': 'invoice_user_id',
        'lines': 'invoice_line_ids',
        'line_product': 'product_id',
        'line_name': 'name',
        'line_quantity': 'quantity',
        'line_uom': 'product_uom_id',
        'line_price_unit': 'price_unit',
        'line_discount': 'discount',
        'line_taxes': 'tax_ids',
        'line_subtotal': 'price_subtotal',
        'amount_untaxed': 'amount_untaxed',
        'amount_tax': 'amount_tax',
        'amount_total': 'amount_total',
        'amount_residual': 'amount_residual',
        'currency': 'currency_id',
        'payment_term': 'invoice_payment_term_id',
        'notes': 'narration',
        'payment_reference': 'payment_reference',
        'payment_method': 'preferred_payment_method_line_id',
        'fiscal_position': 'fiscal_position_id',
        'tax_totals': 'tax_totals',
    },
    'sale.order': {
        'partner': 'partner_id',
        'partner_shipping': 'partner_shipping_id',
        'date': 'date_order',
        'number': 'name',
        'reference': 'client_order_ref',
        'salesperson': 'user_id',
        'lines': 'order_line',
        'line_product': 'product_id',
        'line_name': 'name',
        'line_quantity': 'product_uom_qty',
        'line_uom': 'product_uom_id',
        'line_price_unit': 'price_unit',
        'line_discount': 'discount',
        'line_taxes': 'tax_id',
        'line_subtotal': 'price_subtotal',
        'amount_untaxed': 'amount_untaxed',
        'amount_tax': 'amount_tax',
        'amount_total': 'amount_total',
        'currency': 'currency_id',
        'payment_term': 'payment_term_id',
        'notes': 'note',
        'payment_method': 'preferred_payment_method_line_id',
        'validity_date': 'validity_date',
        'tax_totals': 'tax_totals',
    },
    'purchase.order': {
        'partner': 'partner_id',
        'date': 'date_order',
        'number': 'name',
        'reference': 'partner_ref',
        'salesperson': 'user_id',
        'lines': 'order_line',
        'line_product': 'product_id',
        'line_name': 'name',
        'line_quantity': 'product_qty',
        'line_uom': 'product_uom_id',
        'line_price_unit': 'price_unit',
        'line_taxes': 'taxes_id',
        'line_subtotal': 'price_subtotal',
        'amount_untaxed': 'amount_untaxed',
        'amount_tax': 'amount_tax',
        'amount_total': 'amount_total',
        'currency': 'currency_id',
        'payment_term': 'payment_term_id',
        'notes': 'notes',
        'tax_totals': 'tax_totals',
    },
    'stock.picking': {
        'partner': 'partner_id',
        'date': 'scheduled_date',
        'number': 'name',
        'reference': 'origin',
        'lines': 'move_ids',
        'line_product': 'product_id',
        'line_name': 'description_picking',
        'line_quantity': 'quantity',
        'line_uom': 'product_uom',
    },
}

BLOCK_TYPES = [
    {'type': 'company_header', 'label': 'Company Header', 'icon': 'fa-building-o', 'category': 'header'},
    {'type': 'sender_line', 'label': 'Sender Line', 'icon': 'fa-ellipsis-h', 'category': 'header'},
    {'type': 'company_details', 'label': 'Company Details', 'icon': 'fa-id-card-o', 'category': 'header'},
    {'type': 'document_title', 'label': 'Document Title', 'icon': 'fa-header', 'category': 'header'},
    {'type': 'partner_address', 'label': 'Recipient Address', 'icon': 'fa-address-card-o', 'category': 'header'},
    {'type': 'intro_text', 'label': 'Introduction Text', 'icon': 'fa-comment-o', 'category': 'content'},
    {'type': 'info_table', 'label': 'Info Table', 'icon': 'fa-info-circle', 'category': 'content'},
    {'type': 'line_items', 'label': 'Line Items', 'icon': 'fa-table', 'category': 'content'},
    {'type': 'subtotals', 'label': 'Totals / Taxes', 'icon': 'fa-calculator', 'category': 'content'},
    {'type': 'notes', 'label': 'Payment & Shipping Info', 'icon': 'fa-sticky-note-o', 'category': 'content'},
    {'type': 'free_text', 'label': 'Free Text', 'icon': 'fa-font', 'category': 'content'},
    {'type': 'footer', 'label': 'Footer', 'icon': 'fa-window-minimize', 'category': 'footer'},
    {'type': 'two_columns', 'label': 'Two Columns', 'icon': 'fa-columns', 'category': 'layout'},
    {'type': 'separator', 'label': 'Separator', 'icon': 'fa-minus', 'category': 'layout'},
    {'type': 'spacer', 'label': 'Spacer', 'icon': 'fa-arrows-v', 'category': 'layout'},
    {'type': 'page_break', 'label': 'Page Break', 'icon': 'fa-file-o', 'category': 'layout'},
]

BLOCK_DEFAULTS = {
    'company_header': {
        'show_logo': True,
        'show_company_name': True,
        'show_company_address': True,
        'logo_position': 'left',
    },
    'sender_line': {
        'separator': ' · ',
        'font_size': '8',
        'show_name': True,
        'show_street': True,
        'show_city': True,
        'show_phone': False,
        'show_email': False,
    },
    'company_details': {
        'font_size': '9',
        'show_name': True,
        'show_address': True,
        'show_phone': True,
        'show_fax': False,
        'show_email': True,
        'show_website': True,
        'show_vat': True,
        'show_company_registry': False,
        'show_bank': True,
    },
    'document_title': {
        'font_size': '20',
        'bold': True,
        'alignment': 'left',
    },
    'partner_address': {
        'use_shipping': False,
        'show_vat': True,
        'font_size': '10',
    },
    'info_table': {
        'show_date': True,
        'show_number': True,
        'show_reference': True,
        'show_payment_term': True,
        'columns': 2,
    },
    'line_items': {
        'show_product': True,
        'show_description': True,
        'show_quantity': True,
        'show_uom': True,
        'show_price_unit': True,
        'show_discount': True,
        'show_taxes': False,
        'show_subtotal': True,
    },
    'subtotals': {
        'show_tax_details': True,
        'alignment': 'right',
    },
    'notes': {
        'show_payment_terms': True,
        'show_notes': True,
    },
    'free_text': {
        'content': '',
        'alignment': 'left',
        'font_size': '12',
    },
    'two_columns': {
        'left_ratio': 50,
        'left_blocks': [],
        'right_blocks': [],
    },
    'separator': {
        'style': 'solid',
        'color': '#000000',
        'margin': '10',
    },
    'spacer': {
        'height': '20',
    },
    'page_break': {},
}


class AxolineLayoutCustom(models.Model):
    _name = 'axoline.layout.custom'
    _description = 'Axoline PDF Layout (Editor Data)'
    _order = 'report_name, id'

    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(related='report_id.name', readonly=True)
    report_name = fields.Char(
        related='report_id.report_name',
        store=True,
        readonly=True,
    )
    model_name = fields.Char(
        related='report_id.model',
        string='Model',
        store=True,
        readonly=True,
    )
    layout_json = fields.Text(
        string='Layout (JSON)',
        default=lambda self: json.dumps(DEFAULT_LAYOUT),
    )
    notes = fields.Text(string='Internal Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_report', 'unique (report_id)',
         'Only one layout record per report is allowed.'),
    ]

    @api.constrains('layout_json')
    def _check_layout_json(self):
        for rec in self:
            if not (rec.layout_json or '').strip():
                continue
            try:
                json.loads(rec.layout_json)
            except json.JSONDecodeError as e:
                raise ValidationError(_('Layout (JSON) is invalid: %s') % e) from e

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    def get_field_map(self):
        """Return the field mapping dict for the report's model."""
        return MODEL_FIELD_MAP.get(self.model_name, {})

    def get_blocks(self):
        """Return parsed block list from layout_json."""
        try:
            data = json.loads(self.layout_json or '{}')
        except json.JSONDecodeError:
            data = {}
        return data.get('blocks', [])

    @api.model
    def get_block_types(self):
        return BLOCK_TYPES

    @api.model
    def get_block_defaults(self):
        return BLOCK_DEFAULTS

    # ------------------------------------------------------------------
    #  Report rendering helpers
    # ------------------------------------------------------------------

    def _safe_getattr(self, obj, field_name, default=''):
        """Safely get a field value, return default if missing."""
        try:
            val = getattr(obj, field_name, default)
            if hasattr(val, 'display_name'):
                return val.display_name or ''
            return val
        except Exception:
            return default

    def _get_doc_value(self, doc, key):
        fmap = self.get_field_map()
        field_name = fmap.get(key)
        if not field_name:
            return ''
        return self._safe_getattr(doc, field_name, '')

    def _get_doc_lines(self, doc):
        fmap = self.get_field_map()
        lines_field = fmap.get('lines')
        if not lines_field:
            return []
        return getattr(doc, lines_field, [])

    def _render_block_html(self, block, doc, company):
        """Render a single block to HTML Markup for the QWeb template."""
        btype = block.get('type', '')
        settings = block.get('settings', {})
        method = getattr(self, '_render_block_%s' % btype, None)
        if method:
            return method(settings, doc, company)
        return Markup('')

    # ----- Individual block renderers -----

    def _render_block_company_header(self, s, doc, company):
        # Uses display:table instead of flexbox for wkhtmltopdf compatibility
        parts = []
        logo_pos = s.get('logo_position', 'left')
        lh = s.get('line_height', '1.4')

        if logo_pos == 'top':
            parts.append('<div class="axo-block axo-company-header" style="line-height:%s;margin-bottom:12px;">' % lh)
            if s.get('show_logo', True) and company.logo:
                parts.append(
                    '<div style="margin-bottom:8px;">'
                    '<img src="/logo.png?company=%d" style="max-height:80px;max-width:200px;" alt="Logo"/>'
                    '</div>' % company.id
                )
            if s.get('show_company_name', True):
                parts.append('<strong style="font-size:16px;">%s</strong><br/>' % (company.name or ''))
            if s.get('show_company_address', True):
                addr = self._format_company_address(company)
                parts.append('<span style="font-size:10px;">%s</span>' % addr)
            parts.append('</div>')
        else:
            parts.append('<div class="axo-block axo-company-header" style="display:table;width:100%%;line-height:%s;margin-bottom:12px;">' % lh)
            if logo_pos == 'right':
                parts.append('<div style="display:table-cell;vertical-align:top;">')
                if s.get('show_company_name', True):
                    parts.append('<strong style="font-size:16px;">%s</strong><br/>' % (company.name or ''))
                if s.get('show_company_address', True):
                    addr = self._format_company_address(company)
                    parts.append('<span style="font-size:10px;">%s</span>' % addr)
                parts.append('</div>')
                if s.get('show_logo', True) and company.logo:
                    parts.append(
                        '<div style="display:table-cell;vertical-align:top;text-align:right;width:220px;">'
                        '<img src="/logo.png?company=%d" style="max-height:80px;max-width:200px;" alt="Logo"/>'
                        '</div>' % company.id
                    )
            else:
                if s.get('show_logo', True) and company.logo:
                    parts.append(
                        '<div style="display:table-cell;vertical-align:top;width:220px;padding-right:16px;">'
                        '<img src="/logo.png?company=%d" style="max-height:80px;max-width:200px;" alt="Logo"/>'
                        '</div>' % company.id
                    )
                parts.append('<div style="display:table-cell;vertical-align:top;">')
                if s.get('show_company_name', True):
                    parts.append('<strong style="font-size:16px;">%s</strong><br/>' % (company.name or ''))
                if s.get('show_company_address', True):
                    addr = self._format_company_address(company)
                    parts.append('<span style="font-size:10px;">%s</span>' % addr)
                parts.append('</div>')
            parts.append('</div>')

        return Markup(''.join(parts))

    def _format_company_address(self, company):
        lines = []
        if company.street:
            lines.append(company.street)
        if company.street2:
            lines.append(company.street2)
        city_line = ' '.join(filter(None, [company.zip, company.city]))
        if city_line:
            lines.append(city_line)
        if company.country_id:
            lines.append(company.country_id.name)
        if company.phone:
            lines.append('%s: %s' % (_('Phone'), company.phone))
        if company.email:
            lines.append(company.email)
        if company.vat:
            lines.append('%s: %s' % (_('VAT ID'), company.vat))
        return '<br/>'.join(lines)

    def _render_block_sender_line(self, s, doc, company):
        sep = s.get('separator', ' · ')
        size = s.get('font_size', '8')
        parts = []
        if s.get('show_name', True) and company.name:
            parts.append(company.name)
        if s.get('show_street', True) and company.street:
            parts.append(company.street)
        if s.get('show_city', True):
            city = ' '.join(filter(None, [company.zip, company.city]))
            if city:
                parts.append(city)
        if s.get('show_phone') and company.phone:
            parts.append('%s: %s' % (_('Phone'), company.phone))
        if s.get('show_email') and company.email:
            parts.append(company.email)
        if not parts:
            return Markup('')
        text = sep.join(parts)
        return Markup(
            '<div class="axo-block" style="margin-bottom:8px;">'
            '<span class="axo-sender-line" '
            'style="font-size:%spx;color:#666;border-bottom:1px solid #ccc;'
            'padding-bottom:2px;">%s</span></div>' % (size, text)
        )

    def _render_block_company_details(self, s, doc, company):
        size = s.get('font_size', '9')
        lines = []
        if s.get('show_name', True) and company.name:
            lines.append('<strong>%s</strong>' % company.name)
        if s.get('show_address', True):
            addr_parts = []
            if company.street:
                addr_parts.append(company.street)
            if company.street2:
                addr_parts.append(company.street2)
            city = ' '.join(filter(None, [company.zip, company.city]))
            if city:
                addr_parts.append(city)
            if company.country_id:
                addr_parts.append(company.country_id.name)
            if addr_parts:
                lines.extend(addr_parts)
        if s.get('show_phone', True) and company.phone:
            lines.append('%s: %s' % (_('Phone'), company.phone))
        if s.get('show_fax') and getattr(company, 'fax', None):
            lines.append('%s: %s' % (_('Fax'), company.fax))
        if s.get('show_email', True) and company.email:
            lines.append(company.email)
        if s.get('show_website', True) and company.website:
            lines.append(company.website)
        if s.get('show_vat', True) and company.vat:
            lines.append('%s: %s' % (_('VAT ID'), company.vat))
        if s.get('show_company_registry') and company.company_registry:
            lines.append('%s: %s' % (_('Reg. No.'), company.company_registry))
        if s.get('show_bank', True):
            banks = self.env['res.partner.bank'].sudo().search(
                [('company_id', '=', company.id)], limit=1,
            )
            if banks:
                bank = banks[0]
                bank_line = 'IBAN: %s' % (bank.acc_number or '')
                if bank.bank_id and bank.bank_id.bic:
                    bank_line += ' · BIC: %s' % bank.bank_id.bic
                lines.append(bank_line)
        if not lines:
            return Markup('')
        html = '<br/>'.join(lines)
        lh = s.get('line_height', '1.4')
        return Markup(
            '<div class="axo-block axo-company-details" '
            'style="font-size:%spx;line-height:%s;margin-bottom:12px;">%s</div>'
            % (size, lh, html)
        )

    def _get_document_type_label(self, doc):
        model = doc._name if hasattr(doc, '_name') else ''
        if model == 'sale.order':
            state = getattr(doc, 'state', '')
            return _('Sales Order') if state in ('sale', 'done') else _('Quotation')
        if model == 'account.move':
            move_type = getattr(doc, 'move_type', '')
            return {
                'out_invoice': _('Invoice'),
                'out_refund': _('Credit Note'),
                'in_invoice': _('Vendor Bill'),
                'in_refund': _('Vendor Credit Note'),
            }.get(move_type, _('Invoice'))
        if model == 'purchase.order':
            state = getattr(doc, 'state', '')
            return _('Purchase Order') if state in ('purchase', 'done') else _('Request for Quotation')
        if model == 'stock.picking':
            return _('Delivery Slip')
        return getattr(doc, '_description', '') or model

    def _render_block_document_title(self, s, doc, company):
        fmap = self.get_field_map()
        number = self._safe_getattr(doc, fmap.get('number', 'name'), '')
        mode = s.get('display_mode', 'type_and_number')
        custom = s.get('custom_label', '')

        if mode == 'custom' and custom:
            title = custom.replace('{number}', str(number)).replace('{type}', self._get_document_type_label(doc))
        elif mode == 'type_only':
            title = custom if custom else self._get_document_type_label(doc)
        elif mode == 'number_only':
            title = str(number)
        else:
            doc_type = custom if custom else self._get_document_type_label(doc)
            title = '%s %s' % (doc_type, number) if number else doc_type

        size = s.get('font_size', '20')
        bold = 'font-weight:bold;' if s.get('bold', True) else ''
        align = s.get('alignment', 'left')
        lh = s.get('line_height', '1.2')
        return Markup(
            '<div class="axo-block axo-doc-title" style="font-size:%spx;%stext-align:%s;line-height:%s;margin-bottom:12px;">%s</div>'
            % (size, bold, align, lh, title)
        )

    def _render_block_partner_address(self, s, doc, company):
        fmap = self.get_field_map()
        field = 'partner_shipping' if s.get('use_shipping') and fmap.get('partner_shipping') else 'partner'
        partner = getattr(doc, fmap.get(field, fmap.get('partner', '')), None)
        if not partner:
            return Markup('')
        size = s.get('font_size', '10')
        lh = s.get('line_height', '1.4')
        lines = []
        lines.append('<div class="axo-block axo-partner-address" style="font-size:%spx;line-height:%s;margin-bottom:12px;">' % (size, lh))
        if partner.parent_id:
            lines.append('<strong>%s</strong><br/>' % (partner.parent_id.name or ''))
        lines.append('<strong>%s</strong><br/>' % (partner.name or ''))
        if partner.street:
            lines.append('%s<br/>' % partner.street)
        if partner.street2:
            lines.append('%s<br/>' % partner.street2)
        city = ' '.join(filter(None, [partner.zip or '', partner.city or '']))
        if city:
            lines.append('%s<br/>' % city)
        if partner.country_id:
            lines.append('%s<br/>' % partner.country_id.name)
        if s.get('show_vat', True) and partner.vat:
            lines.append('<br/>%s: %s' % (_('VAT ID'), partner.vat))
        lines.append('</div>')
        return Markup(''.join(lines))

    def _render_block_intro_text(self, s, doc, company):
        fmap = self.get_field_map()
        size = s.get('font_size', '10')
        lh = s.get('line_height', '1.4')
        salutation = s.get('salutation', _('Dear Sir or Madam,'))
        body = s.get('body', '')

        placeholders = {
            '{name}': '', '{first_name}': '', '{last_name}': '',
            '{company}': company.name or '',
            '{doc_name}': getattr(doc, 'name', '') or '',
        }
        try:
            partner = getattr(doc, fmap.get('partner', 'partner_id'), None)
            if partner:
                full = partner.name or ''
                placeholders['{name}'] = full
                name_parts = full.strip().split()
                placeholders['{first_name}'] = name_parts[0] if name_parts else ''
                placeholders['{last_name}'] = name_parts[-1] if name_parts else ''
        except Exception:
            pass

        for key, val in placeholders.items():
            salutation = salutation.replace(key, str(val))
            body = body.replace(key, str(val))

        parts = []
        if salutation:
            parts.append('<p style="margin:0 0 8px 0;">%s</p>' % salutation)
        if body:
            body_html = body.replace('\n', '<br/>')
            parts.append('<p style="margin:0;">%s</p>' % body_html)
        if not parts:
            return Markup('')
        return Markup(
            '<div class="axo-block axo-intro-text" style="font-size:%spx;line-height:%s;margin-bottom:12px;">%s</div>'
            % (size, lh, ''.join(parts))
        )

    def _render_block_info_table(self, s, doc, company):
        fmap = self.get_field_map()
        rows = []
        if s.get('show_number', True) and fmap.get('number'):
            val = self._safe_getattr(doc, fmap['number'])
            if val:
                rows.append((s.get('label_number', _('Number')), val))
        if s.get('show_date', True) and fmap.get('date'):
            val = self._safe_getattr(doc, fmap['date'])
            if val:
                if hasattr(val, 'strftime'):
                    val = val.strftime('%d.%m.%Y')
                rows.append((s.get('label_date', _('Date')), val))
        if s.get('show_reference', True) and fmap.get('reference'):
            val = self._safe_getattr(doc, fmap['reference'])
            if val:
                rows.append((s.get('label_reference', _('Reference')), val))
        if s.get('show_payment_term', True) and fmap.get('payment_term'):
            val = self._safe_getattr(doc, fmap['payment_term'])
            if val:
                rows.append((s.get('label_payment_term', _('Payment Terms')), val))
        if s.get('show_salesperson') and fmap.get('salesperson'):
            try:
                user_rec = getattr(doc, fmap['salesperson'], None)
                if user_rec:
                    name = getattr(user_rec, 'name', None) or getattr(user_rec, 'display_name', '') or ''
                    if name:
                        rows.append((s.get('label_salesperson', _('Salesperson')), name))
            except Exception:
                pass
        if s.get('show_salesperson_email') and fmap.get('salesperson'):
            try:
                user_rec = getattr(doc, fmap['salesperson'], None)
                if user_rec:
                    email = getattr(user_rec, 'email', '') or ''
                    if not email and hasattr(user_rec, 'partner_id'):
                        email = getattr(user_rec.partner_id, 'email', '') or ''
                    if email:
                        rows.append((s.get('label_salesperson_email', _('Email')), email))
            except Exception:
                pass
        if s.get('show_customer_number'):
            try:
                partner_field = fmap.get('partner', 'partner_id')
                partner = getattr(doc, partner_field, None)
                ref = getattr(partner, 'ref', None) or '' if partner else ''
                if ref:
                    rows.append((s.get('label_customer_number', _('Customer No.')), ref))
            except Exception:
                pass
        if not rows:
            return Markup('')
        cols = int(s.get('columns', 2))
        size = s.get('font_size', '10')
        lh = s.get('line_height', '1.2')
        lh_f = float(lh) if lh else 1.2
        if lh_f <= 1.0:
            vpad = '0'
        elif lh_f <= 1.2:
            vpad = '1'
        elif lh_f <= 1.4:
            vpad = '2'
        else:
            vpad = '3'
        td_style = 'padding:%spx 8px %spx 0;border:none;line-height:%s;' % (vpad, vpad, lh)
        td_val_style = 'padding:%spx 8px;border:none;line-height:%s;' % (vpad, lh)
        html = ['<table class="axo-block axo-info-table o_ignore_layout_styling" style="width:100%%;margin-bottom:12px;border-collapse:collapse;border:none;font-size:%spx;">' % size]
        for i in range(0, len(rows), cols):
            html.append('<tr>')
            for j in range(cols):
                idx = i + j
                if idx < len(rows):
                    label, val = rows[idx]
                    html.append(
                        '<td style="%s"><strong>%s:</strong></td>'
                        '<td style="%s">%s</td>' % (td_style, label, td_val_style, val)
                    )
                else:
                    html.append('<td style="border:none;"></td><td style="border:none;"></td>')
            html.append('</tr>')
        html.append('</table>')
        return Markup(''.join(html))

    def _render_block_line_items(self, s, doc, company):
        fmap = self.get_field_map()
        lines = self._get_doc_lines(doc)
        if not lines:
            return Markup('')

        currency = getattr(doc, fmap.get('currency', 'currency_id'), None)
        sym = currency.symbol if currency else '€'
        cur_pos = getattr(currency, 'position', 'after') if currency else 'after'
        monetary_fields = {'line_price_unit', 'line_subtotal'}

        all_col_defs = {
            'position':    ('show_position',    'label_position',    _('Pos.'),          '_position',       'center'),
            'sku':         ('show_sku',         'label_sku',         _('SKU'),            '_sku',            'left'),
            'product':     ('show_product',     'label_product',     _('Product'),        'line_product',     'left'),
            'description': ('show_description', 'label_description', _('Description'),    'line_name',        'left'),
            'quantity':    ('show_quantity',     'label_quantity',    _('Quantity'),       'line_quantity',     'right'),
            'uom':         ('show_uom',         'label_uom',         _('Unit'),           'line_uom',         'left'),
            'price_unit':  ('show_price_unit',  'label_price_unit',  _('Unit Price'),     'line_price_unit',  'right'),
            'discount':    ('show_discount',    'label_discount',    _('Discount %'),     'line_discount',    'right'),
            'taxes':       ('show_taxes',       'label_taxes',       _('Taxes'),          'line_taxes',       'left'),
            'subtotal':    ('show_subtotal',    'label_subtotal',    _('Subtotal'),       'line_subtotal',    'right'),
        }
        default_order = ['position', 'sku', 'product', 'description', 'quantity', 'uom',
                         'price_unit', 'discount', 'taxes', 'subtotal']
        column_order = list(s.get('column_order') or default_order)
        for col_id in default_order:
            if col_id not in column_order:
                column_order.append(col_id)

        header_cells = []
        col_keys = []
        for col_id in column_order:
            cdef = all_col_defs.get(col_id)
            if not cdef:
                continue
            show_key, label_key, default_label, fmap_key, align = cdef
            default_show = col_id not in ('taxes', 'sku')
            if not s.get(show_key, default_show):
                continue
            if not fmap_key.startswith('_') and not fmap.get(fmap_key):
                continue
            header_cells.append(s.get(label_key, default_label))
            col_keys.append((fmap_key, align))
        if not header_cells:
            return Markup('')

        lh = s.get('line_height', '1.2')
        font_size = s.get('font_size', '10')
        style = s.get('table_style', 'minimal')
        hdr_bg = s.get('header_bg', '#000000')
        hdr_fg = s.get('header_fg', '#ffffff')
        stripe_c = s.get('stripe_color', '#f8f9fa')
        has_border = style in ('bordered', 'striped_bordered')
        has_stripe = style in ('striped', 'striped_bordered')

        border_css = '1px solid #dee2e6' if has_border else 'none'
        tbl_border = 'border:1px solid #dee2e6;' if has_border else 'border:none;'
        th_style = (
            'padding:6px 8px;text-align:left;font-size:%spx;line-height:%s;'
            'background:%s;color:%s;border:%s;'
            % (font_size, lh, hdr_bg, hdr_fg, border_css)
        )
        td_base = 'padding:4px 8px;font-size:%spx;line-height:%s;' % (font_size, lh)

        if style == 'minimal':
            td_border = 'border:none;border-bottom:1px solid #ddd;'
            th_style = (
                'padding:6px 8px;text-align:left;font-size:%spx;line-height:%s;'
                'border:none;border-bottom:2px solid %s;color:%s;background:transparent;'
                % (font_size, lh, hdr_bg, hdr_bg)
            )
        elif style == 'clean':
            td_border = 'border:none;'
            th_style = (
                'padding:6px 8px;text-align:left;font-size:%spx;line-height:%s;'
                'border:none;font-weight:bold;background:transparent;'
                % (font_size, lh)
            )
        else:
            td_border = 'border:%s;' % border_css

        html = [
            '<table class="axo-block axo-line-items o_ignore_layout_styling" '
            'style="width:100%%;margin-bottom:12px;border-collapse:collapse;%s">' % tbl_border
        ]
        html.append('<thead><tr>')
        for hdr in header_cells:
            html.append('<th style="%s">%s</th>' % (th_style, hdr))
        html.append('</tr></thead><tbody>')

        row_idx = 0
        pos_nr = 0
        for line in lines:
            display = getattr(line, 'display_type', False)
            if display == 'line_section':
                html.append(
                    '<tr><td colspan="%d" style="padding:6px 0 2px;font-weight:bold;'
                    'font-size:%spx;border:none;line-height:%s;">%s</td></tr>'
                    % (len(header_cells), font_size, lh,
                       self._safe_getattr(line, fmap.get('line_name', 'name'))))
                continue
            if display == 'line_note':
                html.append(
                    '<tr><td colspan="%d" style="padding:2px 0;font-style:italic;'
                    'font-size:%spx;border:none;line-height:%s;">%s</td></tr>'
                    % (len(header_cells), font_size, lh,
                       self._safe_getattr(line, fmap.get('line_name', 'name'))))
                continue

            pos_nr += 1
            bg = ''
            if has_stripe and row_idx % 2 == 1:
                bg = 'background:%s;' % stripe_c
            html.append('<tr style="%s">' % bg)
            for key, align in col_keys:
                if key == '_position':
                    html.append(
                        '<td style="%stext-align:%s;%s">%d</td>'
                        % (td_base, align, td_border, pos_nr)
                    )
                    continue
                if key == '_sku':
                    sku_val = ''
                    try:
                        product = getattr(line, fmap.get('line_product', 'product_id'), None)
                        if product:
                            sku_val = getattr(product, 'default_code', '') or ''
                    except Exception:
                        pass
                    html.append(
                        '<td style="%stext-align:%s;%s">%s</td>'
                        % (td_base, align, td_border, sku_val)
                    )
                    continue
                field_name = fmap.get(key, '')
                val = self._safe_getattr(line, field_name, '')
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    num = '{:,.2f}'.format(val).replace(',', 'X').replace('.', ',').replace('X', '.')
                    if key in monetary_fields:
                        val = ('%s\u00a0%s' % (sym, num)) if cur_pos == 'before' else ('%s\u00a0%s' % (num, sym))
                    else:
                        val = num
                html.append(
                    '<td style="%stext-align:%s;%s">%s</td>'
                    % (td_base, align, td_border, val)
                )
            html.append('</tr>')
            row_idx += 1
        html.append('</tbody></table>')
        return Markup(''.join(html))

    def _render_block_subtotals(self, s, doc, company):
        fmap = self.get_field_map()
        currency = getattr(doc, fmap.get('currency', ''), None)
        sym = currency.symbol if currency else '€'
        cur_pos = getattr(currency, 'position', 'after') if currency else 'after'
        align = s.get('alignment', 'right')
        lh = s.get('line_height', '1.2')
        font_size = s.get('font_size', '10')
        style = s.get('table_style', 'minimal')
        total_line = s.get('total_line_style', 'double')
        hdr_bg = s.get('header_bg', '')
        hdr_fg = s.get('header_fg', '')
        stripe_c = s.get('stripe_color', '#f8f9fa')
        has_border = style in ('bordered',)
        has_stripe = style in ('striped',)

        def fmt(v):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                return str(v)
            num = '{:,.2f}'.format(v).replace(',', 'X').replace('.', ',').replace('X', '.')
            return ('%s\u00a0%s' % (sym, num)) if cur_pos == 'before' else ('%s\u00a0%s' % (num, sym))

        full_width = s.get('full_width', False)
        border_css = '1px solid #dee2e6' if has_border else 'none'
        if full_width:
            tbl_align = 'width:100%;'
        else:
            tbl_align = 'margin-left:auto;' if align == 'right' else ('margin-right:auto;' if align == 'left' else 'margin:0 auto;')
        tbl_style = '%sborder-collapse:collapse;font-size:%spx;' % (tbl_align, font_size)
        if has_border:
            tbl_style += 'border:1px solid #dee2e6;'
        else:
            tbl_style += 'border:none;'

        label_align = 'text-align:left;' if full_width else ''
        td_base = 'padding:3px 12px;line-height:%s;border:%s;%s' % (lh, border_css, label_align)
        td_val = 'padding:3px 12px;line-height:%s;text-align:right;border:%s;' % (lh, border_css)

        if total_line == 'double':
            total_border = 'border-top:3px double #000;'
        elif total_line == 'bold':
            total_border = 'border-top:2px solid #000;'
        elif total_line == 'thin':
            total_border = 'border-top:1px solid #000;'
        else:
            total_border = ''

        html = ['<div class="axo-block axo-subtotals" style="text-align:%s;margin-bottom:12px;">' % align]
        html.append('<table class="o_ignore_layout_styling" style="%s">' % tbl_style)

        rows = []
        untaxed = self._safe_getattr(doc, fmap.get('amount_untaxed', ''), 0) or 0
        tax = self._safe_getattr(doc, fmap.get('amount_tax', ''), 0) or 0
        total_val = self._safe_getattr(doc, fmap.get('amount_total', ''), 0) or 0

        if untaxed or total_val:
            rows.append(('normal', s.get('label_subtotal', _('Subtotal')), fmt(untaxed)))
        if s.get('show_tax_details', True):
            rows.append(('normal', s.get('label_tax', _('Taxes')), fmt(tax)))
        if total_val or untaxed:
            rows.append(('total', s.get('label_total', _('Total')), fmt(total_val)))

        if s.get('show_residual', True):
            residual_field = fmap.get('amount_residual')
            if residual_field:
                residual = self._safe_getattr(doc, residual_field, 0) or 0
                if residual != total_val:
                    rows.append(('normal', s.get('label_residual', _('Amount Due')), fmt(residual)))

        for row_idx, (rtype, label, value) in enumerate(rows):
            bg = ''
            if has_stripe and row_idx % 2 == 1:
                bg = 'background:%s;' % stripe_c

            if rtype == 'total':
                total_bg = ('background:%s;' % hdr_bg) if hdr_bg else ''
                total_fg = ('color:%s;' % hdr_fg) if hdr_fg else ''
                html.append(
                    '<tr style="font-weight:bold;%s%s">'
                    '<td style="%s%s%s">%s</td>'
                    '<td style="%s%s%s">%s</td>'
                    '</tr>' % (
                        total_bg, total_fg,
                        td_base, total_border, total_bg,
                        label,
                        td_val, total_border, total_bg,
                        value,
                    )
                )
            else:
                html.append(
                    '<tr style="%s">'
                    '<td style="%s">%s</td>'
                    '<td style="%s">%s</td>'
                    '</tr>' % (bg, td_base, label, td_val, value)
                )

        html.append('</table></div>')
        return Markup(''.join(html))

    def _render_block_notes(self, s, doc, company):
        fmap = self.get_field_map()
        font_size = s.get('font_size', '10')
        lh = s.get('line_height', '1.4')
        p_style = 'font-size:%spx;margin:0 0 6px 0;' % font_size
        parts = []

        shipping = s.get('shipping_text', '')
        if shipping:
            parts.append('<p style="%s">%s</p>' % (p_style, shipping.replace('\n', '<br/>')))

        if s.get('show_payment_terms', True) and fmap.get('payment_term'):
            val = self._safe_getattr(doc, fmap['payment_term'])
            if val:
                label = s.get('label_payment_terms', _('Payment Terms'))
                parts.append('<p style="%s"><strong>%s:</strong> %s</p>' % (p_style, label, val))

        if s.get('show_payment_method', True) and fmap.get('payment_method'):
            pm_line = getattr(doc, fmap['payment_method'], None)
            if pm_line:
                pm_name = ''
                try:
                    pm = getattr(pm_line, 'payment_method_id', None)
                    if pm:
                        pm_name = pm.display_name or pm_line.display_name or ''
                    else:
                        pm_name = pm_line.display_name or ''
                except Exception:
                    pm_name = str(pm_line.display_name or '') if pm_line else ''
                if pm_name:
                    label = s.get('label_payment_method', _('Payment Method'))
                    parts.append('<p style="%s"><strong>%s:</strong> %s</p>' % (p_style, label, pm_name))

        payment = s.get('payment_text', '')
        if payment:
            parts.append('<p style="%s">%s</p>' % (p_style, payment.replace('\n', '<br/>')))

        if s.get('show_payment_ref', False) and fmap.get('payment_reference'):
            val = self._safe_getattr(doc, fmap['payment_reference'])
            if val:
                label = s.get('label_payment_ref', _('Payment Reference'))
                parts.append('<p style="%s"><strong>%s:</strong> %s</p>' % (p_style, label, val))

        if s.get('show_notes', True) and fmap.get('notes'):
            val = self._safe_getattr(doc, fmap['notes'])
            if val:
                parts.append('<div style="%s">%s</div>' % (p_style, val))

        custom = s.get('custom_text', '')
        if custom:
            parts.append('<p style="%s">%s</p>' % (p_style, custom.replace('\n', '<br/>')))

        if not parts:
            return Markup('')
        return Markup('<div class="axo-block axo-notes" style="line-height:%s;margin-bottom:12px;">%s</div>' % (lh, ''.join(parts)))

    def _render_block_free_text(self, s, doc, company):
        content = s.get('content', '')
        if not content:
            return Markup('')
        content = content.replace('\n', '<br/>')
        size = s.get('font_size', '12')
        align = s.get('alignment', 'left')
        lh = s.get('line_height', '1.4')
        return Markup(
            '<div class="axo-block axo-free-text" style="font-size:%spx;text-align:%s;line-height:%s;margin-bottom:12px;">%s</div>'
            % (size, align, lh, content)
        )

    def _render_block_separator(self, s, doc, company):
        style = s.get('style', 'solid')
        color = s.get('color', '#000000')
        margin = s.get('margin', '10')
        return Markup(
            '<hr class="axo-block axo-separator" style="border:none;border-top:1px %s %s;margin:%spx 0;"/>'
            % (style, color, margin)
        )

    def _render_block_spacer(self, s, doc, company):
        height = s.get('height', '20')
        return Markup('<div class="axo-block axo-spacer" style="height:%spx;"></div>' % height)

    def _render_block_page_break(self, s, doc, company):
        return Markup('<div class="axo-block axo-page-break" style="page-break-after:always;"></div>')

    def _render_block_two_columns(self, s, doc, company):
        # Uses display:table instead of flexbox for wkhtmltopdf compatibility
        left_ratio = int(s.get('left_ratio', 50))
        right_ratio = 100 - left_ratio
        left_blocks = s.get('left_blocks', [])
        right_blocks = s.get('right_blocks', [])
        left_html = ''.join(str(self._render_block_html(b, doc, company)) for b in left_blocks)
        right_html = ''.join(str(self._render_block_html(b, doc, company)) for b in right_blocks)
        return Markup(
            '<div class="axo-block axo-two-columns" style="display:table;width:100%%;margin-bottom:12px;">'
            '<div style="display:table-cell;vertical-align:top;width:%d%%;padding-right:8px;">%s</div>'
            '<div style="display:table-cell;vertical-align:top;width:%d%%;padding-left:8px;">%s</div>'
            '</div>' % (left_ratio, left_html, right_ratio, right_html)
        )

    def _render_block_footer(self, s, doc, company):
        return Markup('')

    def _render_footer_html(self, company):
        """Render footer as standalone HTML for wkhtmltopdf --footer-html."""
        blocks = self.get_blocks()
        footer_block = None
        for b in blocks:
            if b.get('type') == 'footer':
                footer_block = b
                break
        if not footer_block:
            return ''

        s = footer_block.get('settings', {})
        layout = s.get('layout', 'columns')
        align = s.get('alignment', 'left')
        font_size = s.get('font_size', '8')
        lh = s.get('line_height', '1.2')
        color = s.get('text_color', '#666666')
        sep_style = s.get('separator_style', 'solid')
        sep_color = s.get('separator_color', '#cccccc')

        parts_left = []
        parts_center = []
        parts_right = []

        if s.get('show_company_name', True) and company.name:
            parts_left.append('<strong>%s</strong>' % company.name)
        if s.get('show_address', True):
            addr = []
            if company.street:
                addr.append(company.street)
            if company.street2:
                addr.append(company.street2)
            city_parts = []
            if company.zip:
                city_parts.append(company.zip)
            if company.city:
                city_parts.append(company.city)
            if city_parts:
                addr.append(' '.join(city_parts))
            if addr:
                parts_left.append(' · '.join(addr))
        if s.get('show_phone', True) and company.phone:
            parts_center.append('%s: %s' % (_('Phone'), company.phone))
        if s.get('show_email', True) and company.email:
            parts_center.append('%s: %s' % (_('Email'), company.email))
        if s.get('show_website', False) and company.website:
            parts_center.append('%s: %s' % (_('Web'), company.website))
        if s.get('show_vat', True) and company.vat:
            parts_right.append('%s: %s' % (_('VAT ID'), company.vat))
        if s.get('show_company_registry', False) and company.company_registry:
            parts_right.append('%s: %s' % (_('Reg. No.'), company.company_registry))
        if s.get('show_bank', True):
            banks = company.partner_id.bank_ids
            if banks:
                bank = banks[0]
                parts_right.append('IBAN: %s' % (bank.acc_number or ''))
                if bank.bank_id and bank.bank_id.bic:
                    parts_right.append('BIC: %s' % bank.bank_id.bic)
        if s.get('show_ceo', False) and s.get('ceo_name'):
            label = s.get('ceo_label', _('CEO'))
            parts_right.append('%s: %s' % (label, s['ceo_name']))

        custom_l = s.get('custom_left', '')
        custom_c = s.get('custom_center', '')
        custom_r = s.get('custom_right', '')
        if custom_l:
            parts_left.append(custom_l.replace('\n', '<br/>'))
        if custom_c:
            parts_center.append(custom_c.replace('\n', '<br/>'))
        if custom_r:
            parts_right.append(custom_r.replace('\n', '<br/>'))

        sep_html = ''
        if sep_style != 'none':
            sep_html = '<hr style="border:none;border-top:1px %s %s;margin:0 0 4px 0;"/>' % (sep_style, sep_color)

        base_style = 'font-family:sans-serif;font-size:%spx;line-height:%s;color:%s;' % (font_size, lh, color)

        td_base = 'vertical-align:top;border:none;width:33.33%%;text-align:%s !important;' % align

        if layout == 'columns':
            body = (
                '%s'
                '<table style="width:100%%;table-layout:fixed;border-collapse:collapse;border:none;%s">'
                '<tr style="border:none;">'
                '<td style="%spadding:0 4px 0 0;">%s</td>'
                '<td style="%spadding:0 4px;">%s</td>'
                '<td style="%spadding:0 0 0 4px;">%s</td>'
                '</tr></table>'
                % (sep_html, base_style,
                   td_base, '<br/>'.join(parts_left),
                   td_base, '<br/>'.join(parts_center),
                   td_base, '<br/>'.join(parts_right))
            )
        elif layout == 'centered':
            all_parts = parts_left + parts_center + parts_right
            body = '%s<div style="text-align:%s !important;%s">%s</div>' % (
                sep_html, align, base_style, ' · '.join(all_parts)
            )
        else:
            all_parts = parts_left + parts_center + parts_right
            body = '%s<div style="text-align:%s !important;%s">%s</div>' % (
                sep_html, align, base_style, ' · '.join(all_parts)
            )

        page_num = ''
        if s.get('show_page_numbers', True):
            page_num = (
                '<div style="text-align:%s !important;font-size:%spx;color:%s;margin-top:2px;">'
                '%s <span class="page"></span> %s <span class="topage"></span>'
                '</div>' % (align, font_size, color, _('Page'), _('of'))
            )

        layout_data = json.loads(self.layout_json or '{}')
        m = layout_data.get('margins', {})
        ml = m.get('left', 7)
        mr = m.get('right', 7)

        html = (
            '<!DOCTYPE html>'
            '<html><head><meta charset="utf-8"/>'
            '<style>body{margin:0;padding:0 %smm 0 %smm;}'
            'table,tr,td,th{border:none !important;}</style>'
            '</head><body>%s%s</body></html>'
            % (mr, ml, body, page_num)
        )
        return html

    def _render_footer_inner_html(self, company):
        """Render footer inner HTML for embedding in the report template's <div class='footer'>."""
        blocks = self.get_blocks()
        footer_block = None
        for b in blocks:
            if b.get('type') == 'footer':
                footer_block = b
                break
        if not footer_block:
            return ''

        s = footer_block.get('settings', {})
        layout = s.get('layout', 'columns')
        align = s.get('alignment', 'left')
        font_size = s.get('font_size', '8')
        lh = s.get('line_height', '1.2')
        color = s.get('text_color', '#666666')
        sep_style = s.get('separator_style', 'solid')
        sep_color = s.get('separator_color', '#cccccc')

        parts_left = []
        parts_center = []
        parts_right = []

        if s.get('show_company_name', True) and company.name:
            parts_left.append('<strong>%s</strong>' % company.name)
        if s.get('show_address', True):
            addr = []
            if company.street:
                addr.append(company.street)
            if company.street2:
                addr.append(company.street2)
            city_parts = []
            if company.zip:
                city_parts.append(company.zip)
            if company.city:
                city_parts.append(company.city)
            if city_parts:
                addr.append(' '.join(city_parts))
            if addr:
                parts_left.append(' &middot; '.join(addr))
        if s.get('show_phone', True) and company.phone:
            parts_center.append('%s: %s' % (_('Phone'), company.phone))
        if s.get('show_email', True) and company.email:
            parts_center.append('%s: %s' % (_('Email'), company.email))
        if s.get('show_website', False) and company.website:
            parts_center.append('%s: %s' % (_('Web'), company.website))
        if s.get('show_vat', True) and company.vat:
            parts_right.append('%s: %s' % (_('VAT ID'), company.vat))
        if s.get('show_company_registry', False) and company.company_registry:
            parts_right.append('%s: %s' % (_('Reg. No.'), company.company_registry))
        if s.get('show_bank', True):
            banks = company.partner_id.bank_ids
            if banks:
                bank = banks[0]
                parts_right.append('IBAN: %s' % (bank.acc_number or ''))
                if bank.bank_id and bank.bank_id.bic:
                    parts_right.append('BIC: %s' % bank.bank_id.bic)
        if s.get('show_ceo', False) and s.get('ceo_name'):
            label = s.get('ceo_label', _('CEO'))
            parts_right.append('%s: %s' % (label, s['ceo_name']))

        custom_l = s.get('custom_left', '')
        custom_c = s.get('custom_center', '')
        custom_r = s.get('custom_right', '')
        if custom_l:
            parts_left.append(custom_l.replace('\n', '<br/>'))
        if custom_c:
            parts_center.append(custom_c.replace('\n', '<br/>'))
        if custom_r:
            parts_right.append(custom_r.replace('\n', '<br/>'))

        sep_html = ''
        if sep_style != 'none':
            sep_html = '<hr style="border:none;border-top:1px %s %s;margin:0 0 4px 0;"/>' % (sep_style, sep_color)

        base_style = 'font-family:sans-serif;font-size:%spx;line-height:%s;color:%s;' % (font_size, lh, color)

        td_base = 'vertical-align:top;border:none;width:33.33%%;text-align:%s !important;' % align

        if layout == 'columns':
            body = (
                '%s'
                '<table style="width:100%%;table-layout:fixed;border-collapse:collapse;border:none;%s">'
                '<tr style="border:none;">'
                '<td style="%spadding:0 4px 0 0;">%s</td>'
                '<td style="%spadding:0 4px;">%s</td>'
                '<td style="%spadding:0 0 0 4px;">%s</td>'
                '</tr></table>'
                % (sep_html, base_style,
                   td_base, '<br/>'.join(parts_left),
                   td_base, '<br/>'.join(parts_center),
                   td_base, '<br/>'.join(parts_right))
            )
        elif layout == 'centered':
            all_parts = parts_left + parts_center + parts_right
            body = '%s<div style="text-align:%s !important;%s">%s</div>' % (
                sep_html, align, base_style, ' &middot; '.join(all_parts)
            )
        else:
            all_parts = parts_left + parts_center + parts_right
            body = '%s<div style="text-align:%s !important;%s">%s</div>' % (
                sep_html, align, base_style, ' &middot; '.join(all_parts)
            )

        page_num = ''
        if s.get('show_page_numbers', True):
            page_num = (
                '<div style="text-align:%s !important;font-size:%spx;color:%s;margin-top:2px;">'
                '%s <span class="page"></span> %s <span class="topage"></span>'
                '</div>' % (align, font_size, color, _('Page'), _('of'))
            )

        return body + page_num

    # ------------------------------------------------------------------
    #  Full document rendering
    # ------------------------------------------------------------------

    def render_full_html(self, doc, company=None):
        """Render the entire layout for one document record, returns Markup."""
        if not company:
            company = doc.company_id if hasattr(doc, 'company_id') and doc.company_id else self.env.company
        blocks = self.get_blocks()
        parts = []
        for block in blocks:
            parts.append(str(self._render_block_html(block, doc, company)))
        return Markup(''.join(parts))

    # ------------------------------------------------------------------
    #  Actions
    # ------------------------------------------------------------------

    def action_open_visual_editor(self):
        """Open the OWL visual editor from the form view."""
        self.ensure_one()
        IrReport = self.env['ir.actions.report']
        allowed = IrReport._axoline_allowed_models()
        if allowed and self.model_name not in allowed:
            return IrReport._axoline_upsell_action()
        return {
            'type': 'ir.actions.client',
            'tag': 'axoline_layout_editor',
            'name': _('Layout: %s') % self.name,
            'params': {
                'layout_custom_id': self.id,
                'report_id': self.report_id.id,
            },
        }
