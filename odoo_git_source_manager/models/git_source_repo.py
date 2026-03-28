# -*- coding: utf-8 -*-

import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class GitSourceRepo(models.Model):
    """Git Source Repository Model

    Stores metadata for Git repositories including URL, branch, authentication,
    and provider information.
    """

    _name = "git.source.repo"
    _description = "Git Source Repository"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(
        string="Repository Name",
        required=True,
        help="Descriptive name for the repository",
    )
    repo_url = fields.Char(
        string="Repository URL", required=True, help="Git repository URL (HTTPS or SSH)"
    )
    provider = fields.Selection(
        selection=[
            ("github", "GitHub"),
            ("gitlab", "GitLab"),
            ("bitbucket", "Bitbucket"),
            ("generic", "Generic Git"),
        ],
        string="Provider",
        default="generic",
        help="Git hosting provider",
    )
    branch = fields.Char(
        string="Branch",
        default="main",
        required=True,
        help="Default branch to checkout",
    )
    auth_type = fields.Selection(
        selection=[
            ("none", "No Authentication"),
            ("ssh", "SSH Key"),
            ("token", "Access Token"),
        ],
        string="Authentication Type",
        default="none",
        required=True,
        help="Authentication method for repository access",
    )
    token_param = fields.Char(
        string="Token Parameter Name",
        help="Name of ir.config_parameter containing the access token",
    )
    ssh_private_key_param = fields.Char(
        string="SSH Key Parameter Name",
        help="Name of ir.config_parameter containing SSH private key path",
    )
    is_active = fields.Boolean(
        string="Active", default=True, help="Enable or disable this repository"
    )
    notes = fields.Text(string="Notes", help="Additional notes or documentation")
    entity_link_ids = fields.One2many(
        comodel_name="git.entity.link",
        inverse_name="repo_id",
        string="Entity Links",
        help="Links to entities using this repository",
    )
    workspace_count = fields.Integer(
        string="Workspaces", compute="_compute_workspace_count"
    )
    last_commit = fields.Char(
        string="Last Known Commit",
        compute="_compute_last_commit",
        store=False,
        help="Most recent commit hash from workspaces",
    )

    _sql_constraints = [
        (
            "repo_url_unique",
            "UNIQUE(repo_url, branch)",
            "Repository URL and branch combination must be unique!",
        )
    ]

    @api.constrains("repo_url")
    def _check_repo_url(self):
        """Validate repository URL format"""
        for record in self:
            if not record.repo_url:
                continue

            # Check for basic git URL patterns
            patterns = [
                r"^https?://[^\s]+\.git$",  # HTTPS with .git
                r"^https?://[^\s]+$",  # HTTPS without .git
                r"^git@[^\s]+:[^\s]+\.git$",  # SSH format
                r"^ssh://[^\s]+\.git$",  # SSH URL format
            ]

            if not any(re.match(pattern, record.repo_url) for pattern in patterns):
                raise ValidationError(
                    _("Invalid repository URL format. Expected HTTPS or SSH URL.")
                )

            # Security: prevent path traversal
            if ".." in record.repo_url or ";" in record.repo_url:
                raise ValidationError(_("Repository URL contains invalid characters."))

    @api.constrains("auth_type", "token_param", "ssh_private_key_param")
    def _check_auth_params(self):
        """Validate authentication parameters"""
        for record in self:
            if record.auth_type == "token" and not record.token_param:
                raise ValidationError(
                    _(
                        "Token parameter name is required when using token authentication."
                    )
                )
            if record.auth_type == "ssh" and not record.ssh_private_key_param:
                raise ValidationError(
                    _(
                        "SSH key parameter name is required when using SSH authentication."
                    )
                )

    @api.depends("entity_link_ids")
    def _compute_workspace_count(self):
        """Compute number of workspaces using this repository"""
        for record in self:
            record.workspace_count = len(record.entity_link_ids.mapped("workspace_id"))

    @api.depends("entity_link_ids.workspace_id.current_commit")
    def _compute_last_commit(self):
        """Get most recent commit from workspaces"""
        for record in self:
            workspaces = record.entity_link_ids.mapped("workspace_id")
            if workspaces:
                # Filter workspaces that have been updated (have last_updated value)
                updated_workspaces = workspaces.filtered(lambda w: w.last_updated)
                if updated_workspaces:
                    # Get most recently updated workspace
                    latest_workspace = updated_workspaces.sorted(
                        "last_updated", reverse=True
                    )[:1]
                    record.last_commit = latest_workspace.current_commit or "Unknown"
                else:
                    # No workspace has been updated yet
                    record.last_commit = "Not updated yet"
            else:
                record.last_commit = "No workspaces"

    def action_test_connect(self):
        """Test connection to repository using git ls-remote"""
        self.ensure_one()

        try:
            git_manager = self.env["git.manager"]
            result = git_manager.test_connection(self.repo_url, self._get_auth_config())

            if result["success"]:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Connection Successful"),
                        "message": _("Successfully connected to repository."),
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Connection Failed"),
                        "message": result["message"],
                        "type": "danger",
                        "sticky": True,
                    },
                }

        except Exception as e:
            _logger.error(f"Error testing repository connection: {str(e)}")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_view_workspaces(self):
        """Open workspaces view for this repository"""
        self.ensure_one()

        workspace_ids = self.entity_link_ids.mapped("workspace_id").ids

        return {
            "name": _("Workspaces"),
            "type": "ir.actions.act_window",
            "res_model": "git.workspace",
            "view_mode": "list,form",
            "domain": [("id", "in", workspace_ids)],
            "context": {"default_repo_id": self.id},
        }

    def _get_auth_config(self):
        """Get authentication configuration for git operations"""
        self.ensure_one()

        auth_config = {
            "type": self.auth_type,
        }

        if self.auth_type == "token" and self.token_param:
            token = self.env["ir.config_parameter"].sudo().get_param(self.token_param)
            auth_config["token"] = token

        elif self.auth_type == "ssh" and self.ssh_private_key_param:
            ssh_key_path = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(self.ssh_private_key_param)
            )
            auth_config["ssh_key_path"] = ssh_key_path

        return auth_config

    def action_clone_now(self):
        """Manually trigger clone for all entity links"""
        self.ensure_one()

        if not self.entity_link_ids:
            raise UserError(_("No entity links configured for this repository."))

        for link in self.entity_link_ids:
            link.action_update_workspace()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Clone Initiated"),
                "message": _("Clone/update initiated for %d workspace(s).")
                % len(self.entity_link_ids),
                "type": "info",
                "sticky": False,
            },
        }
