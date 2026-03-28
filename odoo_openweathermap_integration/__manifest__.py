# -*- coding: utf-8 -*-
{
    'name': 'Odoo OpenWeather Integration',
    'version': '18.0.1.8.0',
    'summary': "Display live weather data in Odoo using OpenWeatherMap API, directly from your dashboard.",

    'description': """
OpenWeatherMap Integration for Odoo
===================================

Display real-time weather information right inside your Odoo dashboard.

Key Features
------------
* Shows current weather in the top-right corner of the Odoo interface
* Displays temperature, city, and weather condition
* Provides quick access to detailed information on click
* Simple setup - add API key and location in Settings
* Supports user-level preferences and access control
* Uses OpenWeatherMap free API (v2.5) for live data

How It Works
------------
1. Add your OpenWeatherMap API key under Settings → General Settings
2. Manage who can view the widget via Access Rights
3. Each user can configure their own preferences
4. The weather widget appears automatically in the top-right corner of the Odoo dashboard

Note
----
You can obtain a free API key by signing up on the OpenWeatherMap website:
https://home.openweathermap.org/api_keys

Requirements
------------
* Odoo 18.0
* Web module installed
* OpenWeatherMap API key (Free plan supported)

Support
-------
Built by ERPGO  
\nWebsite: https://www.erpgo.az  
\nEmail: contact@erpgo.az  

Copyright (c) 2025 ERPGO.
All rights reserved.
""",
    'author': "ERPGO",
    'website': "https://www.erpgo.az",
    'category': 'Productivity',
    'license': 'Other proprietary',
    'maintainer': 'ERPGO',
    'support': 'contact@erpgo.az',
    'depends': ['web'],
    'data': [
        'security/openweathermap_security.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_openweathermap_integration/static/src/js/WeatherMenu.js',
            'odoo_openweathermap_integration/static/src/xml/weather_notification_templates.xml',
        ],
    },
    'external_dependencies': {
        'python': ['geocoder'],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'cloc_exclude': [
        "**/*",
    ],
}
