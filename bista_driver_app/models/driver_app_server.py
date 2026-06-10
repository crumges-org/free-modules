from odoo import fields, models, api


class DriverAppServer(models.Model):
    _name = 'driver.app.server'
    _description = 'Driver App Configuration'

    name = fields.Char(string="Name", required=True)
    server_route = fields.Char(string="Domain", required=True)
    api_route = fields.Char(string="API Route", required=True)
    content_route = fields.Char(string="Content Route")
    web_route = fields.Char(string="Web Route")

    server_ip_address = fields.Char(string="IP Address")
