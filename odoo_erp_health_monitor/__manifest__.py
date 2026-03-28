{
    'name': 'Odoo ERP Health Monitor',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Monitor ERP server health and performance',
    'author': 'Syed Israr Ahmad',
    'website': 'https://www.linkedin.com/in/syed-israr-ahmad/',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/server_metrics_views.xml',
        'views/slow_query_views.xml',
        'views/cron_log_views.xml',
        'views/database_lock_views.xml',
        'views/odoo_log_views.xml',
        'views/dashboard_form.xml',
        'views/dashboard_action.xml',
        'views/menu_views.xml',
        'views/config_views.xml',
        'data/cron_data.xml',
        'data/ir_cron_cleanup.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'odoo_erp_health_monitor/static/src/css/dashboard.css',
        ],
    },

    # Screenshots for Odoo App Store
    'images': [
        'static/description/screenshot_dashboard.png',
        'static/description/screenshot_cron_jobs.png',
        'static/description/screenshot_system_logs.png',
        'static/description/screenshot_server_metrics.png',
        'static/description/screenshot_configuration.png',
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
}
