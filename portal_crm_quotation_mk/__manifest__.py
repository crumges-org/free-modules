# -*- coding: utf-8 -*-
{
    'name': 'Portal CRM to Quotation',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Complete CRM and Quotation Management from Portal with Dashboard',
    'description': """
Portal CRM to Quotation
Transform your sales workflow by allowing employees to manage CRM Leads/Opportunities 
and create Sales Quotations directly from the Portal interface.

🎯 KEY FEATURES

📊 COMPREHENSIVE DASHBOARD
• Beautiful dashboard with CRM statistics and KPIs
• Visual charts for leads, opportunities, and quotations
• Quick access to all CRM functions
• Real-time activity tracking
• Revenue and conversion metrics

📋 CRM LEAD/OPPORTUNITY MANAGEMENT
• Create, Edit, and Delete leads/opportunities from portal
• List view with activity indicators (Green = Due, Red = Overdue)
• Clickable dynamic stage bar for easy progression
• Win/Lost buttons for quick opportunity closure
• Full edit mode with all lead fields
• Smart filtering and search capabilities

📅 ACTIVITY MANAGEMENT
• Schedule activities with popup form
• Log internal notes directly from portal
• View activities in list view with color coding
• Activity deadline tracking
• Overdue activity alerts

💼 QUOTATION MANAGEMENT
• Create quotations directly from leads/opportunities
• View related quotations with smart button
• Edit quotations: Add, Edit, Delete lines
• Send quotations by email with templates
• View email logs in chatter
• Full quotation management from portal

✨ ADDITIONAL FEATURES
• Modern, responsive design
• Beautiful CSS styling
• AJAX operations for seamless updates
• Modal popups for forms
• Smart buttons for related records
• Chatter integration
• Mobile-friendly interface

🔒 SECURITY
• Portal users only see their assigned records
• Proper access rights validation
• Secure data operations
• CSRF protection
    """,
    'author': 'My Khan',
    'website': 'https://www.odoo.com',
    'support': 'mykhan440@outlook.com',
    'images': ['static/description/icon.png'],
    'depends': [
        'base',
        'portal',
        'crm',
        'sale_management',
        'mail',
        'calendar',
        'contacts',
        'account',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/portal_crm_security.xml',
        'views/portal_templates.xml',
        'views/crm_lead_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'portal_crm_quotation_mk/static/src/css/portal_crm_dashboard.css',
            'portal_crm_quotation_mk/static/src/css/portal_crm_forms.css',
            'portal_crm_quotation_mk/static/src/js/portal_crm_dashboard.js',
            'portal_crm_quotation_mk/static/src/js/portal_crm_forms.js',
            'portal_crm_quotation_mk/static/src/js/portal_crm_activities.js',
            'portal_crm_quotation_mk/static/src/js/portal_sale_order.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
