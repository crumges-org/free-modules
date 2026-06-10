# -*- coding: utf-8 -*-
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install', 'knowledge_guide')
class TestKnowledgeGuidePublicRoutes(HttpCase):
    """Tests for the public HTTP routes of the knowledge guide."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Book = cls.env['knowledge.guide.book']
        cls.Page = cls.env['knowledge.guide.page']

    def _make_published_book(self, slug='public-book'):
        book = self.Book.create({
            'name': 'Public Book',
            'slug': slug,
            'is_published': True,
        })
        self.Page.create({
            'name': 'A page',
            'category': 'Default',
            'content_html': '<p>Hello reader</p>',
            'book_id': book.id,
        })
        return book

    def test_public_route_with_valid_token(self):
        """Hitting /guide/<slug>?token=<valid> returns 200 with the page content."""
        book = self._make_published_book(slug='valid-token-book')
        response = self.url_open(
            f'/guide/{book.slug}?token={book.access_token}',
            timeout=30,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Hello reader', response.text)

    def test_public_route_with_wrong_token_returns_404(self):
        """A wrong token must NOT grant access to the book."""
        book = self._make_published_book(slug='wrong-token-book')
        response = self.url_open(
            f'/guide/{book.slug}?token=not-the-real-token',
            timeout=30,
        )
        self.assertEqual(response.status_code, 404)

    def test_public_route_without_token_returns_404(self):
        """A request without any token must be rejected."""
        book = self._make_published_book(slug='no-token-book')
        response = self.url_open(
            f'/guide/{book.slug}',
            timeout=30,
        )
        self.assertEqual(response.status_code, 404)

    def test_public_route_unpublished_book_returns_404(self):
        """An existing but unpublished book must not be reachable."""
        book = self._make_published_book(slug='unpublished-book')
        book.is_published = False
        response = self.url_open(
            f'/guide/{book.slug}?token={book.access_token}',
            timeout=30,
        )
        self.assertEqual(response.status_code, 404)

    def test_public_page_route_with_valid_id(self):
        """The page-specific URL /guide/<slug>/<page_id>?token=... renders the page."""
        book = self._make_published_book(slug='page-route-book')
        page = book.page_ids[0]
        response = self.url_open(
            f'/guide/{book.slug}/{page.id}?token={book.access_token}',
            timeout=30,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Hello reader', response.text)
