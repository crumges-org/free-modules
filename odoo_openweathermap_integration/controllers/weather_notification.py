# -*- coding: utf-8 -*-
import requests
from odoo import http, _
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

try:
    import geocoder
except ImportError:
    geocoder = None


class WeatherNotification(http.Controller):
    """
    Controller class for fetching weather details based on location.
    This class provides a controller to fetch weather information based on the
    user's location setting.
    It supports both automatic and manual location settings.
    """

    @http.route('/weather/notification/check', type='json', auth="user", methods=['POST'])
    def weather_notification(self):
        """
        Fetch OpenWeatherMap data based on the current user's settings.
        Success -> returns raw OWM JSON (name/sys/weather/main...).
        Error   -> returns {"error": <code>, "message": <human message>}.
        """
        user = request.env.user.sudo()
        company = user.company_id.sudo()
        if not user.show_weather_notification:
            return {'error': _('Weather notification is disabled'),
                    'message': _('Please enable weather notification in your user settings.')}
        
        if not company.openweathermap_api_key:
            return {'error': _('Weather API key is not set'),
                    'message': _('Please set your OpenWeatherMap API key in general settings.')}

        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'appid': company.openweathermap_api_key,
            'units': user.weather_temp_scale_type, # Use metric units for temperature (Celsius)
        }
        if not user.weather_location_type:
            return {'error': _('Weather location type is not set'),
                    'message': _('Please set your location type in your user settings.')}
        if user.weather_location_type == 'auto':
            if geocoder:
                try:
                    g = geocoder.ip('me')
                    if g.status_code == 200:
                        lat, lng = g.latlng
                        params.update({
                            'lat': round(lat, 2),
                            'lon': round(lng, 2)
                        })
                except Exception as e:
                    _logger.error("Error fetching geolocation: %s", e)
                    return {'error': _('Error fetching geolocation'),
                            'message': _('Could not fetch geolocation. Please check your network connection.')}
            else:
                return {'error': _('Geocoder library is not available'),
                        'message': _('Please install the geocoder library to use automatic location.')}
        elif user.weather_location_type == 'manual':
            if not user.weather_city:
                return {'error': _('Weather city is not set'),
                        'message': _('Please set your city in your user settings.')}
            params['q'] = user.weather_city
        elif user.weather_location_type == 'timezone':
            if not user.tz:
                return {'error': _('User timezone is not set'),
                        'message': _('Please set your timezone in your user settings.')}
            params['q'] = user.tz.split('/')[1] if '/' in user.tz else user.tz
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error("Error fetching weather data: %s", e)
            return {'error': response.json().get('message', 'Unknown error'),
                    'message': _('This error response is from OpenWeatherMap API.')}
        