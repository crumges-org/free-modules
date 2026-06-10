# -*- coding: utf-8 -*-
import re
import secrets
from uuid import uuid4

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class KnowledgeGuideBook(models.Model):
    """A book groups several documentation pages and can be published
    online through a secure tokenized URL.
    """
    _name = 'knowledge.guide.book'
    _description = 'Knowledge Guide Book'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
        help='Title of the book / guide.',
    )

    slug = fields.Char(
        string='Slug (URL)',
        required=True,
        index=True,
        help='Unique identifier used in the public URL '
             '(e.g. user-manual). Lowercase letters, digits and dashes only.',
    )

    description_html = fields.Html(
        string='Description / Introduction',
        sanitize=True,
        translate=True,
        help='Introduction shown at the top of the public guide.',
    )

    module_source = fields.Char(
        string='Module Source',
        help='Technical name of the module that provided this book '
             '(used for traceability).',
        readonly=True,
    )

    page_ids = fields.One2many(
        'knowledge.guide.page',
        'book_id',
        string='Pages',
        help='Pages composing this book.',
    )

    is_published = fields.Boolean(
        string='Published',
        default=False,
        help='If checked, the book is reachable through its public URL.',
    )

    access_token = fields.Char(
        string='Access Token',
        default=lambda self: str(uuid4()),
        required=True,
        copy=False,
        help='UUID token securing the public access to the book.',
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order (lower comes first).',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Allows archiving a book without deleting it.',
    )

    page_count = fields.Integer(
        string='Page count',
        compute='_compute_page_count',
        store=True,
        help='Number of active pages in this book.',
    )

    public_url = fields.Char(
        string='Public URL',
        compute='_compute_public_url',
        help='Full URL to access the public guide.',
    )

    link_tracker_id = fields.Many2one(
        'link.tracker',
        string='Tracked Link',
        ondelete='set null',
        copy=False,
        help='Associated link tracker used to measure visits to the public guide.',
    )

    tracked_url = fields.Char(
        string='Tracked URL',
        compute='_compute_tracked_url',
        help='Shortened tracked URL or public URL if no tracker is configured.',
    )

    click_count = fields.Integer(
        string='Visits',
        compute='_compute_click_count',
        help='Number of clicks recorded by the link tracker.',
    )

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------

    @api.depends('page_ids', 'page_ids.active')
    def _compute_page_count(self):
        for book in self:
            book.page_count = len(book.page_ids.filtered('active'))

    @api.depends('slug', 'access_token')
    def _compute_public_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for book in self:
            if book.slug and book.access_token:
                book.public_url = f'{base_url}/guide/{book.slug}?token={book.access_token}'
            else:
                book.public_url = False

    @api.depends('link_tracker_id', 'link_tracker_id.short_url', 'public_url')
    def _compute_tracked_url(self):
        for book in self:
            if book.link_tracker_id and book.link_tracker_id.short_url:
                book.tracked_url = book.link_tracker_id.short_url
            else:
                book.tracked_url = book.public_url or ''

    @api.depends('link_tracker_id', 'link_tracker_id.count')
    def _compute_click_count(self):
        for book in self:
            book.click_count = book.link_tracker_id.count if book.link_tracker_id else 0

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains('slug')
    def _check_slug_unique(self):
        for book in self:
            if not book.slug:
                continue
            duplicate = self.with_context(active_test=False).search([
                ('slug', '=', book.slug),
                ('id', '!=', book.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'The slug "%(slug)s" is already used by the book '
                    '"%(name)s". Please choose a unique slug.',
                    slug=book.slug, name=duplicate.name,
                ))

    @api.constrains('slug')
    def _check_slug_format(self):
        for book in self:
            if book.slug and not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', book.slug):
                raise ValidationError(_(
                    'The slug must contain only lowercase letters, digits '
                    'and dashes, and cannot start or end with a dash.'
                ))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_create_tracked_link(self):
        """Create or update the link.tracker associated with this book.

        A long random code (16 chars via token_urlsafe) is used to avoid
        bruteforce attacks on short link tracker codes.
        """
        self.ensure_one()
        if not self.public_url:
            return self._notify('warning', _('Error'),
                                _('Cannot create a tracked link: no public URL available.'))

        LinkTracker = self.env['link.tracker']

        if self.link_tracker_id:
            self.link_tracker_id.write({
                'url': self.public_url,
                'title': self.name,
            })
            message = _('The tracked link has been updated successfully.')
        else:
            secure_code = secrets.token_urlsafe(16)
            tracker = LinkTracker.create({
                'url': self.public_url,
                'title': self.name,
            })
            tracker.code = secure_code
            self.link_tracker_id = tracker.id
            message = _('The tracked link has been created successfully.')

        return self._notify('success', _('Success'), message)

    def action_regenerate_token(self):
        """Generate a brand new UUID token for the public link.

        If a link tracker exists, its URL is refreshed so it points to the new token.
        """
        for book in self:
            book.access_token = str(uuid4())
            if book.link_tracker_id:
                book.action_create_tracked_link()
        return True

    def action_publish(self):
        self.write({'is_published': True})
        return True

    def action_unpublish(self):
        self.write({'is_published': False})
        return True

    def action_open_public_url(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.public_url,
            'target': 'new',
        }

    def action_view_link_tracker_clicks(self):
        """Open the list of clicks recorded by the associated link tracker."""
        self.ensure_one()
        if not self.link_tracker_id:
            return self._notify('info', _('Information'),
                                _('No tracked link has been created yet for this book.'))

        return {
            'name': _('Visits - %s', self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'link.tracker.click',
            'view_mode': 'list,form',
            'domain': [('link_id', '=', self.link_tracker_id.id)],
            'context': {
                'create': False,
                'search_default_groupby_country_id': 1,
            },
            'views': [
                (self.env.ref('knowledge_guide.view_link_tracker_click_knowledge_guide_list').id, 'list'),
                (False, 'form'),
            ],
        }

    def action_send_guide_email(self):
        """Open the wizard used to send the guide link by email."""
        self.ensure_one()

        if not self.is_published:
            return self._notify('warning', _('Error'),
                                _('The book must be published before it can be sent by email.'))

        if not self.link_tracker_id:
            return self._notify(
                'warning', _('Warning'),
                _('We recommend generating a tracked link before sending the guide. '
                  'Click on "Generate tracked link" in the Sharing tab.'),
                sticky=True,
            )

        return {
            'name': _('Send the guide by email'),
            'type': 'ir.actions.act_window',
            'res_model': 'knowledge.guide.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_book_id': self.id,
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _notify(notif_type, title, message, sticky=False):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notif_type,
                'sticky': sticky,
            },
        }

    # ------------------------------------------------------------------
    # Display name
    # ------------------------------------------------------------------

    @api.depends('name', 'page_count')
    def _compute_display_name(self):
        for book in self:
            book.display_name = _('%(name)s (%(count)s pages)',
                                  name=book.name, count=book.page_count)
