from odoo import fields, models, api


class GeolocationSource(models.Model):
    _name = 'geolocation.source'
    _description = 'Geolocation Source'

    name = fields.Char(string='Source', required=True)
    source_type = fields.Selection([
        ('serial', 'Serial'),
        ('shipment', 'Shipment'),
    ], string="Type", required=True)
    source_description = fields.Text(string='Description')
    active = fields.Boolean(string="Active", default=True)