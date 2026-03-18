# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def add_line_from_portal(self, product_id, quantity=1, price_unit=False):
        """Add a line to the sale order from portal"""
        self.ensure_one()
        product = self.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            raise UserError(_('Product not found.'))
        
        # Get price from product or use provided price
        if not price_unit:
            price_unit = product.list_price
        
        # Create order line
        order_line = self.env['sale.order.line'].sudo().create({
            'order_id': self.id,
            'product_id': product_id,
            'product_uom_qty': quantity,
            'price_unit': price_unit,
        })
        
        return {
            'success': True,
            'line_id': order_line.id,
            'name': order_line.name,
            'quantity': order_line.product_uom_qty,
            'price_unit': order_line.price_unit,
            'price_subtotal': order_line.price_subtotal,
        }

    def update_line_from_portal(self, line_id, quantity=False, price_unit=False):
        """Update a line in the sale order from portal"""
        self.ensure_one()
        order_line = self.order_line.filtered(lambda l: l.id == line_id)
        if not order_line:
            raise UserError(_('Order line not found.'))
        
        order_line = order_line[0]
        vals = {}
        if quantity:
            vals['product_uom_qty'] = quantity
        if price_unit:
            vals['price_unit'] = price_unit
        
        if vals:
            order_line.write(vals)
        
        return {
            'success': True,
            'line_id': order_line.id,
            'quantity': order_line.product_uom_qty,
            'price_unit': order_line.price_unit,
            'price_subtotal': order_line.price_subtotal,
            'amount_total': self.amount_total,
        }

    def delete_line_from_portal(self, line_id):
        """Delete a line from the sale order from portal"""
        self.ensure_one()
        order_line = self.order_line.filtered(lambda l: l.id == line_id)
        if not order_line:
            raise UserError(_('Order line not found.'))
        
        order_line.unlink()
        
        return {
            'success': True,
            'amount_total': self.amount_total,
        }

    def send_quotation_email_from_portal(self):
        """Send quotation by email from portal"""
        self.ensure_one()
        if self.state not in ('draft', 'sent'):
            raise UserError(_('Quotation must be in draft or sent state to be sent by email.'))
        
        # Use the standard send quotation email action
        template = self.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(
                self.id,
                force_send=True,
                email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature'
            )
        else:
            # Fallback: post a message
            self.message_post(
                body=_('Quotation sent by email from portal'),
                subject=_('Quotation: %s') % self.name,
            )
        
        return {
            'success': True,
            'message': _('Quotation has been sent by email.'),
        }
