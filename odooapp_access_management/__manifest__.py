{
    'name': 'Access Management - Advance User Access Rights & Restrictions',
    'version': '18.0.1.3.1',
    'category': 'Extra Tools',
    'summary': 'Odoo Access Management: user access rights and role based access control for menus,'
               ' models, fields, records, buttons, search and chatter. Restrict access per user, group'
               ' or profile, enforced server-side with an access rights dashboard, access map and'
               ' rule explainer.',
    'description': """
Access Management for Odoo
==========================

Advance Access Management is one place to control what every user can see and do:
Odoo access rights, user access control and role based access management for
menus, models, fields, records, buttons, tabs, search and chatter.

Odoo Access Rights Management
-----------------------------

* Access Profiles - reusable access management policies you assign to users and
  groups, or block in one click.
* Menu access rights - hide any menu or sub-menu per user, group or profile.
* Model access rights - restrict create, read, write and delete.
* Field access rights - hide a field, make it read-only, required, or mask it.
* Record level access rights - domain restrictions, own-records-only and
  hierarchy-aware rules.
* Button, tab and search access rights, plus chatter access rights.
* Global access restrictions - export, import, print, duplicate, archive and the
  developer mode.

Secure User Access in Odoo
--------------------------

* Enforced server-side, so access restrictions survive XML-RPC and the JSON API -
  they are not merely hidden in the user interface.
* Sensitive data masking, time and timezone based access windows, expiring rules.
* Password expiry, forced logout, audited impersonation and login activity.
* Admin protection - the access management rules cannot lock you out.

Access Management Tools
-----------------------

* Access rights dashboard with a model heatmap and charts.
* Access Map - an interactive security explorer for groups, users and models.
* Access Explainer - tells you *which rule* caused an effect, native Odoo ACLs
  and record rules included.
* Guided setup wizard, 31 ready-made access control presets, and a groups to
  Excel export.
* Version-portable JSON import/export of access rules with a dry-run diff.
* Translated into English, German, French, Spanish, Simplified Chinese and Arabic.
""",
    'author': 'Roshan',
    'website': 'https://github.com/roshank8s/',
    'license': 'OPL-1',
    'depends': ['base', 'web', 'mail', 'base_setup'],
    'external_dependencies': {'python': ['xlsxwriter']},
    'data': [
        'security/aam_groups.xml',
        'security/ir.model.access.csv',
        'views/aam_menus.xml',
        'views/aam_dashboard_views.xml',
        'views/aam_profile_views.xml',
        'views/aam_rule_views.xml',
        'views/aam_audit_log_views.xml',
        'views/aam_explain_views.xml',
        'views/aam_rules_io_views.xml',
        'views/aam_preset_views.xml',
        'views/aam_rule_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/aam_groups_export_views.xml',
        'views/res_users_views.xml',
        'data/mail_template_data.xml',
        'data/ir_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Tokens and shared mixins first. The wildcard below resolves
            # alphabetically (access_map < dashboard < scss), and Odoo compiles a
            # bundle's SCSS as one document - a forward mixin reference would
            # fail the whole backend bundle, not just this module.
            'odooapp_access_management/static/src/scss/aam_tokens.scss',
            'odooapp_access_management/static/src/**/*.js',
            'odooapp_access_management/static/src/**/*.xml',
            'odooapp_access_management/static/src/**/*.scss',
            # Dark tokens must stay out of the light stylesheet; the glob above
            # would otherwise swallow them.
            ('remove', 'odooapp_access_management/static/src/**/*.dark.scss'),
        ],
        # Odoo 19 has no dark-mode class - it serves a separate compiled bundle,
        # chosen server-side from the color_scheme cookie. Declared in web, so
        # contributing to it is safe on Community too (where it is never served).
        'web.assets_web_dark': [
            'odooapp_access_management/static/src/**/*.dark.scss',
        ],
        'web.assets_tests': [
            'odooapp_access_management/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
