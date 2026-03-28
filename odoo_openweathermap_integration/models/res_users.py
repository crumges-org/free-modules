# -*- coding: utf-8 -*-
import requests
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    """
    Extends the 'res.users' model to include additional fields related to
    weather information.
    """
    _inherit = "res.users"

    show_weather_notification = fields.Boolean(string="Weather Notification", default=False)
    weather_location_type = fields.Selection(selection=[
        ('timezone', 'User\'s Timezone'),
        ('auto', 'Browser Location'),
        ('manual', 'Manual Location'),
    ], string="Set Location", default='timezone',
        help="Setting and managing locations")
    weather_city = fields.Char(string='Weather City', help="City of the user")
    weather_temp_scale_type = fields.Selection(selection=[
        ('metric', 'Metric (°C)'),
        ('imperial', 'Imperial (°F)'),
        ('standard', 'Standard (K)'),
    ], string='Temperature Scale', default='metric', help="Select the temperature scale for weather data")
    
    @api.onchange('weather_location_type','partner_id.city')
    def _onchange_weather_location_type(self):
        for user in self:
            if user.weather_location_type == 'manual' and not user.weather_city:
                user.weather_city = user.partner_id.city
             
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['show_weather_notification', 'weather_temp_scale_type', 'weather_location_type', 'weather_city']
    
    @property   
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['show_weather_notification', 'weather_temp_scale_type', 'weather_location_type', 'weather_city']