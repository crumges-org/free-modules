# -*- coding: utf-8 -*-

import logging
import os
from pathlib import Path
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class GitWorkspace(models.Model):
    """Git Workspace Model

    Represents local Git checkouts with status tracking and update management.
    """

    _name = "git.workspace"
    _description = "Git Workspace"
    _order = "last_updated desc, id desc"

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
        help="Display name for the workspace",
    )
    entity_link_id = fields.Many2one(
        comodel_name="git.entity.link",
        string="Entity Link",
        required=True,
        ondelete="cascade",
        help="Reference to entity-repository link",
    )
    path = fields.Char(
        string="Local Path",
        required=True,
        help="Filesystem path to local checkout (cross-platform compatible)",
    )
    last_updated = fields.Datetime(
        string="Last Updated", readonly=True, help="Timestamp of last successful update"
    )
    current_commit = fields.Char(
        string="Current Commit", readonly=True, help="Current commit hash"
    )
    status = fields.Selection(
        selection=[
            ("unknown", "Unknown"),
            ("ok", "OK"),
            ("failed", "Failed"),
            ("updating", "Updating"),
        ],
        string="Status",
        default="unknown",
        required=True,
        help="Current workspace status",
    )
    log_ids = fields.One2many(
        comodel_name="git.update.log",
        inverse_name="workspace_id",
        string="Update Logs",
        help="History of update operations",
    )
    log_count = fields.Integer(string="Logs", compute="_compute_log_count")
    repo_id = fields.Many2one(
        related="entity_link_id.repo_id", string="Repository", store=True, readonly=True
    )
    entity_id = fields.Many2one(
        related="entity_link_id.entity_id", string="Entity", store=True, readonly=True
    )

    _sql_constraints = [
        ("path_unique", "UNIQUE(path)", "Workspace path must be unique!")
    ]

    @api.constrains("path")
    def _check_path(self):
        """Validate and normalize workspace path"""
        for record in self:
            if not record.path:
                continue

            # Normalize path for the current OS
            normalized_path = self._normalize_path(record.path)

            # Update if path changed during normalization
            if normalized_path != record.path:
                record.path = normalized_path

            # Validate path doesn't contain dangerous characters
            if any(char in record.path for char in [";", "|", "&", "`", "$"]):
                raise ValidationError(
                    _("Path contains invalid or dangerous characters.")
                )

            # Check for path traversal attempts
            if ".." in record.path.split(os.sep):
                raise ValidationError(
                    _("Path contains invalid traversal patterns (..).")
                )

    @staticmethod
    def _normalize_path(path):
        """Normalize path for cross-platform compatibility

        Args:
            path (str): Input path

        Returns:
            str: Normalized path
        """
        if not path:
            return path

        # Convert to Path object for normalization
        path_obj = Path(path)

        # Convert to absolute path and normalize
        # This handles:
        # - Forward/backward slashes
        # - Multiple consecutive slashes
        # - Relative paths
        normalized = str(path_obj.resolve())

        return normalized

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to normalize path"""
        for vals in vals_list:
            if vals.get("path"):
                vals["path"] = self._normalize_path(vals["path"])
        return super(GitWorkspace, self).create(vals_list)

    def write(self, vals):
        """Override write to normalize path"""
        if vals.get("path"):
            vals["path"] = self._normalize_path(vals["path"])
        return super(GitWorkspace, self).write(vals)

    @api.depends("entity_link_id.name")
    def _compute_name(self):
        """Compute display name"""
        for record in self:
            if record.entity_link_id:
                record.name = f"Workspace: {record.entity_link_id.name}"
            else:
                record.name = "New Workspace"

    @api.depends("log_ids")
    def _compute_log_count(self):
        """Compute number of logs"""
        for record in self:
            record.log_count = len(record.log_ids)

    def action_update_now(self):
        """Execute git update operation"""
        self.ensure_one()

        # Prevent concurrent updates
        if self.status == "updating":
            raise UserError(_("Workspace is already being updated."))

        # Set updating status
        self.write({"status": "updating"})
        self.env.cr.commit()  # Commit to make status visible

        try:
            # Get git manager service
            git_manager = self.env["git.manager"]

            # Get repository and auth config
            repo = self.entity_link_id.repo_id
            auth_config = repo._get_auth_config()

            # Execute clone or pull
            result = git_manager.clone_or_pull(
                repo_url=repo.repo_url,
                branch=repo.branch,
                path=self.path,
                auth_config=auth_config,
            )

            # Create log entry
            log_vals = {
                "workspace_id": self.id,
                "timestamp": fields.Datetime.now(),
                "action": "pull" if result.get("action") == "pull" else "clone",
                "result": "success" if result["success"] else "failure",
                "message": result["message"],
                "commit_hash": result.get("commit", ""),
            }
            self.env["git.update.log"].create(log_vals)

            # Update workspace status
            if result["success"]:
                self.write(
                    {
                        "status": "ok",
                        "last_updated": fields.Datetime.now(),
                        "current_commit": result.get("commit", ""),
                    }
                )

                notification_type = "success"
                notification_title = _("Update Successful")
                notification_message = _("Workspace updated successfully.")
            else:
                self.write({"status": "failed"})
                notification_type = "danger"
                notification_title = _("Update Failed")
                notification_message = result["message"]

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": notification_title,
                    "message": notification_message,
                    "type": notification_type,
                    "sticky": notification_type == "danger",
                },
            }

        except Exception as e:
            _logger.error(
                f"Error updating workspace {self.id}: {str(e)}", exc_info=True
            )

            # Create error log
            self.env["git.update.log"].create(
                {
                    "workspace_id": self.id,
                    "timestamp": fields.Datetime.now(),
                    "action": "pull",
                    "result": "failure",
                    "message": f"Exception: {str(e)}",
                }
            )

            # Update status
            self.write({"status": "failed"})

            raise UserError(_("Update failed: %s") % str(e))

    def action_refresh_status(self):
        """Refresh workspace status from git"""
        self.ensure_one()

        try:
            git_manager = self.env["git.manager"]

            # Check if path exists and is a git repo
            if not git_manager.is_git_repo(self.path):
                self.write(
                    {
                        "status": "unknown",
                        "current_commit": False,
                    }
                )
                return

            # Get current commit
            commit = git_manager.get_current_commit(self.path)

            # Get status
            status_result = git_manager.get_status(self.path)

            # Update workspace
            self.write(
                {
                    "current_commit": commit,
                    "status": "ok" if status_result.get("clean", False) else "failed",
                }
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Status Refreshed"),
                    "message": _("Workspace status updated."),
                    "type": "info",
                },
            }

        except Exception as e:
            _logger.error(f"Error refreshing status: {str(e)}")
            raise UserError(_("Failed to refresh status: %s") % str(e))

    def action_view_logs(self):
        """Open logs view"""
        self.ensure_one()

        return {
            "name": _("Update Logs"),
            "type": "ir.actions.act_window",
            "res_model": "git.update.log",
            "view_mode": "list,form",
            "domain": [("workspace_id", "=", self.id)],
            "context": {"default_workspace_id": self.id},
        }

    @api.model
    def cron_update_all_workspaces(self):
        """Cron job to update all enabled workspaces"""
        _logger.info("Starting scheduled workspace updates")

        # Find enabled entity links
        enabled_links = self.env["git.entity.link"].search([("enabled", "=", True)])

        workspaces = enabled_links.mapped("workspace_id").filtered(
            lambda w: w.status != "updating"
        )

        _logger.info(f"Found {len(workspaces)} workspaces to update")

        success_count = 0
        failure_count = 0

        for workspace in workspaces:
            try:
                workspace.action_update_now()
                success_count += 1
            except Exception as e:
                _logger.error(
                    f"Failed to update workspace {workspace.id}: {str(e)}",
                    exc_info=True,
                )
                failure_count += 1

        _logger.info(
            f"Scheduled update complete. Success: {success_count}, "
            f"Failed: {failure_count}"
        )

        return True
