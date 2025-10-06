# Powered by Sensible Consulting Services
# -*- coding: utf-8 -*-
# © 2025 Sensible Consulting Services (<https://sensiblecs.com/>)
{
    'name': 'Sensible Dynamic Portal Dashboard',
    'version': '18.0.1.0',
    'summary': 'Sensible Dynamic Portal Dashboard',
    'description': '''
    Transform Your Business Data Into Visual Stories
    ================================================
    
    🚀 **Advanced Dashboard Solution for Customer Portals**
    
    Empower your customers with interactive KPI tracking, stunning Chart.js visualizations, 
    and intuitive portal navigation. This comprehensive dashboard extension transforms raw 
    business data into compelling visual insights.
    
    ✨ **Key Features:**
    • 📊 5 Interactive Chart Types (Pie, Bar, Line, Radar, Doughnut)
    • 🎯 Real-time KPI Tracking with Custom Colors
    • 📱 Mobile-First Responsive Design
    • 🔒 Enterprise-Grade Security & Access Controls
    • 🎨 Fully Customizable Themes & Brand Colors
    • ⚡ One-Click Chart Type Switching
    • 🎛️ Smart Dynamic Navigation Menus
    
    🎁 **Perfect For:**
    Customer portals, executive dashboards, performance monitoring, 
    data analytics, business intelligence, and multi-tenant applications.
    ''',
    'category': 'Extra Tools',
    'author': 'Sensible Consulting Services',
    'website': 'https://sensiblecs.com',
    'license': 'AGPL-3',
    'depends': ['sensible_dynamic_portal'],
    'data': [
        'security/ir.model.access.csv',

        'views/sbl_dynamic_portal_view.xml',
        'views/sbl_portal_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sensible_dynamic_portal_dashboard/static/src/js/sbl_portal.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False
}
