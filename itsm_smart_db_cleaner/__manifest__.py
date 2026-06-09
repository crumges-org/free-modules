# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2026 IT-Solutions.mg. All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Smart Database Cleaner",
    "version": "18.0.1.0.0",
    "category": "Administration",
    "summary": "Scan, analyse and safely clean your Odoo database with health dashboard",
    "description": """
        Smart Database Cleaner for Odoo
        ===============================

        A free, all-in-one tool to keep your Odoo database lean and healthy:

        - Full database scan with health dashboard
        - Detection of heavy tables and bloated models
        - Orphan filestore detection (attachments without records)
        - Cron job failures monitoring
        - Error logs analysis
        - Safe cleanup actions with simulation (dry-run) mode
        - Backup reminder with configurable frequency
        - Missing PostgreSQL indexes detection
        - Module size analysis (records and storage)
        - One-click safe cleanup with detailed preview

        Designed for system administrators who want a clear picture
        of what is slowing down their database, with safe and reversible
        cleanup options.
    """,
    "author": "IT-Solutions.mg",
    "depends": ["base", "mail"],
    "data": [
        "security/db_cleaner_security.xml",
        "security/ir.model.access.csv",
        "data/db_cleaner_data.xml",
        "data/db_cleaner_cron.xml",
        "wizard/db_cleaner_cleanup_wizard_views.xml",
        "views/db_cleaner_scan_views.xml",
        "views/db_cleaner_table_views.xml",
        "views/db_cleaner_orphan_views.xml",
        "views/db_cleaner_cron_failure_views.xml",
        "views/db_cleaner_log_views.xml",
        "views/db_cleaner_index_views.xml",
        "views/db_cleaner_module_size_views.xml",
        "views/db_cleaner_backup_reminder_views.xml",
        "views/db_cleaner_dashboard_views.xml",
        "views/db_cleaner_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "itsm_smart_db_cleaner/static/src/scss/db_cleaner.scss",
        ],
    },
    "images": [
        'static/images/main_screenshot.png',
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
