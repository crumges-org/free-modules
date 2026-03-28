{
    "name": "Maintenance QR Code",
    "version": "18.0.1.0.0",
    "category": "Maintenance",
    "summary": "Generate & Print QR Code Labels for Maintenance Equipment — One-Click Scan, Track & Identify Assets",
    "description": """
        Maintenance QR Code — Smart Equipment Identification for Odoo Maintenance.

        Instantly generate unique QR codes for every maintenance equipment record,
        preview them on the form, and print professional labels in multiple layouts.
        Scan any label to jump directly to the equipment record in Odoo.

        Key Features:
        - Auto-generate unique equipment codes via configurable sequences
        - Live QR code preview directly on the equipment form
        - One-click QR label printing (Dymo, 2x7, 4x7, Custom layouts)
        - Configurable label header color to match your brand
        - Scannable QR codes linking directly to the equipment form in Odoo
        - Seamless integration with the standard Odoo Maintenance module

        Built & maintained by SDLC Corp — https://sdlccorp.com
    """,
    "author": "SDLC Corp",
    "website": "https://sdlccorp.com/",
    "maintainer": "SDLC Corp",
    "license": "LGPL-3",
    "depends": ["maintenance"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "report/maintenance_qr_report.xml",
        "report/maintenance_qr_templates.xml",
        "views/maintenance_equipment_views.xml",
        "views/maintenance_qr_wizard_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "sdlc_maintenance_qr_code/static/src/scss/report_qr_font.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "images":["static/description/banner.jpg"],
}
