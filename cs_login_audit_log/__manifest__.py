# -*- coding: utf-8 -*-
#
#  ┌────────────────────────────────────────────────────────────────┐
#  │   Developed by: Code Sparks                                    │
#  │   Website: https://code-sparks.odoo.com                        │
#  │   LinkedIn: https://www.linkedin.com/company/codesparks-tech   │
#  │   Description: Login Audit Trail – Track IP, Device & Session  │
#  └────────────────────────────────────────────────────────────────┘
#
#  🔥 Empowering businesses with smart solutions! 💡

{
    "name": "Login Audit Log – Track IP, Device, Session Info",
    "version": "18.0.0.0",
    "summary": "Track user logins with IP address, browser, device type, session ID, etc.",
    "description": """
        Login Audit Log – Track IP, Device, Session Info
        ==================================================
        
        This module adds login auditing to your Odoo system.
        
        Key Features
        ------------
        
        - Record login IP address  
        - Detect browser, OS, and device type  
        - Save session ID and timestamp  
        - Identify admin logins  
        - Track login by company, timezone, language  
        - View logs via backend UI
        
        Ideal for:
        - Security-sensitive organizations
        - Admins needing accountability
        - Compliance & audit purposes

    """,
    "author": "Code Sparks",
    "maintainer": "Code Sparks",
    "support": "info.codesparks@gmail.com",
    "company": "Code Sparks",
    "website": "https://code-sparks.odoo.com",
    "category": "Tools",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/login_audit_views.xml"
    ],
    "images": ["static/description/banner.gif"],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
