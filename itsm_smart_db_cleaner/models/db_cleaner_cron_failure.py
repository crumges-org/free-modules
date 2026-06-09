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

from odoo import api, fields, models


class DbCleanerCronFailure(models.Model):
    _name = "db.cleaner.cron.failure"
    _description = "Cron Job Failure / Issue"
    _order = "severity desc, last_call asc"

    scan_id = fields.Many2one(
        "db.cleaner.scan",
        string="Scan",
        required=True,
        ondelete="cascade",
        index=True,
    )
    cron_id = fields.Many2one(
        "ir.cron",
        string="Cron",
        ondelete="set null",
    )
    cron_name = fields.Char(string="Job Name")
    model_name = fields.Char(string="Model")
    last_call = fields.Datetime(string="Last Call")
    next_call = fields.Datetime(string="Next Call")
    is_active = fields.Boolean(string="Active")
    severity = fields.Selection(
        [
            ("info", "Info"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        string="Severity",
        default="warning",
    )
    issue = fields.Selection(
        [
            ("never_run", "Never executed"),
            ("overdue", "Overdue"),
            ("inactive", "Inactive"),
            ("error", "Last run failed"),
        ],
        string="Issue",
    )
    description = fields.Text(string="Details")

    # -------------------------------------------------------------------------
    # Scan
    # -------------------------------------------------------------------------

    @api.model
    def _scan(self, scan):
        """Detect cron jobs that look broken or overdue."""
        Cron = self.env["ir.cron"].sudo()
        crons = Cron.with_context(active_test=False).search([])
        now = fields.Datetime.now()
        records = []
        for cron in crons:
            issue = None
            severity = "info"
            description = ""

            if not cron.active:
                issue = "inactive"
                severity = "info"
                description = "This cron job is currently disabled."
            elif not cron.lastcall:
                issue = "never_run"
                severity = "warning"
                description = "This cron has never been executed."
            elif cron.nextcall and cron.nextcall < now:
                # Overdue if scheduled time is more than 1 hour in the past.
                delta = (now - cron.nextcall).total_seconds()
                if delta > 3600:
                    issue = "overdue"
                    severity = "warning" if delta < 86400 else "error"
                    description = (
                        "Next call was scheduled %.1f hours ago and "
                        "did not run." % (delta / 3600.0)
                    )

            if not issue:
                continue

            records.append({
                "scan_id": scan.id,
                "cron_id": cron.id,
                "cron_name": cron.cron_name or cron.name,
                "model_name": cron.model_id.model if cron.model_id else False,
                "last_call": cron.lastcall,
                "next_call": cron.nextcall,
                "is_active": cron.active,
                "severity": severity,
                "issue": issue,
                "description": description,
            })

        if records:
            self.create(records)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_open_cron(self):
        self.ensure_one()
        if not self.cron_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.cron",
            "res_id": self.cron_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_reactivate(self):
        for rec in self:
            if rec.cron_id:
                rec.cron_id.write({"active": True})
        return True

    def action_run_now(self):
        self.ensure_one()
        if self.cron_id:
            self.cron_id.method_direct_trigger()
        return True
