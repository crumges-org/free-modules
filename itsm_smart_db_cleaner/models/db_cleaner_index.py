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

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DbCleanerIndex(models.Model):
    _name = "db.cleaner.index"
    _description = "Missing PostgreSQL Index Suggestion"
    _order = "row_count desc, table_name"

    scan_id = fields.Many2one(
        "db.cleaner.scan",
        string="Scan",
        required=True,
        ondelete="cascade",
        index=True,
    )
    table_name = fields.Char(string="Table", required=True)
    column_name = fields.Char(string="Column", required=True)
    field_type = fields.Char(string="Field Type")
    row_count = fields.Integer(string="Rows")
    suggestion = fields.Selection(
        [
            ("foreign_key", "Foreign key without index"),
            ("active", "active flag without index"),
            ("company", "company_id without index"),
            ("seq_scan", "Frequent sequential scan"),
        ],
        string="Suggestion",
    )
    sql_command = fields.Char(
        string="Suggested SQL",
        help="SQL command to create the suggested index.",
    )
    applied = fields.Boolean(string="Applied", default=False)

    # -------------------------------------------------------------------------
    # Scan
    # -------------------------------------------------------------------------

    @api.model
    def _scan(self, scan):
        """Detect probable missing indexes on heavy tables."""
        # We focus on tables with > 10k rows (where indexes really matter).
        try:
            self.env.cr.execute("""
                SELECT relname, n_live_tup
                FROM pg_stat_user_tables
                WHERE n_live_tup > 10000
                ORDER BY n_live_tup DESC
            """)
            big_tables = {r[0]: int(r[1] or 0) for r in self.env.cr.fetchall()}
        except Exception:
            _logger.exception("Could not query pg_stat_user_tables")
            big_tables = {}

        if not big_tables:
            return

        records = []
        # Foreign keys without index
        try:
            self.env.cr.execute("""
                SELECT c.conrelid::regclass::text AS table_name,
                       a.attname AS column_name
                FROM pg_constraint c
                JOIN pg_attribute a
                    ON a.attrelid = c.conrelid
                   AND a.attnum = ANY(c.conkey)
                WHERE c.contype = 'f'
                  AND NOT EXISTS (
                      SELECT 1 FROM pg_index i
                      WHERE i.indrelid = c.conrelid
                        AND a.attnum = ANY(i.indkey)
                  )
            """)
            for table, column in self.env.cr.fetchall():
                short = table.split(".")[-1]
                if short not in big_tables:
                    continue
                records.append({
                    "scan_id": scan.id,
                    "table_name": short,
                    "column_name": column,
                    "field_type": "foreign_key",
                    "row_count": big_tables[short],
                    "suggestion": "foreign_key",
                    "sql_command": (
                        "CREATE INDEX CONCURRENTLY ON %s (%s);"
                        % (short, column)
                    ),
                })
        except Exception:
            _logger.exception("Could not analyse foreign keys")

        # active / company_id columns without index
        for col_name, suggestion in (
            ("company_id", "company"),
            ("active", "active"),
        ):
            try:
                self.env.cr.execute("""
                    SELECT c.table_name
                    FROM information_schema.columns c
                    WHERE c.column_name = %s
                      AND c.table_schema = 'public'
                      AND NOT EXISTS (
                          SELECT 1 FROM pg_indexes p
                          WHERE p.tablename = c.table_name
                            AND p.indexdef LIKE '%%(' || %s || ')%%'
                      )
                """, (col_name, col_name))
                for (table,) in self.env.cr.fetchall():
                    if table not in big_tables:
                        continue
                    records.append({
                        "scan_id": scan.id,
                        "table_name": table,
                        "column_name": col_name,
                        "field_type": col_name,
                        "row_count": big_tables[table],
                        "suggestion": suggestion,
                        "sql_command": (
                            "CREATE INDEX CONCURRENTLY ON %s (%s);"
                            % (table, col_name)
                        ),
                    })
            except Exception:
                _logger.exception("Could not analyse %s columns", col_name)

        # Frequent sequential scans
        try:
            self.env.cr.execute("""
                SELECT relname, seq_scan, idx_scan, n_live_tup
                FROM pg_stat_user_tables
                WHERE n_live_tup > 50000
                  AND seq_scan > 1000
                  AND (idx_scan IS NULL OR seq_scan > idx_scan * 5)
                ORDER BY seq_scan DESC
                LIMIT 20
            """)
            for table, seq, idx, live in self.env.cr.fetchall():
                records.append({
                    "scan_id": scan.id,
                    "table_name": table,
                    "column_name": "(unknown)",
                    "field_type": "stat",
                    "row_count": int(live or 0),
                    "suggestion": "seq_scan",
                    "sql_command": (
                        "-- Review %s: %s seq scans vs %s index scans"
                        % (table, seq, idx or 0)
                    ),
                })
        except Exception:
            _logger.exception("Could not analyse seq scans")

        if records:
            self.create(records)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_apply_index(self):
        """Run the suggested CREATE INDEX command."""
        for rec in self:
            if not rec.sql_command or not rec.sql_command.upper().startswith("CREATE"):
                continue
            try:
                # CONCURRENTLY cannot run inside a transaction block, so we
                # fall back to a regular CREATE INDEX from the wizard.
                cmd = rec.sql_command.replace("CONCURRENTLY ", "")
                self.env.cr.execute(cmd)
                rec.applied = True
            except Exception as exc:
                _logger.warning("Could not apply %s: %s", rec.sql_command, exc)
        return True
