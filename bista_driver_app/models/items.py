# -*- coding: utf-8 -*-
from odoo import fields, models, http, api, Command, _, SUPERUSER_ID
from markupsafe import Markup


class ShipmentItem(models.Model):
    _name = "shipment.item"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Item"

    name = fields.Char(string="Name", required=True)
    shipment_id = fields.Many2one('shipment.shipment', string="Shipment", ondelete='cascade')
    active = fields.Boolean(default=True, tracking=True)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if record.shipment_id:
            record.shipment_id.message_post(
                body=Markup(f"<p>Item added:</p><ul><li><b>{record.name}</b></li></ul>")
            )
        return record

    def write(self, vals):
        for record in self:
            old_name = record.name
            result = super().write(vals)
            if record.shipment_id and 'name' in vals:
                record.shipment_id.message_post(
                    body=Markup(f"<p>Item updated:</p><ul><li>{old_name} ➝ <b>{record.name}</b></li></ul>")
                )
        return result

    def unlink(self):
        for record in self:
            if record.shipment_id:
                record.shipment_id.message_post(
                    body=Markup(f"<p>Item removed:</p><ul><li><b>{record.name}</b></li></ul>")
                )
        return super().unlink()
