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

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class DbCleanerCleanupWizard(models.TransientModel):
    _name = "db.cleaner.cleanup.wizard"
    _description = "Safe Cleanup Wizard"

    scan_id = fields.Many2one(
        "db.cleaner.scan",
        string="Scan",
        required=True,
    )

    # Mode
    simulation = fields.Boolean(
        string="Simulation Mode",
        default=True,
        help="When enabled, no record is actually deleted. "
             "The wizard only reports what would be removed.",
    )

    # What to clean
    clean_orphan_attachments = fields.Boolean(
        string="Orphan Attachments",
        default=True,
    )
    clean_old_logs = fields.Boolean(
        string="Old ir.logging Entries",
        default=True,
    )
    log_retention_days = fields.Integer(
        string="Keep logs for (days)",
        default=30,
    )
    clean_old_mail = fields.Boolean(
        string="Sent Mail Older Than",
        default=False,
    )
    mail_retention_days = fields.Integer(
        string="Keep mails for (days)",
        default=180,
    )
    clean_failed_mails = fields.Boolean(
        string="Failed Mail Queue",
        default=False,
    )
    vacuum_analyze = fields.Boolean(
        string="Run ANALYZE",
        default=True,
    )

    # Output
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
        ],
        default="draft",
        readonly=True,
    )
    summary = fields.Html(
        string="Summary",
        readonly=True,
    )
    orphan_count = fields.Integer(string="Orphan Attachments", readonly=True)
    orphan_size_mb = fields.Float(string="Orphan Size (MB)", readonly=True)
    log_count = fields.Integer(string="Old Logs", readonly=True)
    mail_count = fields.Integer(string="Old Mails", readonly=True)
    failed_mail_count = fields.Integer(string="Failed Mails", readonly=True)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _gather_orphan_attachments(self):
        self.ensure_one()
        if not self.scan_id:
            return self.env["ir.attachment"]
        ids = self.scan_id.orphan_ids.mapped("attachment_id").ids
        return self.env["ir.attachment"].sudo().browse(ids).exists()

    def _gather_old_logs(self):
        self.ensure_one()
        if "ir.logging" not in self.env:
            return self.env["ir.logging"] if "ir.logging" in self.env else None
        cutoff = fields.Datetime.now() - timedelta(days=self.log_retention_days)
        return self.env["ir.logging"].sudo().search([
            ("create_date", "<", cutoff),
        ])

    def _gather_old_mails(self):
        self.ensure_one()
        cutoff = fields.Datetime.now() - timedelta(days=self.mail_retention_days)
        return self.env["mail.mail"].sudo().search([
            ("state", "=", "sent"),
            ("create_date", "<", cutoff),
        ])

    def _gather_failed_mails(self):
        self.ensure_one()
        return self.env["mail.mail"].sudo().search([
            ("state", "=", "exception"),
        ])

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_preview(self):
        """Show what would be cleaned without performing any change."""
        self.ensure_one()
        return self._execute(simulate_override=True)

    def action_execute(self):
        """Perform the cleanup according to the simulation flag."""
        self.ensure_one()
        return self._execute(simulate_override=None)

    def _execute(self, simulate_override=None):
        self.ensure_one()
        is_sim = simulate_override if simulate_override is not None else self.simulation

        lines = []
        orphan_count = orphan_size = log_count = mail_count = failed_mail_count = 0

        if self.clean_orphan_attachments:
            attachments = self._gather_orphan_attachments()
            orphan_count = len(attachments)
            orphan_size = sum(attachments.mapped("file_size") or [0]) / 1024.0 / 1024.0
            if not is_sim and attachments:
                try:
                    attachments.unlink()
                except Exception as exc:
                    _logger.warning("Could not unlink some orphans: %s", exc)
            lines.append(self._format_line(
                "Orphan attachments",
                orphan_count,
                "%.2f MB" % orphan_size,
                is_sim,
            ))

        if self.clean_old_logs and "ir.logging" in self.env:
            logs = self._gather_old_logs()
            log_count = len(logs) if logs else 0
            if not is_sim and logs:
                try:
                    logs.unlink()
                except Exception as exc:
                    _logger.warning("Could not delete logs: %s", exc)
            lines.append(self._format_line(
                "Old ir.logging entries (>%sd)" % self.log_retention_days,
                log_count, "", is_sim,
            ))

        if self.clean_old_mail:
            mails = self._gather_old_mails()
            mail_count = len(mails)
            if not is_sim and mails:
                try:
                    mails.unlink()
                except Exception as exc:
                    _logger.warning("Could not delete mails: %s", exc)
            lines.append(self._format_line(
                "Sent mails (>%sd)" % self.mail_retention_days,
                mail_count, "", is_sim,
            ))

        if self.clean_failed_mails:
            mails = self._gather_failed_mails()
            failed_mail_count = len(mails)
            if not is_sim and mails:
                try:
                    mails.unlink()
                except Exception as exc:
                    _logger.warning("Could not delete failed mails: %s", exc)
            lines.append(self._format_line(
                "Failed mails", failed_mail_count, "", is_sim,
            ))

        if self.vacuum_analyze and not is_sim:
            self._run_analyze()
            lines.append("<li>ANALYZE executed on heavy tables.</li>")
        elif self.vacuum_analyze and is_sim:
            lines.append("<li><em>(Simulation)</em> ANALYZE would be executed.</li>")

        title = _(
            "<h4>Simulation report</h4>"
        ) if is_sim else _(
            "<h4>Cleanup report</h4>"
        )
        html = title + "<ul>" + "".join(lines) + "</ul>"
        if is_sim:
            html += _(
                "<p class='text-muted'><em>No record was actually deleted. "
                "Uncheck 'Simulation Mode' to perform the cleanup.</em></p>"
            )

        self.write({
            "state": "done",
            "summary": html,
            "orphan_count": orphan_count,
            "orphan_size_mb": round(orphan_size, 2),
            "log_count": log_count,
            "mail_count": mail_count,
            "failed_mail_count": failed_mail_count,
        })
        if not is_sim:
            self.scan_id.message_post(body=_(
                "Cleanup executed: %d orphans (%.2f MB), %d logs, "
                "%d sent mails, %d failed mails removed."
            ) % (
                orphan_count, orphan_size, log_count,
                mail_count, failed_mail_count,
            ))
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context),
        }

    @staticmethod
    def _format_line(label, count, extra, is_sim):
        prefix = "<em>(Simulation)</em> " if is_sim else ""
        action = "would be removed" if is_sim else "removed"
        suffix = " (%s)" % extra if extra else ""
        return "<li>%s<strong>%d</strong> %s %s%s</li>" % (
            prefix, count, label, action, suffix,
        )

    def _run_analyze(self):
        """Run ANALYZE on tables flagged as heavy in the scan."""
        if not self.scan_id:
            return
        for table in self.scan_id.table_ids:
            full_name = "%s.%s" % (
                table.schema_name or "public", table.table_name,
            )
            try:
                self.env.cr.execute("ANALYZE %s" % full_name)
            except Exception:
                _logger.exception("ANALYZE failed on %s", full_name)
