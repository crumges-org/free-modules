from odoo import models, fields, api, exceptions
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class KnowledgeArticleVersion(models.Model):
    _name = 'knowledge.article.version'
    _description = 'Knowledge Article Version'
    _order = 'create_date desc'

    article_id = fields.Many2one('knowledge.article', string='Article', required=True, ondelete="cascade")
    version_number = fields.Integer(string="Version", required=True)
    content = fields.Html(string="Content Snapshot")
    create_date = fields.Datetime(string='Saved On', readonly=True)
    user_id = fields.Many2one('res.users', string="Saved By", default=lambda self: self.env.user, readonly=True)
    display_name = fields.Char(string="Name", compute="_compute_display_name", store=False)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.article_id.name} v{rec.version_number}"

    def action_compare_with_current(self):
        self.ensure_one()
        article = self.article_id

        current_version = self.env['knowledge.article.version'].search([
            ('article_id', '=', article.id),
        ], order='version_number desc', limit=1)

        if not current_version:
            raise UserError("Current version record not found.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Compare Versions',
            'res_model': 'knowledge.version.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_old_version_id': self.id,
                'default_current_version_id': current_version.id,
            }
        }

    @api.model
    def action_compare_selected_versions(self, records):
        if len(records) != 2:
            raise UserError("Please select exactly 2 versions to compare.")

        versions = sorted(records, key=lambda v: v.version_number)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'knowledge.version.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_article_id': versions[0].article_id.id,
                'default_old_version_id': versions[0].id,
                'default_current_version_id': versions[1].id,
            }
        }

class KnowledgeVersionCompareWizard(models.TransientModel):
    _name = 'knowledge.version.compare.wizard'
    _description = 'Compare Article Versions'

    article_id = fields.Many2one('knowledge.article', string='Current Article', required=True)
    old_version_id = fields.Many2one('knowledge.article.version', string='Old Version', required=True)
    current_version_id = fields.Many2one('knowledge.article.version', string="Current Version", required=True)
    current_content = fields.Html(string="Current Content", readonly=True)
    old_content = fields.Html(string="Previous Content", readonly=True)
    diff_html = fields.Html(string="Difference")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            old = self.env['knowledge.article.version'].browse(vals.get('old_version_id'))
            current = self.env['knowledge.article.version'].browse(vals.get('current_version_id'))

            vals.update({
                'old_content': old.content or '',
                'current_content': current.content or '',
                'diff_html': self._generate_diff_html(
                    old.content or '',
                    current.content or '',
                    old.version_number,
                    current.version_number
                ),
            })
        return super().create(vals_list)

    def _generate_diff_html(self, old, new, old_num=None, new_num=None):
        try:
            import difflib
            from bs4 import BeautifulSoup

            def strip_html(raw_html):
                soup = BeautifulSoup(raw_html or '', "html.parser")
                return soup.get_text()

            old_text = strip_html(old)
            new_text = strip_html(new)

            differ = difflib.HtmlDiff(tabsize=4, wrapcolumn=80)
            diff_table = differ.make_table(
                old_text.splitlines(),
                new_text.splitlines(),
                fromdesc=f'Version {old_num or "?"}',
                todesc=f'Version {new_num or "?"}',
                context=True,
                numlines=2
            )
            return f'<div class="o_diff_content">{diff_table}</div>'
        except Exception as e:
            return f"<p><strong>Unable to generate diff:</strong> {str(e)}</p>"
