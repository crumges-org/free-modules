# -*- coding: utf-8 -*-

import logging
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "git_manager")
class TestGitSourceRepo(TransactionCase):
    """Test cases for git.source.repo model"""

    def setUp(self):
        super().setUp()
        self.repo_model = self.env["git.source.repo"]

    def test_create_repo_valid(self):
        """Test creating repository with valid data"""
        repo = self.repo_model.create(
            {
                "name": "Test Repo",
                "repo_url": "https://github.com/odoo/odoo.git",
                "branch": "17.0",
                "auth_type": "none",
            }
        )

        self.assertTrue(repo.id)
        self.assertEqual(repo.name, "Test Repo")
        self.assertEqual(repo.branch, "17.0")
        self.assertEqual(repo.auth_type, "none")
        self.assertTrue(repo.is_active)

    def test_create_repo_with_ssh_auth(self):
        """Test creating repository with SSH authentication"""
        repo = self.repo_model.create(
            {
                "name": "Private Repo",
                "repo_url": "git@github.com:company/private.git",
                "branch": "main",
                "auth_type": "ssh",
                "ssh_private_key_param": "git_mgr.ssh_key_path",
            }
        )

        self.assertEqual(repo.auth_type, "ssh")
        self.assertEqual(repo.ssh_private_key_param, "git_mgr.ssh_key_path")

    def test_create_repo_with_token_auth(self):
        """Test creating repository with token authentication"""
        repo = self.repo_model.create(
            {
                "name": "Token Repo",
                "repo_url": "https://github.com/company/repo.git",
                "branch": "main",
                "auth_type": "token",
                "token_param": "git_mgr.token.github",
            }
        )

        self.assertEqual(repo.auth_type, "token")
        self.assertEqual(repo.token_param, "git_mgr.token.github")

    def test_create_repo_invalid_url_format(self):
        """Test validation for invalid URL format"""
        with self.assertRaises(ValidationError):
            self.repo_model.create(
                {
                    "name": "Bad Repo",
                    "repo_url": "not-a-valid-url",
                    "branch": "main",
                    "auth_type": "none",
                }
            )

    def test_create_repo_with_path_traversal(self):
        """Test validation prevents path traversal in URL"""
        with self.assertRaises(ValidationError):
            self.repo_model.create(
                {
                    "name": "Malicious Repo",
                    "repo_url": "https://github.com/../../../etc/passwd",
                    "branch": "main",
                    "auth_type": "none",
                }
            )

    def test_token_auth_requires_param(self):
        """Test that token authentication requires token parameter"""
        with self.assertRaises(ValidationError):
            self.repo_model.create(
                {
                    "name": "Token Repo",
                    "repo_url": "https://github.com/test/repo.git",
                    "branch": "main",
                    "auth_type": "token",
                    # Missing token_param
                }
            )

    def test_ssh_auth_requires_param(self):
        """Test that SSH authentication requires key parameter"""
        with self.assertRaises(ValidationError):
            self.repo_model.create(
                {
                    "name": "SSH Repo",
                    "repo_url": "git@github.com:test/repo.git",
                    "branch": "main",
                    "auth_type": "ssh",
                    # Missing ssh_private_key_param
                }
            )

    def test_unique_constraint_url_branch(self):
        """Test unique constraint on repo_url and branch combination"""
        # Create first repo
        self.repo_model.create(
            {
                "name": "Repo 1",
                "repo_url": "https://github.com/test/repo.git",
                "branch": "main",
                "auth_type": "none",
            }
        )

        # Try to create duplicate
        with self.assertRaises(Exception):  # Unique constraint violation
            self.repo_model.create(
                {
                    "name": "Repo 2",
                    "repo_url": "https://github.com/test/repo.git",
                    "branch": "main",  # Same URL and branch
                    "auth_type": "none",
                }
            )

    def test_workspace_count_computation(self):
        """Test workspace count computed field"""
        repo = self.repo_model.create(
            {
                "name": "Test Repo",
                "repo_url": "https://github.com/test/repo.git",
                "branch": "main",
                "auth_type": "none",
            }
        )

        self.assertEqual(repo.workspace_count, 0)

        # Create entity link (which creates workspace)
        company = self.env["res.company"].search([], limit=1)
        link = self.env["git.entity.link"].create(
            {
                "entity_id": company.id,
                "repo_id": repo.id,
            }
        )

        repo.invalidate_recordset(["workspace_count"])
        self.assertEqual(repo.workspace_count, 1)

    def test_get_auth_config_none(self):
        """Test getting auth config for no authentication"""
        repo = self.repo_model.create(
            {
                "name": "Public Repo",
                "repo_url": "https://github.com/odoo/odoo.git",
                "branch": "main",
                "auth_type": "none",
            }
        )

        auth_config = repo._get_auth_config()
        self.assertEqual(auth_config["type"], "none")

    def test_get_auth_config_token(self):
        """Test getting auth config with token"""
        # Set up token in system parameters
        self.env["ir.config_parameter"].sudo().set_param(
            "git_mgr.token.test", "test_token_123"
        )

        repo = self.repo_model.create(
            {
                "name": "Token Repo",
                "repo_url": "https://github.com/test/repo.git",
                "branch": "main",
                "auth_type": "token",
                "token_param": "git_mgr.token.test",
            }
        )

        auth_config = repo._get_auth_config()
        self.assertEqual(auth_config["type"], "token")
        self.assertEqual(auth_config["token"], "test_token_123")
