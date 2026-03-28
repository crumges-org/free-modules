# -*- coding: utf-8 -*-

import logging
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "git_manager")
class TestAccessRights(TransactionCase):
    """Test cases for access rights and security"""

    def setUp(self):
        super().setUp()

        # Get groups
        self.group_admin = self.env.ref("base.group_system")
        self.group_user = self.env.ref("odoo_git_source_manager.group_git_manager_user")

        # Create test users
        self.admin_user = self.env["res.users"].create(
            {
                "name": "Git Admin",
                "login": "git_admin",
                "email": "git_admin@test.com",
                "groups_id": [(6, 0, [self.group_admin.id])],
            }
        )

        self.regular_user = self.env["res.users"].create(
            {
                "name": "Git User",
                "login": "git_user",
                "email": "git_user@test.com",
                "groups_id": [(6, 0, [self.group_user.id])],
            }
        )

        # Create test repository as admin
        self.test_repo = (
            self.env["git.source.repo"]
            .with_user(self.admin_user)
            .create(
                {
                    "name": "Test Repo",
                    "repo_url": "https://github.com/test/repo.git",
                    "branch": "main",
                    "auth_type": "none",
                }
            )
        )

    def test_admin_can_create_repo(self):
        """Test that admin can create repository"""
        repo = (
            self.env["git.source.repo"]
            .with_user(self.admin_user)
            .create(
                {
                    "name": "Admin Repo",
                    "repo_url": "https://github.com/admin/repo.git",
                    "branch": "main",
                    "auth_type": "none",
                }
            )
        )

        self.assertTrue(repo.id)
        self.assertEqual(repo.name, "Admin Repo")

    def test_user_cannot_create_repo(self):
        """Test that regular user cannot create repository"""
        with self.assertRaises(AccessError):
            self.env["git.source.repo"].with_user(self.regular_user).create(
                {
                    "name": "User Repo",
                    "repo_url": "https://github.com/user/repo.git",
                    "branch": "main",
                    "auth_type": "none",
                }
            )

    def test_user_can_read_repo(self):
        """Test that user can read repositories"""
        repo = (
            self.env["git.source.repo"]
            .with_user(self.regular_user)
            .browse(self.test_repo.id)
        )

        # Should be able to read
        self.assertEqual(repo.name, "Test Repo")
        self.assertEqual(repo.branch, "main")

    def test_user_cannot_write_repo(self):
        """Test that user cannot modify repositories"""
        with self.assertRaises(AccessError):
            repo = (
                self.env["git.source.repo"]
                .with_user(self.regular_user)
                .browse(self.test_repo.id)
            )
            repo.write({"name": "Modified Name"})

    def test_user_cannot_delete_repo(self):
        """Test that user cannot delete repositories"""
        with self.assertRaises(AccessError):
            repo = (
                self.env["git.source.repo"]
                .with_user(self.regular_user)
                .browse(self.test_repo.id)
            )
            repo.unlink()

    def test_admin_can_modify_repo(self):
        """Test that admin can modify repositories"""
        repo = (
            self.env["git.source.repo"]
            .with_user(self.admin_user)
            .browse(self.test_repo.id)
        )
        repo.write({"name": "Modified by Admin"})

        self.assertEqual(repo.name, "Modified by Admin")

    def test_admin_can_delete_repo(self):
        """Test that admin can delete repositories"""
        repo = (
            self.env["git.source.repo"]
            .with_user(self.admin_user)
            .create(
                {
                    "name": "Temp Repo",
                    "repo_url": "https://github.com/temp/repo.git",
                    "branch": "main",
                    "auth_type": "none",
                }
            )
        )

        repo_id = repo.id
        repo.unlink()

        # Verify deleted
        self.assertFalse(repo.exists())

    def test_user_can_create_entity_link(self):
        """Test that user can create entity links (limited write access)"""
        company = self.env["res.company"].search([], limit=1)

        # User should be able to create links
        link = (
            self.env["git.entity.link"]
            .with_user(self.regular_user)
            .create(
                {
                    "entity_id": company.id,
                    "repo_id": self.test_repo.id,
                }
            )
        )

        self.assertTrue(link.id)

    def test_user_cannot_modify_workspace(self):
        """Test that user cannot directly modify workspaces"""
        company = self.env["res.company"].search([], limit=1)
        link = (
            self.env["git.entity.link"]
            .with_user(self.admin_user)
            .create(
                {
                    "entity_id": company.id,
                    "repo_id": self.test_repo.id,
                }
            )
        )

        workspace = link.workspace_id

        with self.assertRaises(AccessError):
            workspace_as_user = (
                self.env["git.workspace"]
                .with_user(self.regular_user)
                .browse(workspace.id)
            )
            workspace_as_user.write({"status": "ok"})

    def test_user_can_read_logs(self):
        """Test that user can read update logs"""
        company = self.env["res.company"].search([], limit=1)
        link = (
            self.env["git.entity.link"]
            .with_user(self.admin_user)
            .create(
                {
                    "entity_id": company.id,
                    "repo_id": self.test_repo.id,
                }
            )
        )

        log = (
            self.env["git.update.log"]
            .with_user(self.admin_user)
            .create(
                {
                    "workspace_id": link.workspace_id.id,
                    "action": "pull",
                    "result": "success",
                    "message": "Test log",
                }
            )
        )

        # User should be able to read
        log_as_user = (
            self.env["git.update.log"].with_user(self.regular_user).browse(log.id)
        )
        self.assertEqual(log_as_user.message, "Test log")

    def test_user_cannot_delete_logs(self):
        """Test that user cannot delete logs"""
        company = self.env["res.company"].search([], limit=1)
        link = (
            self.env["git.entity.link"]
            .with_user(self.admin_user)
            .create(
                {
                    "entity_id": company.id,
                    "repo_id": self.test_repo.id,
                }
            )
        )

        log = (
            self.env["git.update.log"]
            .with_user(self.admin_user)
            .create(
                {
                    "workspace_id": link.workspace_id.id,
                    "action": "pull",
                    "result": "success",
                    "message": "Test log",
                }
            )
        )

        with self.assertRaises(AccessError):
            log_as_user = (
                self.env["git.update.log"].with_user(self.regular_user).browse(log.id)
            )
            log_as_user.unlink()
