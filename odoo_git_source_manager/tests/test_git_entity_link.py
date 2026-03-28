# -*- coding: utf-8 -*-

import logging
from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "git_manager")
class TestGitEntityLink(TransactionCase):
    """Test cases for git.entity.link model"""

    def setUp(self):
        super().setUp()
        self.link_model = self.env["git.entity.link"]
        self.repo_model = self.env["git.source.repo"]

        # Create test repository
        self.test_repo = self.repo_model.create(
            {
                "name": "Test Repo",
                "repo_url": "https://github.com/test/repo.git",
                "branch": "main",
                "auth_type": "none",
            }
        )

        # Get test company
        self.test_company = self.env["res.company"].search([], limit=1)

    def test_create_entity_link(self):
        """Test creating entity link"""
        link = self.link_model.create(
            {
                "entity_id": self.test_company.id,
                "repo_id": self.test_repo.id,
            }
        )

        self.assertTrue(link.id)
        self.assertEqual(link.entity_id.id, self.test_company.id)
        self.assertEqual(link.repo_id.id, self.test_repo.id)
        self.assertTrue(link.enabled)

    def test_entity_link_creates_workspace(self):
        """Test that creating link automatically creates workspace"""
        link = self.link_model.create(
            {
                "entity_id": self.test_company.id,
                "repo_id": self.test_repo.id,
            }
        )

        self.assertTrue(link.workspace_id)
        self.assertEqual(link.workspace_id.entity_link_id.id, link.id)

    def test_workspace_path_computation(self):
        """Test workspace path computation"""
        link = self.link_model.create(
            {
                "entity_id": self.test_company.id,
                "repo_id": self.test_repo.id,
            }
        )

        self.assertTrue(link.workspace_path)
        self.assertIn(
            self.test_company.name.lower().replace(" ", "_"),
            link.workspace_path.lower(),
        )
        self.assertIn("test_repo", link.workspace_path.lower())

    def test_unique_constraint_entity_repo(self):
        """Test unique constraint on entity and repo combination"""
        # Create first link
        self.link_model.create(
            {
                "entity_id": self.test_company.id,
                "repo_id": self.test_repo.id,
            }
        )

        # Try to create duplicate
        with self.assertRaises(Exception):  # Unique constraint violation
            self.link_model.create(
                {
                    "entity_id": self.test_company.id,
                    "repo_id": self.test_repo.id,
                }
            )

    def test_name_computation(self):
        """Test name computed field"""
        link = self.link_model.create(
            {
                "entity_id": self.test_company.id,
                "repo_id": self.test_repo.id,
            }
        )

        expected_name = f"{self.test_company.name} - {self.test_repo.name}"
        self.assertEqual(link.name, expected_name)

    def test_sanitize_path_component(self):
        """Test path sanitization"""
        # Test various problematic characters
        test_cases = [
            ("Test Name", "test_name"),
            ("Test-Name", "test-name"),
            ("Test  Name", "test_name"),
            ("Test/Name", "test_name"),
            ("Test\\Name", "test_name"),
        ]

        for input_str, expected in test_cases:
            result = self.link_model._sanitize_path_component(input_str)
            self.assertEqual(result, expected)

    def test_sequence_ordering(self):
        """Test sequence field for ordering"""
        # Create another repo
        repo2 = self.repo_model.create(
            {
                "name": "Repo 2",
                "repo_url": "https://github.com/test/repo2.git",
                "branch": "main",
                "auth_type": "none",
            }
        )

        link1 = self.link_model.create(
            {
                "entity_id": self.test_company.id,
                "repo_id": self.test_repo.id,
                "sequence": 20,
            }
        )

        link2 = self.link_model.create(
            {
                "entity_id": self.test_company.id,
                "repo_id": repo2.id,
                "sequence": 10,
            }
        )

        # Search with order
        links = self.link_model.search(
            [("entity_id", "=", self.test_company.id)], order="sequence"
        )

        self.assertEqual(links[0].id, link2.id)
        self.assertEqual(links[1].id, link1.id)
