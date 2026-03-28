# -*- coding: utf-8 -*-

import logging
from unittest.mock import patch, MagicMock
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "git_manager")
class TestGitWorkspace(TransactionCase):
    """Test cases for git.workspace model"""

    def setUp(self):
        super().setUp()
        self.workspace_model = self.env["git.workspace"]
        self.repo_model = self.env["git.source.repo"]
        self.link_model = self.env["git.entity.link"]

        # Create test data
        self.test_repo = self.repo_model.create(
            {
                "name": "Test Repo",
                "repo_url": "https://github.com/test/repo.git",
                "branch": "main",
                "auth_type": "none",
            }
        )

        self.test_company = self.env["res.company"].search([], limit=1)

        self.test_link = self.link_model.create(
            {
                "entity_id": self.test_company.id,
                "repo_id": self.test_repo.id,
            }
        )

        self.test_workspace = self.test_link.workspace_id

    def test_workspace_created_automatically(self):
        """Test workspace is created when entity link is created"""
        self.assertTrue(self.test_workspace)
        self.assertEqual(self.test_workspace.entity_link_id.id, self.test_link.id)

    def test_workspace_status_default(self):
        """Test workspace has unknown status by default"""
        self.assertEqual(self.test_workspace.status, "unknown")

    @patch(
        "odoo.addons.odoo_git_source_manager.services.git_manager.GitManager.clone_or_pull"
    )
    def test_update_now_success(self, mock_clone_or_pull):
        """Test successful workspace update"""
        # Mock git manager response
        mock_clone_or_pull.return_value = {
            "success": True,
            "message": "Clone successful",
            "commit": "abc123",
            "action": "clone",
        }

        result = self.test_workspace.action_update_now()

        # Verify workspace status updated
        self.assertEqual(self.test_workspace.status, "ok")
        self.assertEqual(self.test_workspace.current_commit, "abc123")
        self.assertTrue(self.test_workspace.last_updated)

        # Verify log created
        logs = self.env["git.update.log"].search(
            [("workspace_id", "=", self.test_workspace.id)]
        )
        self.assertTrue(len(logs) > 0)
        self.assertEqual(logs[0].result, "success")

    @patch(
        "odoo.addons.odoo_git_source_manager.services.git_manager.GitManager.clone_or_pull"
    )
    def test_update_now_failure(self, mock_clone_or_pull):
        """Test failed workspace update"""
        # Mock git manager failure
        mock_clone_or_pull.return_value = {
            "success": False,
            "message": "Clone failed: connection timeout",
            "commit": "",
            "action": "clone",
        }

        result = self.test_workspace.action_update_now()

        # Verify workspace status set to failed
        self.assertEqual(self.test_workspace.status, "failed")

        # Verify failure log created
        logs = self.env["git.update.log"].search(
            [("workspace_id", "=", self.test_workspace.id)]
        )
        self.assertTrue(len(logs) > 0)
        self.assertEqual(logs[0].result, "failure")

    def test_update_now_prevents_concurrent_updates(self):
        """Test that concurrent updates are prevented"""
        # Set workspace to updating status
        self.test_workspace.write({"status": "updating"})

        # Try to update again
        with self.assertRaises(UserError):
            self.test_workspace.action_update_now()

    @patch(
        "odoo.addons.odoo_git_source_manager.services.git_manager.GitManager.is_git_repo"
    )
    @patch(
        "odoo.addons.odoo_git_source_manager.services.git_manager.GitManager.get_current_commit"
    )
    @patch(
        "odoo.addons.odoo_git_source_manager.services.git_manager.GitManager.get_status"
    )
    def test_refresh_status(self, mock_get_status, mock_get_commit, mock_is_repo):
        """Test refreshing workspace status"""
        # Mock git manager responses
        mock_is_repo.return_value = True
        mock_get_commit.return_value = "def456"
        mock_get_status.return_value = {"clean": True, "changes": [], "branch": "main"}

        self.test_workspace.action_refresh_status()

        # Verify status updated
        self.assertEqual(self.test_workspace.current_commit, "def456")
        self.assertEqual(self.test_workspace.status, "ok")

    def test_log_count_computation(self):
        """Test log count computed field"""
        self.assertEqual(self.test_workspace.log_count, 0)

        # Create log entries
        self.env["git.update.log"].create(
            {
                "workspace_id": self.test_workspace.id,
                "action": "pull",
                "result": "success",
                "message": "Test log 1",
            }
        )

        self.env["git.update.log"].create(
            {
                "workspace_id": self.test_workspace.id,
                "action": "pull",
                "result": "success",
                "message": "Test log 2",
            }
        )

        self.test_workspace.invalidate_recordset(["log_count"])
        self.assertEqual(self.test_workspace.log_count, 2)

    @patch(
        "odoo.addons.odoo_git_source_manager.services.git_manager.GitManager.clone_or_pull"
    )
    def test_cron_update_all_workspaces(self, mock_clone_or_pull):
        """Test cron job updates all enabled workspaces"""
        # Mock successful update
        mock_clone_or_pull.return_value = {
            "success": True,
            "message": "Update successful",
            "commit": "abc123",
            "action": "pull",
        }

        # Ensure link is enabled
        self.test_link.write({"enabled": True})

        # Run cron
        self.workspace_model.cron_update_all_workspaces()

        # Verify workspace was updated
        self.assertEqual(self.test_workspace.status, "ok")

    def test_unique_constraint_path(self):
        """Test unique constraint on workspace path"""
        # Try to create workspace with same path
        with self.assertRaises(Exception):  # Unique constraint violation
            self.workspace_model.create(
                {
                    "entity_link_id": self.test_link.id,
                    "path": self.test_workspace.path,
                    "status": "unknown",
                }
            )
