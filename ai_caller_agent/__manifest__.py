

{
    "name": "AI Caller Agent for Odoo",
    "summary": "Smart Inbound Handling + Automated Outbound Campaigns. Automate the Entire Calling Workflow From A-to-Z — Same Day Activation",
    "description": """
AI Caller Agent for Odoo brings full inbound and outbound AI-powered calling directly into your Odoo CRM.

Run automated outbound campaigns, receive inbound calls with AI, tag and route leads, schedule appointments, and trigger workflows — all through your AI calling cloud service, connected instantly through this module.

This module is lightweight, easy to install, and gives you same-day activation of AI-driven calling inside Odoo.
    """,
    "category": "CRM",
    "author": "Mark Khan",
    "website": "https://ippbx.com",
    "support": "mark.k@ippbx.com",
    "price": 00.00,
    "version": "18.0.1.0.0",
    "currency": "USD",
    "depends": ["crm"],
    "data": [
        "security/ir.model.access.csv",
        "views/automation_campaign_views.xml",
        "data/automation_cron.xml",
    ],
    
    "images": [
        "static/description/banner.gif",
        "static/description/icon.png",
    ],
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
