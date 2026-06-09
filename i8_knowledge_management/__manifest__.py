{
    "name": "Knowledge Management",
    'summary': "A fast, organized, collaborative knowledge hub inside Odoo community Edition",
    'description': """
        A fast, organized, collaborative knowledge hub inside Odoo community Edition.
    """,
    'version': "18.0.1.0.0",
    "author": "i8CLOUD Consulting",
    "company": "i8CLOUD Consulting",
    "maintainer": "i8CLOUD Consulting",
    "website": "http://i8cloudconsulting.com",
    "support": "contact@i8cloudconsulting.com",
    "license": "LGPL-3",
    "category": "Knowledge",
    "depends": ["base", "mail", "web", 'hr'],
    "data": [
        "security/ir.model.access.csv",
        "security/knowledge_security.xml",
        "views/knowledge_views.xml",
        "views/knowledge_menus.xml",
        "views/article_public_template.xml",
    ],
    "assets": {
    "web.assets_backend": [
        "i8_knowledge_management/static/src/js/knowledge_split.js",
        "i8_knowledge_management/static/src/xml/knowledge_split_template.xml",
        "i8_knowledge_management/static/src/css/knowledge_split.css",
        ]
    },
    "images": ["static/description/banner.gif"],
    "installable": True,
    "application": True,
    'price': 0.00,
    'currency': 'USD',
}