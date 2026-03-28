# -*- coding: utf-8 -*-

import logging
import json
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class GitManagerController(http.Controller):
    """JSON RPC Controller for Git Manager AJAX operations"""

    def _check_access(self, workspace_id):
        """Check if user has access to workspace

        Args:
            workspace_id (int): Workspace ID

        Returns:
            recordset: Workspace record

        Raises:
            AccessError: If user doesn't have access
        """
        workspace = request.env["git.workspace"].browse(workspace_id)

        if not workspace.exists():
            raise UserError("Workspace not found")

        # Check if user has at least read access
        try:
            workspace.check_access_rights("read")
            workspace.check_access_rule("read")
        except AccessError:
            raise AccessError("You do not have access to this workspace")

        return workspace

    @http.route("/git/update_now", type="json", auth="user", methods=["POST"])
    def update_now(self, workspace_id):
        """Trigger workspace update via AJAX

        Args:
            workspace_id (int): Workspace ID to update

        Returns:
            dict: Result with success status and message
        """
        try:
            workspace = self._check_access(workspace_id)

            # Check if workspace is already updating
            if workspace.status == "updating":
                return {
                    "success": False,
                    "message": "Workspace is already being updated",
                    "status": "updating",
                }

            # Trigger update
            result = workspace.action_update_now()

            return {
                "success": True,
                "message": "Update initiated successfully",
                "status": workspace.status,
                "result": result,
            }

        except UserError as e:
            _logger.warning(f"User error in update_now: {str(e)}")
            return {"success": False, "message": str(e), "status": "error"}
        except Exception as e:
            _logger.error(f"Error in update_now: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Internal error: {str(e)}",
                "status": "error",
            }

    @http.route(
        "/git/status/<int:workspace_id>", type="json", auth="user", methods=["GET"]
    )
    def get_status(self, workspace_id):
        """Get current workspace status

        Args:
            workspace_id (int): Workspace ID

        Returns:
            dict: Current workspace status information
        """
        try:
            workspace = self._check_access(workspace_id)

            return {
                "success": True,
                "workspace_id": workspace.id,
                "status": workspace.status,
                "last_updated": (
                    workspace.last_updated.isoformat()
                    if workspace.last_updated
                    else None
                ),
                "current_commit": workspace.current_commit or "",
                "path": workspace.path,
                "entity": workspace.entity_id.name if workspace.entity_id else "",
                "repo": workspace.repo_id.name if workspace.repo_id else "",
            }

        except Exception as e:
            _logger.error(f"Error in get_status: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}

    @http.route(
        "/git/logs/<int:workspace_id>", type="json", auth="user", methods=["GET"]
    )
    def get_logs(self, workspace_id, limit=20):
        """Get recent update logs for workspace

        Args:
            workspace_id (int): Workspace ID
            limit (int): Number of logs to return (default 20)

        Returns:
            dict: List of recent logs
        """
        try:
            workspace = self._check_access(workspace_id)

            logs = request.env["git.update.log"].search(
                [("workspace_id", "=", workspace_id)],
                order="timestamp desc",
                limit=limit,
            )

            log_data = []
            for log in logs:
                log_data.append(
                    {
                        "id": log.id,
                        "timestamp": (
                            log.timestamp.isoformat() if log.timestamp else None
                        ),
                        "action": log.action,
                        "result": log.result,
                        "message": log.message or "",
                        "commit_hash": log.commit_hash or "",
                    }
                )

            return {"success": True, "logs": log_data, "total": len(logs)}

        except Exception as e:
            _logger.error(f"Error in get_logs: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}

    @http.route(
        "/git/refresh_status/<int:workspace_id>",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def refresh_status(self, workspace_id):
        """Refresh workspace status from git

        Args:
            workspace_id (int): Workspace ID

        Returns:
            dict: Updated status information
        """
        try:
            workspace = self._check_access(workspace_id)

            # Trigger status refresh
            workspace.action_refresh_status()

            return {
                "success": True,
                "status": workspace.status,
                "current_commit": workspace.current_commit or "",
                "message": "Status refreshed successfully",
            }

        except Exception as e:
            _logger.error(f"Error in refresh_status: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}

    @http.route("/git/test_connection", type="json", auth="user", methods=["POST"])
    def test_connection(self, repo_id):
        """Test connection to repository

        Args:
            repo_id (int): Repository ID

        Returns:
            dict: Connection test result
        """
        try:
            # Check access
            repo = request.env["git.source.repo"].browse(repo_id)

            if not repo.exists():
                return {"success": False, "message": "Repository not found"}

            # Check permissions
            try:
                repo.check_access_rights("read")
                repo.check_access_rule("read")
            except AccessError:
                return {"success": False, "message": "Access denied"}

            # Test connection
            result = repo.action_test_connect()

            return {"success": True, "result": result}

        except Exception as e:
            _logger.error(f"Error in test_connection: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}
