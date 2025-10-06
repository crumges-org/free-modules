# Powered by Sensible Consulting Services
# -*- coding: utf-8 -*-
# © 2025 Sensible Consulting Services (<https://sensiblecs.com/>)
{
    'name': 'Dynamic Portal | Dynamic Customer Portal | Dynamic User Portal | Dynamic Vendor Portal',
    'version': '18.0.1.0',
    'summary': '''Dynamic portals offer customizable, user-specific experiences with no coding required, 
        providing personalized access and role-based permissions.''',
    'description': '''Dynamic Portal
        This module enables the creation of a customizable and configurable menu within the customer portal.
        You can apply a domain to filter and refine the records displayed.
        You can access and view the detailed information of each individual record.
        Dynamic Portal Management
        No-Code Dynamic Portal
        Customizable Portal Interface
        Personalized Portal Experience
        User-Specific Portal Access
        Dynamic User Portal
        Flexible Portal Solutions
        Portal Customization without Code
        Dynamic Portal Design
        Portal Navigation Customization
        Adaptive Portal Features
        Interactive Portal Design
        Easy Portal Configuration
        Portal Access Control
        Role-Based Portal Customization
        Drag-and-Drop Portal Builder
        Scalable Dynamic Portal
        Personalized User Interface for Portals
    ''',
    'category': 'Extra Tools',
    'author': 'Sensible Consulting Services',
    'website': 'https://sensiblecs.com',
    'license': 'AGPL-3',
    'depends': ['portal'],
    'data': [
        'security/ir.model.access.csv',

        'views/sbl_dynamic_portal_view.xml',
        'views/sbl_portal_template.xml',
        'views/sbl_menu_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False
}
