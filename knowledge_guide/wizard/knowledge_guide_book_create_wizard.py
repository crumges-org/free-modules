# -*- coding: utf-8 -*-
import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class KnowledgeGuideBookCreateWizard(models.TransientModel):
    """Wizard to create a new book from a selection of existing pages.

    Triggered from the Knowledge Guide Pages list view, contextual
    "Action" menu. Pages already attached to another book block the
    creation: the user must release them or remove them from the
    selection.
    """
    _name = 'knowledge.guide.book.create.wizard'
    _description = 'Create Book from Selected Pages'

    name = fields.Char(
        string='Book name',
        required=True,
    )

    slug = fields.Char(
        string='Slug (URL)',
        required=True,
        help='Lowercase letters, digits and dashes only. '
             'Used in the public URL.',
    )

    page_ids = fields.Many2many(
        'knowledge.guide.page',
        string='Pages to add',
        default=lambda self: self._default_page_ids(),
    )

    blocked_page_ids = fields.Many2many(
        'knowledge.guide.page',
        'knowledge_guide_book_create_wizard_blocked_rel',
        'wizard_id', 'page_id',
        string='Pages already in another book',
        compute='_compute_blocked_page_ids',
    )

    has_blocked = fields.Boolean(compute='_compute_blocked_page_ids')

    def _default_page_ids(self):
        if self.env.context.get('active_model') != 'knowledge.guide.page':
            return [(6, 0, [])]
        return [(6, 0, self.env.context.get('active_ids') or [])]

    @api.depends('page_ids', 'page_ids.book_id')
    def _compute_blocked_page_ids(self):
        for wizard in self:
            blocked = wizard.page_ids.filtered(lambda p: p.book_id)
            wizard.blocked_page_ids = blocked
            wizard.has_blocked = bool(blocked)

    @api.onchange('name')
    def _onchange_name_set_slug(self):
        if self.name and not self.slug:
            slug = re.sub(r'[^a-z0-9]+', '-', self.name.lower()).strip('-')
            self.slug = slug or False

    def action_create_book(self):
        self.ensure_one()

        if not self.page_ids:
            raise ValidationError(_('Please select at least one page.'))

        blocked = self.page_ids.filtered(lambda p: p.book_id)
        if blocked:
            details = '\n'.join(
                _('- %(page)s (currently in: %(book)s)',
                  page=p.name, book=p.book_id.name)
                for p in blocked
            )
            raise ValidationError(_(
                'The following pages are already attached to another book '
                'and cannot be added:\n%(details)s\n\n'
                'Detach them from their current book first, or remove them '
                'from the selection.',
                details=details,
            ))

        book = self.env['knowledge.guide.book'].create({
            'name': self.name,
            'slug': self.slug,
        })
        self.page_ids.write({'book_id': book.id})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Book'),
            'res_model': 'knowledge.guide.book',
            'res_id': book.id,
            'view_mode': 'form',
            'target': 'current',
        }
