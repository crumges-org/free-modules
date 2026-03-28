from odoo import models, fields

class ResCompany(models.Model):
    _inherit = "res.company"

    openweathermap_api_key = fields.Char(string='OpenWeatherMap API Key', help="API key from OpenWeatherMap")
