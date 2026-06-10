# -*- coding: utf-8 -*-
from collections import OrderedDict

from odoo import http
from odoo.http import request
from werkzeug.exceptions import NotFound


class KnowledgeGuideController(http.Controller):
    """Controller for the knowledge guide.

    Provides JSON-RPC routes for the OWL backend client action and HTTP
    routes for the public consumption of published books.
    """

    # ==================================================================
    # Backend routes (JSON-RPC, auth='user')
    # ==================================================================

    @http.route('/knowledge_guide/get_pages', type='json', auth='user')
    def get_pages(self, search_term=None):
        """Return all pages the current user is allowed to see.

        Args:
            search_term (str, optional): text used to filter pages.

        Returns:
            dict: {
                'pages': [list of pages with their data],
                'categories': [unique categories]
            }
        """
        user = request.env.user
        user_groups = user.groups_id.ids

        domain = [
            ('active', '=', True),
            '|',
            ('group_ids', '=', False),
            ('group_ids', 'in', user_groups)
        ]

        if search_term:
            domain += [
                '|', '|',
                ('name', 'ilike', search_term),
                ('content_html', 'ilike', search_term),
                ('custom_content_html', 'ilike', search_term),
            ]

        pages = request.env['knowledge.guide.page'].search(domain)

        pages_data = []
        categories = set()

        for page in pages:
            pages_data.append({
                'id': page.id,
                'name': page.name,
                'content_html': page.display_content_html or '',
                'category': page.category,
                'icon': page.icon,
                'sequence': page.sequence,
                'module_source': page.module_source or '',
            })
            categories.add(page.category)

        return {
            'pages': pages_data,
            'categories': sorted(list(categories))
        }

    @http.route('/knowledge_guide/get_page', type='json', auth='user')
    def get_page(self, page_id):
        """Return a single page by ID, applying group-based access control."""
        user = request.env.user
        user_groups = user.groups_id.ids

        page = request.env['knowledge.guide.page'].browse(page_id)

        if not page.exists() or not page.active:
            return False

        if page.group_ids and not any(g.id in user_groups for g in page.group_ids):
            return False

        return {
            'id': page.id,
            'name': page.name,
            'content_html': page.display_content_html or '',
            'category': page.category,
            'icon': page.icon,
            'sequence': page.sequence,
            'module_source': page.module_source or '',
        }

    # ==================================================================
    # Public routes (HTTP, auth='public')
    # ==================================================================

    def _get_published_book(self, slug, token):
        """Fetch a published book and validate its access token.

        sudo() is justified here because the access is public; security
        relies on the unguessable UUID token.
        """
        if not token:
            raise NotFound()

        Book = request.env['knowledge.guide.book'].sudo()
        book = Book.search([
            ('slug', '=', slug),
            ('is_published', '=', True),
            ('active', '=', True),
        ], limit=1)

        if not book or book.access_token != token:
            raise NotFound()

        return book

    def _get_book_pages_by_category(self, book):
        """Group the active pages of a book by category."""
        pages = book.page_ids.filtered('active').sorted(
            key=lambda p: (p.sequence, p.name)
        )
        categories = OrderedDict()
        for page in pages:
            cat = page.category or 'General'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(page)
        return categories, pages

    @http.route(
        '/guide/<string:slug>',
        type='http',
        auth='public',
        website=False,
        csrf=False,
    )
    def guide_book_public(self, slug, token=None, **kwargs):
        """Render a published guide with the first page selected.

        URL: /guide/<slug>?token=<uuid>
        """
        book = self._get_published_book(slug, token)
        categories, all_pages = self._get_book_pages_by_category(book)

        selected_page = all_pages[0] if all_pages else None
        prev_page, next_page = self._get_prev_next(all_pages, selected_page)

        return self._render_guide(book, categories, all_pages, selected_page,
                                   prev_page, next_page, token)

    @http.route(
        '/guide/<string:slug>/<int:page_id>',
        type='http',
        auth='public',
        website=False,
        csrf=False,
    )
    def guide_page_public(self, slug, page_id, token=None, **kwargs):
        """Render a specific page of a published guide.

        URL: /guide/<slug>/<page_id>?token=<uuid>
        """
        book = self._get_published_book(slug, token)
        categories, all_pages = self._get_book_pages_by_category(book)

        selected_page = request.env['knowledge.guide.page'].sudo().browse(page_id)
        if not selected_page.exists() or selected_page.book_id != book or not selected_page.active:
            raise NotFound()

        prev_page, next_page = self._get_prev_next(all_pages, selected_page)

        return self._render_guide(book, categories, all_pages, selected_page,
                                   prev_page, next_page, token)

    def _render_guide(self, book, categories, all_pages, selected_page,
                      prev_page, next_page, token):
        """Render the public template prefixed with an HTML5 doctype.

        The DOCTYPE is not included in the QWeb template (it is not valid
        XML), so we prepend it manually to the rendered HTML.
        """
        response = request.render('knowledge_guide.guide_book_public', {
            'book': book,
            'categories': categories,
            'all_pages': all_pages,
            'selected_page': selected_page,
            'prev_page': prev_page,
            'next_page': next_page,
            'token': token,
        })
        response.flatten()
        html_content = response.data
        if isinstance(html_content, bytes):
            html_content = html_content.decode('utf-8')
        html_content = '<!DOCTYPE html>\n' + html_content
        response.data = html_content.encode('utf-8')
        return response

    def _get_prev_next(self, all_pages, selected_page):
        """Return (previous_page, next_page) for in-guide navigation."""
        if not selected_page or not all_pages:
            return None, None

        page_list = list(all_pages)
        try:
            idx = page_list.index(selected_page)
        except ValueError:
            return None, None

        prev_page = page_list[idx - 1] if idx > 0 else None
        next_page = page_list[idx + 1] if idx < len(page_list) - 1 else None
        return prev_page, next_page
