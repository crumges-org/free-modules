{
    'name': 'CRM Stage History',
    'summary': 'Track CRM lead stage change history',
    'author': 'Kitworks Systems',
    'website': 'https://github.com/kitworks-systems/addons',
    'category': 'CRM',
    'license': 'LGPL-3',
    'version': '18.0.2.0.0',
    'depends': [
        'crm',
        'generic_mixin',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/crm_stage_history_views.xml',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],
}
