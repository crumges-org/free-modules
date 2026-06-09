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

from datetime import timedelta

from odoo import _, api, fields, models


class DbCleanerBackupReminder(models.Model):
    _name = "db.cleaner.backup.reminder"
    _description = "Database Backup Reminder"
    _inherit = ["mail.thread"]
    _rec_name = "display_name"

    active = fields.Boolean(string="Active", default=True)
    frequency = fields.Selection(
        [
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("biweekly", "Every 2 weeks"),
            ("monthly", "Monthly"),
        ],
        string="Frequency",
        default="weekly",
        required=True,
    )
    last_backup_date = fields.Datetime(
        string="Last Backup",
        tracking=True,
    )
    next_reminder = fields.Datetime(
        string="Next Reminder",
        compute="_compute_next_reminder",
        store=True,
    )
    user_ids = fields.Many2many(
        "res.users",
        string="Recipients",
        help="Users notified when a backup is due.",
    )
    notes = fields.Text(string="Backup Notes")
    is_overdue = fields.Boolean(
        string="Overdue",
        compute="_compute_next_reminder",
        store=True,
    )
    display_name = fields.Char(
        string="Name",
        compute="_compute_display_name",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends("frequency", "last_backup_date")
    def _compute_next_reminder(self):
        deltas = {
            "daily": timedelta(days=1),
            "weekly": timedelta(days=7),
            "biweekly": timedelta(days=14),
            "monthly": timedelta(days=30),
        }
        now = fields.Datetime.now()
        for rec in self:
            base = rec.last_backup_date or now
            delta = deltas.get(rec.frequency, timedelta(days=7))
            rec.next_reminder = base + delta
            rec.is_overdue = bool(rec.next_reminder and rec.next_reminder < now)

    @api.depends("frequency", "last_backup_date")
    def _compute_display_name(self):
        labels = dict(self._fields["frequency"].selection)
        for rec in self:
            label = labels.get(rec.frequency, rec.frequency or "")
            rec.display_name = "Backup reminder (%s)" % label

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_mark_done(self):
        """Mark a backup as performed now."""
        self.write({"last_backup_date": fields.Datetime.now()})
        for rec in self:
            rec.message_post(body=_(
                "Backup marked as performed by %s."
            ) % self.env.user.name)
        return True

    @api.model
    def cron_check_reminders(self):
        """Cron: notify users when a backup is due."""
        now = fields.Datetime.now()
        overdue = self.search([
            ("active", "=", True),
            ("next_reminder", "<=", now),
        ])
        for rec in overdue:
            rec._notify_overdue()
        return True

    def _notify_overdue(self):
        self.ensure_one()
        recipients = self.user_ids or self.env.ref(
            "base.group_system"
        ).users
        if not recipients:
            return
        partners = recipients.mapped("partner_id")
        body = _(
            "<p>The database backup is <strong>overdue</strong>.</p>"
            "<p>Last backup: %s</p>"
            "<p>Frequency: %s</p>"
        ) % (
            self.last_backup_date or _("never"),
            dict(self._fields["frequency"].selection).get(
                self.frequency, self.frequency,
            ),
        )
        self.message_post(
            body=body,
            partner_ids=partners.ids,
            subject=_("Backup reminder: action required"),
        )
