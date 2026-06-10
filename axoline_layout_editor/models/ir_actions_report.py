# Part of Axoline Layout Editor. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#: Store URL of the PRO add-on, used for the upsell funnel in the FREE version.
AXOLINE_PRO_STORE_URL = 'https://apps.odoo.com/apps/modules/18.0/axoline_layout_editor_pro'


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    axoline_is_locked = fields.Boolean(
        string='Axoline PRO Required',
        compute='_compute_axoline_is_locked',
        help='Technical flag: this QWeb PDF report can only be edited with '
             'the Axoline Layout Editor PRO add-on.',
    )

    @api.depends('report_type', 'model')
    def _compute_axoline_is_locked(self):
        allowed = self._axoline_allowed_models()
        for rec in self:
            rec.axoline_is_locked = bool(
                allowed
                and rec.report_type == 'qweb-pdf'
                and rec.model not in allowed
            )

    # ------------------------------------------------------------------
    #  Freemium hooks (overridden by axoline_layout_editor_pro)
    # ------------------------------------------------------------------

    @api.model
    def _axoline_is_pro(self):
        """Return True when the PRO add-on is installed.

        The PRO module inherits this method and returns True, which removes
        every restriction enforced by the FREE version.
        """
        return False

    @api.model
    def _axoline_allowed_models(self):
        """Models that may be edited in the FREE version.

        An empty list means "no restriction" (PRO). The FREE version only
        allows customer/vendor documents on ``account.move`` (invoices).
        """
        if self._axoline_is_pro():
            return []
        return ['account.move']

    @api.model
    def _axoline_upsell_action(self, message=None):
        """Return a notification action pointing to the PRO module."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('PRO feature'),
                'message': message or _(
                    'Editing this document type is available in the '
                    'Axoline PDF Report Designer PRO add-on.'
                ),
                'type': 'warning',
                'sticky': True,
                'links': [{
                    'label': _('Get the PRO add-on'),
                    'url': AXOLINE_PRO_STORE_URL,
                }],
            },
        }

    def action_axoline_open_pro_store(self):
        """Open the PRO add-on page on the Odoo App Store in a new tab."""
        return {
            'type': 'ir.actions.act_url',
            'url': AXOLINE_PRO_STORE_URL,
            'target': 'new',
        }

    def action_axoline_open_layout_editor(self):
        """Open the visual drag-and-drop layout editor as a client action."""
        self.ensure_one()
        if self.report_type != 'qweb-pdf':
            raise UserError(
                _('Only reports of type "PDF (QWeb)" can be edited.'),
            )
        allowed = self._axoline_allowed_models()
        if allowed and self.model not in allowed:
            return self._axoline_upsell_action()
        custom = self.env['axoline.layout.custom'].search(
            [('report_id', '=', self.id)], limit=1,
        )
        if not custom:
            custom = self.env['axoline.layout.custom'].create({
                'report_id': self.id,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'axoline_layout_editor',
            'name': _('Layout: %s') % self.name,
            'params': {
                'layout_custom_id': custom.id,
                'report_id': self.id,
            },
        }

    # ------------------------------------------------------------------
    #  Rendering hook: use custom layout when active
    # ------------------------------------------------------------------

    @api.model
    def _render_qweb_html(self, report_ref, docids, data=None):
        report = self._get_report(report_ref)
        allowed = self._axoline_allowed_models()
        if allowed and report.model not in allowed:
            # FREE version: never apply a custom layout for restricted models
            # (e.g. a layout saved while PRO was installed).
            return super()._render_qweb_html(report_ref, docids, data=data)
        layout = self.env['axoline.layout.custom'].sudo().search([
            ('report_id', '=', report.id),
            ('active', '=', True),
        ], limit=1)
        if layout and layout.get_blocks():
            return self._render_axoline_layout(report, layout, docids, data)
        return super()._render_qweb_html(report_ref, docids, data=data)

    def _render_axoline_layout(self, report, layout, docids, data):
        """Render using the Axoline layout editor JSON → QWeb master template."""
        if not data:
            data = {}
        data.setdefault('report_type', 'html')
        report_model = self._get_rendering_context_model(report)
        data = data and dict(data) or {}
        if report_model is not None:
            data.update(report_model._get_report_values(docids, data=data))
        else:
            docs = self.env[report.model].browse(docids)
            data.update({
                'doc_ids': docids,
                'doc_model': report.model,
                'docs': docs,
            })

        # Build a company map so the template doesn't need hasattr()
        docs = data.get('docs', self.env[report.model].browse(docids))
        fallback_company = self.env.company
        company_map = {}
        for doc in docs:
            try:
                company_map[doc.id] = doc.company_id or fallback_company
            except Exception:
                company_map[doc.id] = fallback_company

        data['axoline_layout'] = layout
        data['axoline_blocks'] = layout.get_blocks()
        data['axoline_company_map'] = company_map
        data['axoline_fallback_company'] = fallback_company

        layout_data = json.loads(layout.layout_json or '{}')
        m = layout_data.get('margins', {})
        data['data_report_margin_top'] = m.get('top', 10)
        data['data_report_margin_bottom'] = m.get('bottom', 20)
        data['data_report_margin_left'] = m.get('left', 7)
        data['data_report_margin_right'] = m.get('right', 7)
        data['data_report_header_spacing'] = 0

        from markupsafe import Markup as M
        footer_inner = layout._render_footer_inner_html(fallback_company)
        data['axoline_footer_html'] = M(footer_inner) if footer_inner else ''

        template = 'axoline_layout_editor.report_axoline_master'
        return self._render_template(template, data), 'html'

    # ------------------------------------------------------------------
    #  Extend wkhtmltopdf args to support margin-left and margin-right
    # ------------------------------------------------------------------

    def _build_wkhtmltopdf_args(
        self, paperformat_id, landscape,
        specific_paperformat_args=None, set_viewport_size=False,
    ):
        command_args = super()._build_wkhtmltopdf_args(
            paperformat_id, landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
        if not specific_paperformat_args:
            return command_args
        if 'data-report-margin-left' in specific_paperformat_args:
            try:
                idx = command_args.index('--margin-left')
                command_args[idx + 1] = str(specific_paperformat_args['data-report-margin-left'])
            except ValueError:
                command_args.extend(['--margin-left', str(specific_paperformat_args['data-report-margin-left'])])
        if 'data-report-margin-right' in specific_paperformat_args:
            try:
                idx = command_args.index('--margin-right')
                command_args[idx + 1] = str(specific_paperformat_args['data-report-margin-right'])
            except ValueError:
                command_args.extend(['--margin-right', str(specific_paperformat_args['data-report-margin-right'])])
        return command_args
