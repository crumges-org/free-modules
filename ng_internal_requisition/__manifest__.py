{
    "name": "Internal Requisition",
    "summary": "This module allows users to make a request for products from the stock.",
    "description": """
This module allows departments or employees to request products from internal stock.
It supports approval workflows, tracking, and optional integration with purchasing
if stock is unavailable.
    """,
    "author": "Mattobell Ltd.",
    "website": "https://www.mattobellonline.com",
    "category": "Productivity",
    "version": "18.0.1.0.0",
    "depends": [
        "base",
        "hr",
        "product",
        "stock",
        "purchase",
        "purchase_requisition"
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "data/sequence.xml",
        "views/hr_department.xml",
        "views/ir_request.xml",
        "wizards/ir_request.xml",
    ],
    "images": [
        "static/description/banner.png",
        "static/description/icon.png"
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3"
}
