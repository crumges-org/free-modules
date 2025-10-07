{
    'name': 'TimePicker Pro',
    'version': '1.0',
    'category': 'User Interface',
    'summary': 'An intuitive and user-friendly TimePicker Pro for Odoo.',
    'description': 'The Enhanced TimePicker Pro improves the time input experience in Odoo. '
                   'It allows users to easily select and input time values with precision, '
                   'making it ideal for applications requiring accurate time management.',
    'author': 'Master Software Solutions',
    'website': 'https://www.mastersoftwaresolutions.com/',
    'depends': ['base'],
    "assets": {
        'web.assets_backend': [
            'mss_timepicker/static/src/xml/timepicker.xml',
            'mss_timepicker/static/src/css/timepicker.css',
            'mss_timepicker/static/src/js/timepicker.js',
        ],
    },
    'live_test_url': 'https://www.mastersoftwaresolutions.com/request-live-preview',
    'images': ['static/description/main_screenshot.gif', 'static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
