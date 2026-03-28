# -*- coding: utf-8 -*-

import logging
import os
import platform
from pathlib import Path
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class GitEntityLink(models.Model):
    """Git Entity Link Model

    Links Git repositories to entities with ordering and workspace management.
    This is a through model for many-to-many relationship with additional fields.
    """

    _name = "git.entity.link"
    _description = "Git Entity Link"
    _order = "entity_id, sequence, id"

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
        help="Display name for the link",
    )
    entity_id = fields.Many2one(
        comodel_name="res.company",  # Using res.company as entity, can be changed
        string="Entity",
        required=True,
        ondelete="cascade",
        help="Entity (company/database) to link repository to",
    )
    repo_id = fields.Many2one(
        comodel_name="git.source.repo",
        string="Repository",
        required=True,
        ondelete="cascade",
        help="Git repository to link",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Order of repository application (lower = first)",
    )
    workspace_path = fields.Char(
        string="Workspace Path",
        compute="_compute_workspace_path",
        store=True,
        help="Computed local checkout path",
    )
    enabled = fields.Boolean(
        string="Enabled", default=True, help="Enable or disable this link"
    )
    workspace_id = fields.Many2one(
        comodel_name="git.workspace",
        string="Workspace",
        readonly=True,
        help="Associated workspace",
    )
    last_update_status = fields.Selection(
        related="workspace_id.status", string="Status", readonly=True
    )
    last_updated = fields.Datetime(
        related="workspace_id.last_updated", string="Last Updated", readonly=True
    )

    _sql_constraints = [
        (
            "entity_repo_unique",
            "UNIQUE(entity_id, repo_id)",
            "Entity and Repository combination must be unique!",
        )
    ]

    @api.depends("entity_id.name", "repo_id.name")
    def _compute_name(self):
        """Compute display name"""
        for record in self:
            if record.entity_id and record.repo_id:
                record.name = f"{record.entity_id.name} - {record.repo_id.name}"
            else:
                record.name = "New Link"

    @staticmethod
    def _get_default_workspace_base_path():
        """Get default workspace base path based on OS

        Returns:
            str: Default workspace base path
        """
        system = platform.system()

        if system == "Windows":
            # Windows: Use ProgramData directory
            # e.g., C:\ProgramData\Odoo\GitWorkspaces
            return os.path.join(
                os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
                "Odoo",
                "GitWorkspaces",
            )
        else:
            # Linux/Unix: Use standard location
            return "/var/lib/odoo/gitworkspaces"

    @api.depends("entity_id", "repo_id")
    def _compute_workspace_path(self):
        """Compute local workspace path (cross-platform compatible)"""
        for record in self:
            if record.entity_id and record.repo_id:
                # Get base path from config or use OS-appropriate default
                base_path = (
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param(
                        "git_mgr.workspace_base_path",
                        default=self._get_default_workspace_base_path(),
                    )
                )

                # Sanitize names for filesystem
                entity_name = self._sanitize_path_component(record.entity_id.name)
                repo_name = self._sanitize_path_component(record.repo_id.name)

                # Use pathlib for cross-platform path construction
                workspace_path = Path(base_path) / entity_name / repo_name
                record.workspace_path = str(workspace_path)
            else:
                record.workspace_path = False

    @staticmethod
    def _sanitize_path_component(name):
        """Sanitize string for use in filesystem path"""
        import re

        # Remove or replace invalid characters
        sanitized = re.sub(r"[^\w\-_]", "_", name)
        # Remove consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        return sanitized.lower()

    @api.model_create_multi
    def create(self, vals_list):
        """Create entity link and associated workspace"""
        records = super().create(vals_list)

        for record in records:
            # Create workspace if it doesn't exist
            if not record.workspace_id:
                workspace = self.env["git.workspace"].create(
                    {
                        "entity_link_id": record.id,
                        "path": record.workspace_path,
                        "status": "unknown",
                    }
                )
                record.workspace_id = workspace.id

        return records

    def action_update_workspace(self):
        """Trigger workspace update"""
        self.ensure_one()

        if not self.workspace_id:
            raise ValidationError(_("No workspace configured for this link."))

        if not self.enabled:
            raise ValidationError(_("This link is disabled. Enable it first."))

        return self.workspace_id.action_update_now()

    def action_view_workspace(self):
        """Open workspace form view"""
        self.ensure_one()

        return {
            "name": _("Workspace"),
            "type": "ir.actions.act_window",
            "res_model": "git.workspace",
            "res_id": self.workspace_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_logs(self):
        """Open update logs for this workspace"""
        self.ensure_one()

        return {
            "name": _("Update Logs"),
            "type": "ir.actions.act_window",
            "res_model": "git.update.log",
            "view_mode": "list,form",
            "domain": [("workspace_id", "=", self.workspace_id.id)],
            "context": {"default_workspace_id": self.workspace_id.id},
        }
