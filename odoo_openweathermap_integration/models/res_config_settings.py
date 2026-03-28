from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    openweathermap_api_key = fields.Char(related='company_id.openweathermap_api_key', readonly=False, help="API key from OpenWeatherMap")
    