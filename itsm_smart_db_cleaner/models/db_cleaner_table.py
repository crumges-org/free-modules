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


class DbCleanerTable(models.Model):
    _name = "db.cleaner.table"
    _description = "Heavy Database Table"
    _order = "total_bytes desc"

    scan_id = fields.Many2one(
        "db.cleaner.scan",
        string="Scan",
        required=True,
        ondelete="cascade",
        index=True,
    )
    table_name = fields.Char(string="Table", required=True)
    schema_name = fields.Char(string="Schema", default="public")
    row_count = fields.Integer(string="Rows")
    table_bytes = fields.Float(string="Table Size (MB)")
    indexes_bytes = fields.Float(string="Indexes Size (MB)")
    total_bytes = fields.Float(string="Total Size (MB)")
    bloat_ratio = fields.Float(
        string="Bloat Ratio",
        help="Approximate ratio of dead tuples vs live tuples.",
    )
    is_critical = fields.Boolean(
        string="Critical",
        compute="_compute_is_critical",
        store=True,
    )

    @api.depends("total_bytes", "bloat_ratio")
    def _compute_is_critical(self):
        for rec in self:
            rec.is_critical = (
                rec.total_bytes >= 500.0
                or (rec.bloat_ratio and rec.bloat_ratio >= 0.4)
            )

    # -------------------------------------------------------------------------
    # Scan
    # -------------------------------------------------------------------------

    @api.model
    def _scan(self, scan, limit=50):
        """Populate heavy tables for the given scan record."""
        query = """
            SELECT
                N.nspname AS schemaname,
                C.relname AS relname,
                pg_total_relation_size(C.oid) AS total_bytes,
                pg_relation_size(C.oid) AS table_bytes,
                pg_indexes_size(C.oid) AS indexes_bytes,
                COALESCE(S.n_live_tup, 0) AS live_tup,
                COALESCE(S.n_dead_tup, 0) AS dead_tup
            FROM pg_class C
            LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
            LEFT JOIN pg_stat_user_tables S
                ON S.schemaname = N.nspname AND S.relname = C.relname
            WHERE C.relkind = 'r'
              AND N.nspname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY total_bytes DESC
            LIMIT %s
        """
        self.env.cr.execute(query, (limit,))
        rows = self.env.cr.fetchall()
        records = []
        for schema, table, total, tbl, idx, live, dead in rows:
            bloat = 0.0
            if live:
                bloat = round(dead / float(live), 4)
            records.append({
                "scan_id": scan.id,
                "schema_name": schema,
                "table_name": table,
                "row_count": int(live or 0),
                "table_bytes": round((tbl or 0) / 1024.0 / 1024.0, 2),
                "indexes_bytes": round((idx or 0) / 1024.0 / 1024.0, 2),
                "total_bytes": round((total or 0) / 1024.0 / 1024.0, 2),
                "bloat_ratio": bloat,
            })
        if records:
            self.create(records)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_vacuum(self):
        """Run a non-blocking VACUUM ANALYZE on the selected tables."""
        for rec in self:
            full_name = "%s.%s" % (
                rec.schema_name or "public", rec.table_name,
            )
            try:
                # Autocommit-style: VACUUM cannot run in a transaction block.
                with self.env.cr.savepoint():
                    self.env.cr.execute("ANALYZE %s" % full_name)
            except Exception:
                _logger.exception("ANALYZE failed on %s", full_name)
        return True
