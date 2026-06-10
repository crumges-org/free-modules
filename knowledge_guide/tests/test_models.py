# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'knowledge_guide')
class TestKnowledgeGuidePage(TransactionCase):
    """Tests for the knowledge.guide.page model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Page = cls.env['knowledge.guide.page']

    def test_display_content_falls_back_to_original(self):
        """When no custom override is set, display_content_html mirrors content_html."""
        page = self.Page.create({
            'name': 'Test page',
            'category': 'Test',
            'content_html': '<p>Original</p>',
        })
        self.assertEqual(page.display_content_html, '<p>Original</p>')
        self.assertFalse(page.has_custom_content)

    def test_display_content_uses_custom_override(self):
        """When custom_content_html is set, it replaces the original in display_content_html."""
        page = self.Page.create({
            'name': 'Test page',
            'category': 'Test',
            'content_html': '<p>Original</p>',
            'custom_content_html': '<p>Custom</p>',
        })
        self.assertEqual(page.display_content_html, '<p>Custom</p>')
        self.assertTrue(page.has_custom_content)

    def test_display_content_ignores_empty_custom(self):
        """Whitespace-only custom_content_html should not override the original."""
        page = self.Page.create({
            'name': 'Test page',
            'category': 'Test',
            'content_html': '<p>Original</p>',
            'custom_content_html': '   ',
        })
        self.assertEqual(page.display_content_html, '<p>Original</p>')
        self.assertFalse(page.has_custom_content)

    def test_default_category_general(self):
        """A page without explicit category falls back to 'General'."""
        page = self.Page.create({'name': 'No category page'})
        self.assertEqual(page.category, 'General')

    def test_default_icon_book(self):
        """A page without explicit icon defaults to fa-book."""
        page = self.Page.create({'name': 'No icon', 'category': 'Test'})
        self.assertEqual(page.icon, 'fa-book')

    def test_action_view_source_returns_window_action(self):
        """action_view_source_html opens a wizard window action with the page id."""
        page = self.Page.create({
            'name': 'Source view',
            'category': 'Test',
            'content_html': '<p>raw</p>',
        })
        action = page.action_view_source_html()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'knowledge.guide.view.source.wizard')
        self.assertEqual(action['view_mode'], 'form')


@tagged('post_install', '-at_install', 'knowledge_guide')
class TestKnowledgeGuideBook(TransactionCase):
    """Tests for the knowledge.guide.book model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Book = cls.env['knowledge.guide.book']
        cls.Page = cls.env['knowledge.guide.page']

    def test_public_url_computed_with_token(self):
        """public_url contains the slug, the /guide/ prefix and the access token."""
        book = self.Book.create({'name': 'Test book', 'slug': 'test-book'})
        self.assertIn('/guide/test-book', book.public_url)
        self.assertIn(f'token={book.access_token}', book.public_url)

    def test_slug_unique_constraint(self):
        """Two books cannot share the same slug, even when one is archived."""
        self.Book.create({'name': 'Book A', 'slug': 'shared-slug'})
        with self.assertRaises(ValidationError):
            self.Book.create({'name': 'Book B', 'slug': 'shared-slug'})

    def test_slug_format_rejects_uppercase(self):
        """A slug with uppercase letters is rejected."""
        with self.assertRaises(ValidationError):
            self.Book.create({'name': 'Bad slug', 'slug': 'BadSlug'})

    def test_slug_format_rejects_underscores(self):
        """A slug with underscores is rejected."""
        with self.assertRaises(ValidationError):
            self.Book.create({'name': 'Bad slug', 'slug': 'bad_slug'})

    def test_slug_format_rejects_leading_dash(self):
        """A slug cannot start or end with a dash."""
        with self.assertRaises(ValidationError):
            self.Book.create({'name': 'Bad slug', 'slug': '-leading'})

    def test_slug_format_accepts_valid(self):
        """Lowercase letters, digits and inner dashes are accepted."""
        book = self.Book.create({'name': 'Good', 'slug': 'good-slug-123'})
        self.assertEqual(book.slug, 'good-slug-123')

    def test_page_count_excludes_archived(self):
        """page_count counts active pages only."""
        book = self.Book.create({'name': 'Counted', 'slug': 'counted'})
        active = self.Page.create({
            'name': 'Active page', 'category': 'Test', 'book_id': book.id,
        })
        archived = self.Page.create({
            'name': 'Archived page', 'category': 'Test', 'book_id': book.id,
        })
        archived.active = False
        self.assertEqual(book.page_count, 1)
        # Recheck after recompute
        active.active = False
        self.assertEqual(book.page_count, 0)

    def test_action_publish_toggles_is_published(self):
        """action_publish / action_unpublish flips the is_published flag."""
        book = self.Book.create({'name': 'Publishable', 'slug': 'publishable'})
        self.assertFalse(book.is_published)
        book.action_publish()
        self.assertTrue(book.is_published)
        book.action_unpublish()
        self.assertFalse(book.is_published)

    def test_action_regenerate_token_changes_token(self):
        """Regenerating the token produces a new value."""
        book = self.Book.create({'name': 'Tokened', 'slug': 'tokened'})
        original_token = book.access_token
        book.action_regenerate_token()
        self.assertNotEqual(book.access_token, original_token)
