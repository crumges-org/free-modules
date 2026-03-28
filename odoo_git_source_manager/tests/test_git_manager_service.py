# -*- coding: utf-8 -*-

import logging
from unittest.mock import patch, MagicMock, call
from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "git_manager")
class TestGitManager(TransactionCase):
    """Test cases for git.manager service"""

    def setUp(self):
        super().setUp()
        self.git_manager = self.env["git.manager"]

    @patch("subprocess.run")
    def test_safe_command_success(self, mock_run):
        """Test safe command execution with success"""
        # Mock successful command
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"Command output", stderr=b""
        )

        result = self.git_manager.safe_command(["git", "status"])

        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["stdout"], "Command output")
        self.assertEqual(result["stderr"], "")
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_safe_command_failure(self, mock_run):
        """Test safe command execution with failure"""
        # Mock failed command
        mock_run.return_value = MagicMock(
            returncode=1, stdout=b"", stderr=b"Error message"
        )

        result = self.git_manager.safe_command(["git", "invalid"])

        self.assertEqual(result["returncode"], 1)
        self.assertEqual(result["stderr"], "Error message")

    @patch("subprocess.run")
    def test_safe_command_timeout(self, mock_run):
        """Test safe command handles timeout"""
        import subprocess

        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

        result = self.git_manager.safe_command(["git", "clone", "url"])

        self.assertEqual(result["returncode"], -1)
        self.assertIn("timed out", result["stderr"])

    def test_mask_sensitive_data(self):
        """Test masking of sensitive data in commands"""
        cmd = ["git", "clone", "https://token123@github.com/repo.git"]
        masked = self.git_manager._mask_sensitive_data(cmd)

        self.assertEqual(masked[0], "git")
        self.assertEqual(masked[1], "clone")
        self.assertIn("***@", masked[2])
        self.assertNotIn("token123", masked[2])

    @patch("os.path.exists")
    @patch("os.path.isdir")
    def test_is_git_repo_true(self, mock_isdir, mock_exists):
        """Test is_git_repo returns True for valid repo"""
        mock_exists.return_value = True
        mock_isdir.return_value = True

        result = self.git_manager.is_git_repo("/path/to/repo")

        self.assertTrue(result)

    @patch("os.path.exists")
    def test_is_git_repo_false(self, mock_exists):
        """Test is_git_repo returns False for non-existent path"""
        mock_exists.return_value = False

        result = self.git_manager.is_git_repo("/nonexistent")

        self.assertFalse(result)

    @patch("subprocess.run")
    def test_test_connection_success(self, mock_run):
        """Test connection test success"""
        # Mock ls-remote success
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"refs/heads/main", stderr=b""
        )

        result = self.git_manager.test_connection(
            "https://github.com/test/repo.git", {"type": "none"}
        )

        self.assertTrue(result["success"])
        self.assertIn("Successfully", result["message"])

    @patch("subprocess.run")
    def test_test_connection_failure(self, mock_run):
        """Test connection test failure"""
        # Mock ls-remote failure
        mock_run.return_value = MagicMock(
            returncode=128, stdout=b"", stderr=b"fatal: repository not found"
        )

        result = self.git_manager.test_connection(
            "https://github.com/test/nonexistent.git", {"type": "none"}
        )

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"].lower())

    @patch("os.makedirs")
    @patch("os.path.exists")
    @patch("os.path.dirname")
    @patch("subprocess.run")
    def test_clone_or_pull_new_repo(
        self, mock_run, mock_dirname, mock_exists, mock_makedirs
    ):
        """Test cloning new repository"""
        # Mock path doesn't exist (new clone)
        mock_exists.return_value = False
        mock_dirname.return_value = "/var/lib/odoo/gitworkspaces"

        # Mock clone command success
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=b"Cloning into...", stderr=b""),
            MagicMock(
                returncode=0, stdout=b"abc123def\n", stderr=b""
            ),  # get_current_commit
        ]

        result = self.git_manager.clone_or_pull(
            "https://github.com/test/repo.git",
            "main",
            "/var/lib/odoo/gitworkspaces/test/repo",
            {"type": "none"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "clone")
        self.assertIn("abc123def", result["commit"])

    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("subprocess.run")
    def test_clone_or_pull_existing_repo(self, mock_run, mock_isdir, mock_exists):
        """Test pulling updates for existing repository"""
        # Mock path exists (existing repo)
        mock_exists.return_value = True
        mock_isdir.return_value = True

        # Mock fetch and reset commands
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=b"Fetching...", stderr=b""),  # fetch
            MagicMock(
                returncode=0, stdout=b"HEAD is now at abc123", stderr=b""
            ),  # reset
            MagicMock(
                returncode=0, stdout=b"abc123def\n", stderr=b""
            ),  # get_current_commit
        ]

        result = self.git_manager.clone_or_pull(
            "https://github.com/test/repo.git",
            "main",
            "/var/lib/odoo/gitworkspaces/test/repo",
            {"type": "none"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "pull")

    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("subprocess.run")
    def test_get_current_commit(self, mock_run, mock_isdir, mock_exists):
        """Test getting current commit hash"""
        mock_exists.return_value = True
        mock_isdir.return_value = True

        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"abc123def456\n", stderr=b""
        )

        commit = self.git_manager.get_current_commit("/path/to/repo")

        self.assertEqual(commit, "abc123def456")

    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("subprocess.run")
    def test_get_status_clean(self, mock_run, mock_isdir, mock_exists):
        """Test getting status for clean repository"""
        mock_exists.return_value = True
        mock_isdir.return_value = True

        # Mock status and branch commands
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # status (clean)
            MagicMock(returncode=0, stdout=b"main\n", stderr=b""),  # branch
        ]

        status = self.git_manager.get_status("/path/to/repo")

        self.assertTrue(status["clean"])
        self.assertEqual(len(status["changes"]), 0)
        self.assertEqual(status["branch"], "main")

    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("subprocess.run")
    def test_get_status_with_changes(self, mock_run, mock_isdir, mock_exists):
        """Test getting status with uncommitted changes"""
        mock_exists.return_value = True
        mock_isdir.return_value = True

        # Mock status with changes
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=b" M file1.txt\n?? file2.txt\n", stderr=b""),
            MagicMock(returncode=0, stdout=b"main\n", stderr=b""),
        ]

        status = self.git_manager.get_status("/path/to/repo")

        self.assertFalse(status["clean"])
        self.assertEqual(len(status["changes"]), 2)

    def test_format_repo_url_with_token(self):
        """Test formatting URL with token authentication"""
        url = "https://github.com/company/repo.git"
        auth_config = {"type": "token", "token": "ghp_testtoken123"}

        formatted = self.git_manager._format_repo_url(url, auth_config)

        self.assertIn("ghp_testtoken123@", formatted)
        self.assertIn("github.com", formatted)

    def test_format_repo_url_no_auth(self):
        """Test formatting URL without authentication"""
        url = "https://github.com/company/repo.git"
        auth_config = {"type": "none"}

        formatted = self.git_manager._format_repo_url(url, auth_config)

        self.assertEqual(formatted, url)

    def test_prepare_env_with_ssh(self):
        """Test preparing environment for SSH authentication"""
        auth_config = {"type": "ssh", "ssh_key_path": "/home/odoo/.ssh/git_id"}

        env = self.git_manager._prepare_env(auth_config)

        self.assertIn("GIT_SSH_COMMAND", env)
        self.assertIn("/home/odoo/.ssh/git_id", env["GIT_SSH_COMMAND"])
