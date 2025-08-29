# -*- coding: utf-8 -*-
# pyright: reportUnusedExpression=false
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo WooCommerce Automation',
    'summary': """
        Comprehensive WooCommerce integration for Odoo 18.
        Automate product synchronization, order management, inventory updates,
        and customer data synchronization between Odoo and WooCommerce.
    """,
    'description': """
        Odoo WooCommerce Automation Module
        
        Features:
        - Bidirectional product synchronization
        - Automatic order import and status updates
        - Real-time inventory synchronization
        - Customer data synchronization
        - Advanced mapping and configuration
        - Automated workflows and scheduling
        - Comprehensive reporting and analytics
        - Multi-store support
        - Error handling and logging
        - REST API integration
        
        Compatibility:
        ✅ Odoo Community Edition 18.0+
        ✅ Odoo Enterprise Edition 18.0+
        ✅ On-Premise Installations
        ✅ Odoo.sh Deployments
        ❌ Odoo Online (not supported)
        
        Note: Invoice digitization features require Enterprise Edition.
        Core WooCommerce functionality works perfectly with Community Edition.
        
        Developed by ECOSIRE (PRIVATE) LIMITED
        Website: https://www.ecosire.com/
        Email: info@ecosire.com
        Official Number: 0923130168262
    """,
    'category': 'Sales',
    'version': '18.0.1.0.0',
    'author': 'ECOSIRE (PRIVATE) LIMITED',
    'website': 'https://www.ecosire.com/',
    'support': 'info@ecosire.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'product',
        'stock',
        'account',
        'contacts',
        'mail',
        'web',
    ],
    # Optional dependencies - module works with or without these
    'optional_depends': [
        'account_invoice_extract',  # Enterprise module - optional for Community Edition
    ],
    'data': [
        # Security
        'security/woocommerce_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/woocommerce_data.xml',
        'data/cron_data.xml',
        
        # Views
        'views/woocommerce_configuration_views.xml',
        'views/woocommerce_sync_log_views.xml',
        'views/woocommerce_dashboard_views.xml',
        
        # Wizards (must be loaded before menu)
        'wizard/woocommerce_import_wizard_views.xml',
        'wizard/woocommerce_export_wizard_views.xml',
        'wizard/woocommerce_mapping_wizard_views.xml',
        'wizard/woocommerce_test_connection_wizard_views.xml',
        
        # Reports (must be loaded before menu)
        'reports/woocommerce_sync_report_views.xml',
        
        # Menu (must be loaded after wizards and reports)
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/woocommerce_demo_data.xml',
    ],
    'external_dependencies': {
        'python': [
            'requests>=2.25.1',
            'woocommerce>=3.0.0',
        ],
    },
    'assets': {
        'web.assets_backend': [
            'odoo_woocommerce_automation/static/src/css/woocommerce.css',
            'odoo_woocommerce_automation/static/src/js/woocommerce_dashboard.js',
            'odoo_woocommerce_automation/static/src/js/woocommerce_sync.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1,
    'price': 0.0,
    'currency': 'USD',
    # Compatibility information
    'version': '18.0.1.0.0',
    'odoo_version': '18.0',
    'compatibility': {
        'community': True,
        'enterprise': True,
        'online': False,  # Not compatible with Odoo Online
    },
    'images': [
        'static/description/thumbnail.png',
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    # Post-installation hook to ensure proper module setup
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
} 
