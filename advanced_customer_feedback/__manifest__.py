{
    'name': 'Advanced Customer Feedback Management',
    'version': '18.0.1.0.0',
    'category': 'Customer Relationship Management',
    'summary': 'Collect and manage customer feedback and suggestions',
    'description': """
Customer Feedback and Suggestion Box
====================================

This module provides a comprehensive system for collecting and managing customer feedback, allowing businesses to:
- Create dedicated portal forms for customer feedback submission
- Categorize feedback by type (product suggestion, website issue, general comment)
- Internal dashboard for reviewing and managing feedback
- Link feedback to relevant Odoo records (products, sales orders)
- Generate reports on feedback trends and insights

Features:
- Customer portal feedback submission
- Feedback categorization and tagging
- Internal feedback management dashboard
- Integration with existing Odoo records
- Feedback analytics and reporting
- Email notifications for new feedback
- Customer satisfaction tracking

Compatible with Odoo 17 and 18 Community Edition.
    """,
    'author': 'Samy_Sensei',
    'website': 'https://linktr.ee/Prof.M.Samy',
    'depends': ['base', 'mail', 'portal', 'website'],
    'data': [
        'security/customer_feedback_security.xml',
        'security/ir.model.access.csv',
        'data/feedback_data.xml',
        'views/customer_feedback_views.xml',
        'views/feedback_category_views.xml',
        'views/feedback_template_views.xml',
        'views/feedback_template_field_views.xml',
        'views/feedback_tag_views.xml',
        'views/menu_views.xml',
        'report/feedback_report.xml',
        'templates/feedback_dashboard_template.xml',
        'templates/feedback_portal_template.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
