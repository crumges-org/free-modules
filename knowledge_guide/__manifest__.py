# -*- coding: utf-8 -*-
{
    'name': 'Knowledge Guide',
    'version': '18.0.1.1.0',
    'category': 'Productivity',
    'summary': 'Build navigable user guides and publish them on the web with secure tokenized links.',
    'description': """
Knowledge Guide
===============

Build navigable user documentation for your Odoo modules and publish it on
the web with secure tokenized links.

Each Odoo module can contribute its own pages through XML data files,
making this the perfect base layer for product documentation, internal
training material, or customer-facing user manuals.

Key features
------------
* Documentation pages organized by collapsible categories
* Books that group multiple pages and can be published online via a secure
  tokenized URL (no authentication required for end users)
* Original content shipped by modules + per-page custom override editable
  by the admin (the original content stays untouched)
* HTML source viewer wizard (admins can inspect the raw page source)
* Real-time search with automatic highlight in titles and content
* User-group filtering to show or hide pages based on permissions
* Standalone web template (clean reading experience without the Odoo backend)
* Click tracking on published guides via Odoo's native link.tracker
* Email wizard to send the guide link to multiple recipients with a
  customizable subject and body
* Modern OWL framework client action for the backend interface
* Modular architecture: any other module can ship its own documentation
  pages via a simple XML data file

Use cases
---------
* End-user documentation shipped with your custom Odoo modules
* Customer-facing knowledge bases published on a public URL
* Internal team training material with group-based access control
* Quick onboarding guides sent by email to new users

How to extend
-------------
Any module can contribute its own pages by depending on `knowledge_guide`
and shipping an XML data file::

    <record id="page_my_module" model="knowledge.guide.page">
        <field name="name">My Feature</field>
        <field name="category">My Module</field>
        <field name="sequence">10</field>
        <field name="icon">fa-cog</field>
        <field name="module_source">my_module</field>
        <field name="content_html"><![CDATA[
            <h1>My Feature</h1>
            <p>Description...</p>
        ]]></field>
    </record>

Administrators can later override the page content without touching the
original by filling the dedicated "Custom content" field on the page form.

    """,
    'author': 'Kameos',
    'website': 'https://kameos.be',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'link_tracker',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/knowledge_guide_book_create_wizard_views.xml',
        'views/knowledge_guide_book_views.xml',
        'views/knowledge_guide_page_views.xml',
        'views/knowledge_guide_menu.xml',
        'views/guide_public_templates.xml',
        'wizard/knowledge_guide_send_wizard_views.xml',
        'wizard/knowledge_guide_view_source_wizard_views.xml',
        'data/knowledge_guide_data.xml',
        'data/email_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'knowledge_guide/static/src/css/knowledge_guide.css',
            'knowledge_guide/static/src/js/knowledge_guide.js',
            'knowledge_guide/static/src/xml/knowledge_guide.xml',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
