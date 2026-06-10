# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KnowledgeGuideViewSourceWizard(models.TransientModel):
    """Read-only wizard that exposes the raw HTML source of a guide page.

    Useful when the rich-text editor sanitizes or rewrites the markup and
    the administrator wants to inspect or copy the underlying source.
    """
    _name = 'knowledge.guide.view.source.wizard'
    _description = 'Knowledge Guide HTML Source Wizard'

    page_id = fields.Many2one(
        'knowledge.guide.page',
        required=True,
    )
    source_code = fields.Text(
        string='HTML source',
        compute='_compute_source_code',
    )

    @api.depends('page_id')
    def _compute_source_code(self):
        for rec in self:
            rec.source_code = rec.page_id.content_html or ''
