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
from collections import defaultdict

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DbCleanerModuleSize(models.Model):
    _name = "db.cleaner.module.size"
    _description = "Module Storage Footprint"
    _order = "total_bytes desc"

    scan_id = fields.Many2one(
        "db.cleaner.scan",
        string="Scan",
        required=True,
        ondelete="cascade",
        index=True,
    )
    module_id = fields.Many2one(
        "ir.module.module",
        string="Module",
        ondelete="set null",
    )
    module_name = fields.Char(string="Technical Name", required=True)
    shortdesc = fields.Char(string="Display Name")
    state = fields.Char(string="State")
    table_count = fields.Integer(string="Tables")
    record_count = fields.Integer(string="Records")
    total_bytes = fields.Float(string="Total Size (MB)")

    # -------------------------------------------------------------------------
    # Scan
    # -------------------------------------------------------------------------

    @api.model
    def _scan(self, scan):
        """Aggregate the storage footprint of installed modules."""
        Module = self.env["ir.module.module"].sudo()
        modules = Module.search([("state", "=", "installed")])

        # Build mapping: model -> module
        model_to_module = {}
        try:
            self.env.cr.execute("""
                SELECT d.module, m.model
                FROM ir_model m
                JOIN ir_model_data d
                    ON d.res_id = m.id AND d.model = 'ir.model'
            """)
            for module_name, model_name in self.env.cr.fetchall():
                # Use the first declaring module as canonical owner.
                model_to_module.setdefault(model_name, module_name)
        except Exception:
            _logger.exception("Could not map models to modules")

        # Get all table sizes.
        try:
            self.env.cr.execute("""
                SELECT C.relname,
                       pg_total_relation_size(C.oid) AS bytes,
                       COALESCE(S.n_live_tup, 0) AS rows
                FROM pg_class C
                LEFT JOIN pg_namespace N ON N.oid = C.relnamespace
                LEFT JOIN pg_stat_user_tables S ON S.relname = C.relname
                WHERE C.relkind = 'r'
                  AND N.nspname = 'public'
            """)
            table_info = {
                row[0]: {"bytes": int(row[1] or 0), "rows": int(row[2] or 0)}
                for row in self.env.cr.fetchall()
            }
        except Exception:
            _logger.exception("Could not list table sizes")
            table_info = {}

        # Aggregate per module
        per_module = defaultdict(lambda: {"bytes": 0, "rows": 0, "tables": 0})
        for model_name, module_name in model_to_module.items():
            table = model_name.replace(".", "_")
            info = table_info.get(table)
            if not info:
                continue
            agg = per_module[module_name]
            agg["bytes"] += info["bytes"]
            agg["rows"] += info["rows"]
            agg["tables"] += 1

        records = []
        for module in modules:
            agg = per_module.get(module.name)
            if not agg or not agg["tables"]:
                continue
            records.append({
                "scan_id": scan.id,
                "module_id": module.id,
                "module_name": module.name,
                "shortdesc": module.shortdesc,
                "state": module.state,
                "table_count": agg["tables"],
                "record_count": agg["rows"],
                "total_bytes": round(agg["bytes"] / 1024.0 / 1024.0, 2),
            })

        # Sort by size and only keep the top 100 to avoid clutter.
        records.sort(key=lambda r: r["total_bytes"], reverse=True)
        if records:
            self.create(records[:100])
