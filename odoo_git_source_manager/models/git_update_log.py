# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class GitUpdateLog(models.Model):
    """Git Update Log Model

    Records history of all git update operations with results and details.
    """

    _name = "git.update.log"
    _description = "Git Update Log"
    _order = "timestamp desc, id desc"

    workspace_id = fields.Many2one(
        comodel_name="git.workspace",
        string="Workspace",
        required=True,
        ondelete="cascade",
        index=True,
        help="Workspace that was updated",
    )
    timestamp = fields.Datetime(
        string="Timestamp",
        required=True,
        default=fields.Datetime.now,
        index=True,
        help="When the operation occurred",
    )
    action = fields.Selection(
        selection=[
            ("clone", "Clone"),
            ("pull", "Pull"),
            ("fetch", "Fetch"),
            ("checkout", "Checkout"),
        ],
        string="Action",
        required=True,
        help="Type of git operation performed",
    )
    result = fields.Selection(
        selection=[
            ("success", "Success"),
            ("failure", "Failure"),
        ],
        string="Result",
        required=True,
        index=True,
        help="Operation result",
    )
    message = fields.Text(
        string="Message", help="Output or error message from git operation"
    )
    commit_hash = fields.Char(
        string="Commit Hash", help="Resulting commit hash after operation"
    )
    # Related fields for easier filtering
    repo_id = fields.Many2one(
        related="workspace_id.repo_id", string="Repository", store=True, readonly=True
    )
    entity_id = fields.Many2one(
        related="workspace_id.entity_id", string="Entity", store=True, readonly=True
    )

    def name_get(self):
        """Custom display name"""
        result = []
        for record in self:
            name = f"{record.action.upper()} - {record.result.upper()} - {record.timestamp}"
            result.append((record.id, name))
        return result

    @api.model
    def _cleanup_old_logs(self, days=90):
        """Clean up old log entries to prevent database bloat

        Args:
            days (int): Number of days to retain logs
        """
        cutoff_date = fields.Datetime.now() - fields.timedelta(days=days)
        old_logs = self.search(
            [
                ("timestamp", "<", cutoff_date),
                ("result", "=", "success"),  # Keep failure logs longer
            ]
        )

        count = len(old_logs)
        if count > 0:
            old_logs.unlink()
            _logger.info(f"Cleaned up {count} old log entries")

        return count
