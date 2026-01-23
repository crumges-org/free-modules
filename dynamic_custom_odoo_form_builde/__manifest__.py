{
    'name': 'Custom Dynamic No-Code Drag-and-Drop Odoo Forms Builder — Embed on Websites, CRM/HR Integration, Conditional Logic & reCAPTCHA',
    'version': '18.0.1.11.1',
    'category': 'Tools',
    'summary': 'Create dynamic forms and embed them in external websites',
    'description': """Build custom no-code Odoo forms with drag-and-drop, website embed (JS/iFrame), CRM/HR integration, conditional logic & reCAPTCHA. Easy Odoo model mapping.
URL- dynamic-custom-odoo-form-builder
""",
    'author': 'WebbyCrown Solutions',
    'website': 'https://www.webbycrown.com',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    # Optional dependencies for additional functionality
    # 'hr' - for HR-related forms (job applications, employee surveys)
    # 'event' - for event registration forms
    'data': [
        'security/dynamic_forms_security.xml',
        'data/access_rights.xml',
        'data/email_templates.xml',
        'views/config_views.xml',
        'views/form_views.xml',
        'views/field_views.xml',
        'views/field_condition_views.xml',
        'views/field_mapping_views.xml',
        'views/email_notification_views.xml',
        'views/submission_views.xml',
        'views/reporting_views.xml',
        'views/menu_views.xml',
        'views/embed_templates.xml',
        'report/form_submission_report.xml',
        'data/dynamic_forms_data.xml',
        'demo/dynamic_forms_demo.xml',
        'data/dynamic_forms_config_data.xml',
        'data/dynamic_forms_setup_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dynamic_custom_odoo_form_builde/static/src/css/form_builder.css',
            'dynamic_custom_odoo_form_builde/static/src/js/dynamic_forms_assets.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'images': ['static/description/main_screenshot.png'],
    'icon': '/dynamic_custom_odoo_form_builde/static/description/icon.png',
    'license': 'LGPL-3',
}
