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

import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DbCleanerLog(models.Model):
    _name = "db.cleaner.log"
    _description = "Database Cleaner Log Entry"
    _order = "occurrences desc"

    scan_id = fields.Many2one(
        "db.cleaner.scan",
        string="Scan",
        required=True,
        ondelete="cascade",
        index=True,
    )
    log_type = fields.Selection(
        [
            ("ir_logging", "ir.logging"),
            ("mail_failure", "Mail failure"),
            ("constraint", "DB constraint"),
        ],
        string="Type",
        default="ir_logging",
    )
    level = fields.Char(string="Level")
    name = fields.Char(string="Source")
    message = fields.Text(string="Message")
    occurrences = fields.Integer(string="Occurrences", default=1)
    last_occurrence = fields.Datetime(string="Last Seen")

    # -------------------------------------------------------------------------
    # Scan
    # -------------------------------------------------------------------------

    @api.model
    def _scan(self, scan, days=7, limit=100):
        """Aggregate recent error logs from ir.logging."""
        if "ir.logging" not in self.env:
            return
        cutoff = fields.Datetime.now() - timedelta(days=days)
        try:
            self.env.cr.execute("""
                SELECT level, name,
                       COUNT(*) AS occ,
                       MAX(create_date) AS last_dt,
                       MIN(message) AS sample
                FROM ir_logging
                WHERE level IN ('ERROR', 'CRITICAL', 'WARNING')
                  AND create_date >= %s
                GROUP BY level, name
                ORDER BY occ DESC
                LIMIT %s
            """, (cutoff, limit))
            rows = self.env.cr.fetchall()
        except Exception:
            _logger.exception("Could not query ir_logging")
            return

        records = []
        for level, name, occ, last_dt, sample in rows:
            records.append({
                "scan_id": scan.id,
                "log_type": "ir_logging",
                "level": level,
                "name": name,
                "message": (sample or "")[:1000],
                "occurrences": occ,
                "last_occurrence": last_dt,
            })

        # Mail failures
        try:
            Mail = self.env["mail.mail"].sudo()
            failures = Mail.search_count([("state", "=", "exception")])
            if failures:
                records.append({
                    "scan_id": scan.id,
                    "log_type": "mail_failure",
                    "level": "ERROR",
                    "name": "mail.mail",
                    "message": "%s mail messages stuck in exception state." % failures,
                    "occurrences": failures,
                    "last_occurrence": fields.Datetime.now(),
                })
        except Exception:
            _logger.exception("Could not query mail failures")

        if records:
            self.create(records)
