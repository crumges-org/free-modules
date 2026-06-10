# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class KnowledgeGuidePage(models.Model):
    """A documentation page belonging to a knowledge guide book.

    Each page represents a section of the guide with HTML content,
    a category and the user groups allowed to view it.

    A page can hold both an original content (typically shipped by the
    source module via XML data) and a custom override entered by the
    administrator. The displayed content is the override when present,
    otherwise the original.
    """
    _name = 'knowledge.guide.page'
    _description = 'Knowledge Guide Page'
    _order = 'sequence, category, name'

    name = fields.Char(
        string='Title',
        required=True,
        translate=True,
        help='Title of the section displayed in the guide.',
    )

    content_html = fields.Html(
        string='Original content',
        sanitize=True,
        sanitize_form=False,
        translate=True,
        help='Content provided by the source module. '
             'Treat as read-only when a module source is set.',
    )

    custom_content_html = fields.Html(
        string='Custom content',
        sanitize=True,
        sanitize_form=False,
        translate=True,
        help='Content written by the administrator. '
             'When set, it replaces the original content in the displayed guide.',
    )

    display_content_html = fields.Html(
        string='Displayed content',
        compute='_compute_display_content_html',
        sanitize=False,
    )

    has_custom_content = fields.Boolean(
        compute='_compute_display_content_html',
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order (lower comes first).',
    )

    category = fields.Char(
        string='Category',
        required=True,
        default='General',
        translate=True,
        help='Section / category of the page (e.g. General, Sales, Inventory).',
    )

    module_source = fields.Char(
        string='Module Source',
        help='Technical name of the module providing this page (for traceability).',
        readonly=True,
    )

    group_ids = fields.Many2many(
        'res.groups',
        string='Allowed Groups',
        help='If empty, the page is visible to everyone. '
             'Otherwise only users belonging to one of these groups can see it.',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Allows archiving sections without deleting them.',
    )

    icon = fields.Char(
        string='Icon',
        default='fa-book',
        help='FontAwesome class for the icon (e.g. fa-book, fa-cog, fa-user).',
    )

    book_id = fields.Many2one(
        'knowledge.guide.book',
        string='Book',
        ondelete='set null',
        index=True,
        help='Book this page belongs to (optional).',
    )

    @api.depends('content_html', 'custom_content_html')
    def _compute_display_content_html(self):
        for record in self:
            if record.custom_content_html and record.custom_content_html.strip():
                record.display_content_html = record.custom_content_html
                record.has_custom_content = True
            else:
                record.display_content_html = record.content_html
                record.has_custom_content = False

    def action_view_source_html(self):
        """Open a transient wizard that shows the raw HTML of this page."""
        self.ensure_one()
        wizard = self.env['knowledge.guide.view.source.wizard'].create({
            'page_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('HTML source'),
            'res_model': 'knowledge.guide.view.source.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.depends('name', 'category')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.category}] {record.name}"
