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

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class DbCleanerScan(models.Model):
    _name = "db.cleaner.scan"
    _description = "Database Cleaner Scan"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    name = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
        default=lambda self: _("New"),
        copy=False,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        readonly=True,
    )
    scan_date = fields.Datetime(
        string="Scan Date",
        readonly=True,
    )
    duration = fields.Float(
        string="Duration (s)",
        readonly=True,
    )
    note = fields.Text(string="Notes")

    # Scan results - relations
    table_ids = fields.One2many(
        "db.cleaner.table",
        "scan_id",
        string="Heavy Tables",
    )
    orphan_ids = fields.One2many(
        "db.cleaner.orphan",
        "scan_id",
        string="Orphan Files",
    )
    cron_failure_ids = fields.One2many(
        "db.cleaner.cron.failure",
        "scan_id",
        string="Cron Failures",
    )
    log_ids = fields.One2many(
        "db.cleaner.log",
        "scan_id",
        string="Error Logs",
    )
    index_ids = fields.One2many(
        "db.cleaner.index",
        "scan_id",
        string="Missing Indexes",
    )
    module_size_ids = fields.One2many(
        "db.cleaner.module.size",
        "scan_id",
        string="Module Sizes",
    )

    # Aggregated counters
    table_count = fields.Integer(
        string="Heavy Tables",
        compute="_compute_counters",
        store=True,
    )
    orphan_count = fields.Integer(
        string="Orphan Files",
        compute="_compute_counters",
        store=True,
    )
    cron_failure_count = fields.Integer(
        string="Cron Failures",
        compute="_compute_counters",
        store=True,
    )
    log_count = fields.Integer(
        string="Error Logs",
        compute="_compute_counters",
        store=True,
    )
    index_count = fields.Integer(
        string="Missing Indexes",
        compute="_compute_counters",
        store=True,
    )
    module_size_count = fields.Integer(
        string="Modules Analyzed",
        compute="_compute_counters",
        store=True,
    )

    # Health
    db_size_mb = fields.Float(
        string="Database Size (MB)",
        readonly=True,
    )
    filestore_size_mb = fields.Float(
        string="Filestore Size (MB)",
        readonly=True,
    )
    orphan_size_mb = fields.Float(
        string="Orphan Size (MB)",
        readonly=True,
    )
    health_score = fields.Integer(
        string="Health Score (/100)",
        compute="_compute_health_score",
        store=True,
    )
    health_status = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("warning", "Warning"),
            ("critical", "Critical"),
        ],
        string="Health Status",
        compute="_compute_health_score",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends(
        "table_ids", "orphan_ids", "cron_failure_ids",
        "log_ids", "index_ids", "module_size_ids",
    )
    def _compute_counters(self):
        for scan in self:
            scan.table_count = len(scan.table_ids)
            scan.orphan_count = len(scan.orphan_ids)
            scan.cron_failure_count = len(scan.cron_failure_ids)
            scan.log_count = len(scan.log_ids)
            scan.index_count = len(scan.index_ids)
            scan.module_size_count = len(scan.module_size_ids)

    @api.depends(
        "orphan_count", "cron_failure_count", "log_count",
        "index_count", "table_count", "orphan_size_mb", "db_size_mb",
    )
    def _compute_health_score(self):
        for scan in self:
            score = 100
            score -= min(20, scan.orphan_count // 50)
            score -= min(20, scan.cron_failure_count * 4)
            score -= min(15, scan.log_count // 20)
            score -= min(15, scan.index_count * 2)
            score -= min(10, max(0, scan.table_count - 5) * 2)
            if scan.db_size_mb and scan.orphan_size_mb:
                ratio = scan.orphan_size_mb / max(scan.db_size_mb, 1.0)
                score -= int(min(20, ratio * 100))
            score = max(0, min(100, score))
            scan.health_score = score
            if score >= 85:
                scan.health_status = "excellent"
            elif score >= 65:
                scan.health_status = "good"
            elif score >= 40:
                scan.health_status = "warning"
            else:
                scan.health_status = "critical"

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "db.cleaner.scan"
                ) or _("New")
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_run_scan(self):
        """Execute a full database scan."""
        self.ensure_one()
        start = fields.Datetime.now()
        self.write({
            "state": "running",
            "scan_date": start,
        })
        # Reset previous results
        self.table_ids.unlink()
        self.orphan_ids.unlink()
        self.cron_failure_ids.unlink()
        self.log_ids.unlink()
        self.index_ids.unlink()
        self.module_size_ids.unlink()

        steps = [
            ("db_metrics", self._scan_db_metrics),
            ("tables", lambda: self.env["db.cleaner.table"]._scan(self)),
            ("orphans", lambda: self.env["db.cleaner.orphan"]._scan(self)),
            ("cron_failures", lambda: self.env["db.cleaner.cron.failure"]._scan(self)),
            ("logs", lambda: self.env["db.cleaner.log"]._scan(self)),
            ("indexes", lambda: self.env["db.cleaner.index"]._scan(self)),
            ("module_sizes", lambda: self.env["db.cleaner.module.size"]._scan(self)),
        ]
        errors = []
        for label, fn in steps:
            try:
                with self.env.cr.savepoint():
                    fn()
            except Exception as exc:
                _logger.exception("Scan step %s failed", label)
                errors.append("%s: %s" % (label, exc))

        end = fields.Datetime.now()
        duration = (end - start).total_seconds()
        note = self.note or ""
        if errors:
            note = (note + "\n" if note else "") + "\n".join(errors)
        self.write({
            "state": "done",
            "duration": duration,
            "note": note,
        })
        self.message_post(body=_(
            "Scan completed in %.2fs. Health score: %s/100. %d step(s) failed."
        ) % (duration, self.health_score, len(errors)))
        return True

    def _scan_db_metrics(self):
        """Compute global database and filestore size metrics."""
        self.ensure_one()
        db_size = 0.0
        try:
            self.env.cr.execute(
                "SELECT pg_database_size(current_database())"
            )
            row = self.env.cr.fetchone()
            if row and row[0]:
                db_size = round(row[0] / 1024.0 / 1024.0, 2)
        except Exception:
            _logger.exception("Could not compute database size")

        filestore_size = 0.0
        try:
            import os
            filestore_path = self.env["ir.attachment"]._filestore()
            if filestore_path and os.path.isdir(filestore_path):
                total = 0
                for dirpath, _dirs, files in os.walk(filestore_path):
                    for f in files:
                        fp = os.path.join(dirpath, f)
                        try:
                            total += os.path.getsize(fp)
                        except OSError:
                            continue
                filestore_size = round(total / 1024.0 / 1024.0, 2)
        except Exception:
            _logger.exception("Could not compute filestore size")

        self.write({
            "db_size_mb": db_size,
            "filestore_size_mb": filestore_size,
        })

    def action_open_cleanup_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Safe Cleanup"),
            "res_model": "db.cleaner.cleanup.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_scan_id": self.id},
        }

    def action_view_tables(self):
        self.ensure_one()
        return self._open_related("db.cleaner.table", "scan_id", _("Heavy Tables"))

    def action_view_orphans(self):
        self.ensure_one()
        return self._open_related("db.cleaner.orphan", "scan_id", _("Orphan Files"))

    def action_view_cron_failures(self):
        self.ensure_one()
        return self._open_related("db.cleaner.cron.failure", "scan_id", _("Cron Failures"))

    def action_view_logs(self):
        self.ensure_one()
        return self._open_related("db.cleaner.log", "scan_id", _("Error Logs"))

    def action_view_indexes(self):
        self.ensure_one()
        return self._open_related("db.cleaner.index", "scan_id", _("Missing Indexes"))

    def action_view_modules(self):
        self.ensure_one()
        return self._open_related("db.cleaner.module.size", "scan_id", _("Module Sizes"))

    def _open_related(self, model, field, title):
        return {
            "type": "ir.actions.act_window",
            "name": title,
            "res_model": model,
            "view_mode": "list,form",
            "domain": [(field, "=", self.id)],
            "context": {"default_%s" % field: self.id},
        }

    @api.model
    def cron_periodic_scan(self):
        """Cron job: run a periodic scan and store the result."""
        scan = self.create({"note": _("Automated periodic scan")})
        scan.action_run_scan()
        return True
