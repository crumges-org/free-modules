# -*- coding: utf-8 -*-
{
    'name': "Driver App for Fleet & Delivery",

    'summary': "Driver & Shipment Tracking.",

    'description': """
        Module for Fleet app api
    """,

    "version": "18.0.1.0.0",
    "author": "Bista Solutions Inc",
    "website": "http://www.bistasolutions.com",
    "license": "LGPL-3",


    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'base_setup','web_editor','stock', 'contacts','documents',
                'base_address_extended','bista_mobile_base'
                ],
    'external_dependencies': {
        'python': ['PyJWT', 'timezonefinder', 'shapely', 'google-auth'],
    },
    # always loaded
    'data': [
        'security/shipment.xml',
        'security/ir.model.access.csv',
        'security/res_partner_rules.xml',

        'data/data.xml',
        'data/sequence.xml',
        'data/stop_status.xml',
        'data/geolocation_history_shipment_source_data.xml',
        # 'data/otp_twilio_sms.xml',
        'data/ir_cron_fleet.xml',
        'data/fleet_offline_pdf_paperformat.xml',

        'views/fleet_driver_views.xml',
        'views/timeline.xml',
        'views/shipment.xml',
        'views/carrier.xml',
        'views/document.xml',
        'views/location.xml',
        'views/status.xml',
        'views/shipment_setting.xml',
        'views/res_partner.xml',
        'views/geolocation_history_views.xml',
        'views/geolocation_source_views.xml',
        'views/stop.xml',
        'views/items.xml',
        'views/driver_app_server.xml',
        # 'views/res_config_settings.xml',
        'views/documents_type.xml',
        'views/stop_status.xml',
        'views/shipment_instructions.xml',
        # 'views/twilio_sms.xml',
        # 'views/twilio_account_views.xml',
        'views/users.xml',
        # 'views/geolocation_source_views.xml',

        'wizard/shipment_wizard.xml',
        'wizard/assign_driver.xml',
        'wizard/shipment_cancellation_reason.xml',
        'wizard/shipment_fleet_map.xml',
        # 'wizard/sms_builder.xml',
        'wizard/shipment_config_settings.xml',

        'reports/shipment_instruction_report.xml',
        'views/partner_view.xml',
        'data/document_type.xml',
        'views/mail_views.xml',

    ],
    'assets': {
    #     'web.assets_frontend': [
    #         'bista_driver_app/static/src/core/l10n/localization_service.js',
    #     ],
    #     # 'web_editor.assets_wysiwyg': [
    #     #     "bista_driver_app/static/src/wysiwyg/wysiwyg.js",
    #     # ],
        'web.assets_backend': [
            'bista_driver_app/static/src/scss/*.scss',
            'bista_driver_app/static/src/js/badge_field.js',
            'bista_driver_app/static/src/js/dropdown.js',
            'bista_driver_app/static/src/js/form_controller.js',
            'bista_driver_app/static/src/js/list_binary_field.js',
            'bista_driver_app/static/src/js/list_controller.js',
            'bista_driver_app/static/src/js/list_renderer.js',
            'bista_driver_app/static/src/js/message_patch.js',
            'bista_driver_app/static/src/js/notebook.js',
            'bista_driver_app/static/src/js/notification.js',
            'bista_driver_app/static/src/js/relational_utils.js',
            'bista_driver_app/static/src/js/statusbar_field.js',
            'bista_driver_app/static/src/js/use_my_location.js',
            # 'bista_driver_app/static/src/js/*.js',
            'bista_driver_app/static/src/xml/*.xml',
            "bista_driver_app/static/src/js/map/map_field.js",
            "bista_driver_app/static/src/js/map/map_field.scss",
            "bista_driver_app/static/src/js/map/map_field.xml",
    #         # "bista_driver_app/static/src/js/tracking_map/map_field.js",
    #         # "bista_driver_app/static/src/js/tracking_map/map_field.scss",
    #         # "bista_driver_app/static/src/js/tracking_map/map_field.xml",
            "bista_driver_app/static/src/js/location_map/map_field.js",
            "bista_driver_app/static/src/js/location_map/map_field.scss",
            "bista_driver_app/static/src/js/location_map/map_field.xml",
            "bista_driver_app/static/src/js/osm_map/osm_map_widget.js",
            "bista_driver_app/static/src/js/osm_map/osm_map_widget.xml",
            "bista_driver_app/static/src/js/osm_map/osm_map_widget.scss",
            "bista_driver_app/static/src/js/osm_tracking_map/osm_tracking_map_widget.js",
            "bista_driver_app/static/src/js/osm_tracking_map/osm_tracking_map_widget.xml",
            "bista_driver_app/static/src/js/osm_tracking_map/osm_tracking_map_widget.scss",
    #         "bista_driver_app/static/src/js/autocomplete/autocomplete.js",
    #         "bista_driver_app/static/src/js/autocomplete/autocomplete.scss",
    #         "bista_driver_app/static/src/js/autocomplete/autocomplete.xml",
    #         "bista_driver_app/static/src/core/message_patch.js",
            'bista_driver_app/static/src/webclient/settings_from_view/*',
    #         # 'web_google_map/static/src/**/*',


        ]
    },
    "images": ["static/description/banner.gif"],
}
