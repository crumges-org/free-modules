# Part of Axoline Layout Editor. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


#: Store URL of the PRO add-on, surfaced to the editor for the upsell funnel.
AXOLINE_PRO_STORE_URL = 'https://apps.odoo.com/apps/modules/18.0/axoline_layout_editor_pro'


class AxolineLayoutEditorController(http.Controller):

    # ------------------------------------------------------------------
    #  Freemium helpers
    # ------------------------------------------------------------------

    def _axoline_is_pro(self):
        return request.env['ir.actions.report']._axoline_is_pro()

    def _axoline_free_template_ids(self):
        """System templates that are usable in the FREE version (Classic only)."""
        classic = request.env.ref(
            'axoline_layout_editor.template_classic', raise_if_not_found=False,
        )
        return classic.ids if classic else []

    def _axoline_template_is_locked(self, template):
        """A template is locked when PRO is missing, it is a system template
        and it is not the free Classic template. Custom (user) templates are
        always available."""
        if self._axoline_is_pro():
            return False
        if not template.is_system:
            return False
        return template.id not in self._axoline_free_template_ids()

    @http.route('/axoline_layout_editor/load', type='json', auth='user')
    def load_layout(self, layout_custom_id):
        layout = request.env['axoline.layout.custom'].browse(int(layout_custom_id))
        if not layout.exists():
            return {'error': 'Layout nicht gefunden.'}
        fmap = layout.get_field_map()
        return {
            'id': layout.id,
            'report_id': layout.report_id.id,
            'report_name': layout.report_id.name,
            'report_technical_name': layout.report_id.report_name,
            'model_name': layout.model_name,
            'layout_json': json.loads(layout.layout_json or '{"version":1,"blocks":[]}'),
            'block_types': layout.get_block_types(),
            'block_defaults': layout.get_block_defaults(),
            'field_map': fmap,
            'active': layout.active,
            'is_pro': self._axoline_is_pro(),
            'pro_store_url': AXOLINE_PRO_STORE_URL,
        }

    @http.route('/axoline_layout_editor/save', type='json', auth='user')
    def save_layout(self, layout_custom_id, layout_json, active=None):
        layout = request.env['axoline.layout.custom'].browse(int(layout_custom_id))
        if not layout.exists():
            return {'error': 'Layout nicht gefunden.'}
        vals = {'layout_json': json.dumps(layout_json, ensure_ascii=False)}
        if active is not None:
            vals['active'] = active
        layout.write(vals)
        return {'success': True}

    @http.route('/axoline_layout_editor/preview', type='http', auth='user')
    def preview_layout(self, layout_custom_id, record_id=None, **kwargs):
        """Render preview using the exact same QWeb pipeline as the PDF."""
        layout = request.env['axoline.layout.custom'].browse(int(layout_custom_id))
        if not layout.exists():
            return request.make_response(
                '<h1>Layout nicht gefunden</h1>',
                [('Content-Type', 'text/html')],
            )

        report = layout.report_id
        model = layout.model_name
        Model = request.env[model]

        if record_id:
            doc = Model.browse(int(record_id))
        else:
            doc = Model.search([], limit=1)

        if not doc.exists():
            body = (
                '<html><body style="padding:40px;font-family:sans-serif;">'
                '<h2>Keine Beispiel-Datensätze</h2>'
                '<p>Modell <code>%s</code> hat noch keine Datensätze.</p>'
                '</body></html>' % model
            )
            return request.make_response(body, [('Content-Type', 'text/html; charset=utf-8')])

        IrReport = request.env['ir.actions.report']
        html_bytes, _ = IrReport._render_axoline_layout(
            report, layout, doc.ids, data={},
        )
        if isinstance(html_bytes, bytes):
            html_str = html_bytes.decode('utf-8')
        else:
            html_str = str(html_bytes)

        layout_data = json.loads(layout.layout_json or '{}')
        m = layout_data.get('margins', {})
        margin_top = m.get('top', 10)
        margin_bottom = m.get('bottom', 20)
        margin_left = m.get('left', 7)
        margin_right = m.get('right', 7)

        inject_css = """<style>
        @page { size: A4; margin: 0; }
        html { background: #d0d0d0 !important; }
        body.o_body_html {
            background: #f0f0f0 !important;
            width: 210mm !important;
            max-width: 210mm !important;
            min-height: 297mm;
            margin: 20px auto !important;
            padding: 0 !important;
            box-shadow: 0 2px 20px rgba(0,0,0,.2);
            box-sizing: border-box;
            overflow-x: visible !important;
            position: relative;
        }
        body.container, body.container-fluid {
            max-width: 210mm !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
        #wrapwrap {
            padding: %(mt)smm %(mr)smm %(mb)smm %(ml)smm !important;
            background: #fff !important;
            margin: 0 !important;
            position: relative;
            min-height: 297mm;
            box-sizing: border-box;
        }
        #wrapwrap > main {
            padding: 0 !important;
            max-width: none !important;
            position: relative;
            border: 1px dashed #b0b0b0;
            min-height: calc(297mm - %(mt)smm - %(mb)smm);
        }

        /* Margin labels */
        #wrapwrap::before {
            content: '%(mt)s mm';
            position: absolute;
            top: %(mt_half)smm;
            left: 50%%;
            transform: translate(-50%%, -50%%);
            font-size: 9px;
            color: #999;
            font-family: sans-serif;
            z-index: 100;
        }
        #wrapwrap::after {
            content: '%(mb)s mm';
            position: absolute;
            bottom: %(mb_half)smm;
            left: 50%%;
            transform: translate(-50%%, 50%%);
            font-size: 9px;
            color: #999;
            font-family: sans-serif;
            z-index: 100;
        }
        #wrapwrap > main::before {
            content: '%(ml)s mm';
            position: absolute;
            top: 50%%;
            left: -%(ml)smm;
            width: %(ml)smm;
            text-align: center;
            transform: translateY(-50%%);
            font-size: 9px;
            color: #999;
            font-family: sans-serif;
            z-index: 100;
        }
        #wrapwrap > main::after {
            content: '%(mr)s mm';
            position: absolute;
            top: 50%%;
            right: -%(mr)smm;
            width: %(mr)smm;
            text-align: center;
            transform: translateY(-50%%);
            font-size: 9px;
            color: #999;
            font-family: sans-serif;
            z-index: 100;
        }
        </style>""" % {
            'mt': margin_top, 'mb': margin_bottom,
            'ml': margin_left, 'mr': margin_right,
            'mt_half': margin_top / 2, 'mb_half': margin_bottom / 2,
        }
        html_str = html_str.replace('</head>', inject_css + '</head>', 1)

        return request.make_response(html_str, [('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/axoline_layout_editor/footer/<int:layout_id>/<int:company_id>',
                type='http', auth='public')
    def render_footer(self, layout_id, company_id):
        """Serve footer HTML for wkhtmltopdf --footer-html."""
        layout = request.env['axoline.layout.custom'].sudo().browse(layout_id)
        if not layout.exists():
            return request.make_response('', [('Content-Type', 'text/html')])
        company = request.env['res.company'].sudo().browse(company_id)
        footer_html = layout._render_footer_html(company)
        return request.make_response(
            footer_html or '',
            [('Content-Type', 'text/html; charset=utf-8')],
        )

    # ------------------------------------------------------------------
    #  Template endpoints
    # ------------------------------------------------------------------

    @http.route('/axoline_layout_editor/templates', type='json', auth='user')
    def list_templates(self):
        Template = request.env['axoline.layout.template']
        templates = Template.search([])
        result = []
        for t in templates:
            result.append({
                'id': t.id,
                'name': t.name,
                'description': t.description or '',
                'category': t.category,
                'is_system': t.is_system,
                'has_thumbnail': bool(t.thumbnail),
                'locked': self._axoline_template_is_locked(t),
            })
        return result

    @http.route('/axoline_layout_editor/apply_template', type='json', auth='user')
    def apply_template(self, layout_custom_id, template_id):
        layout = request.env['axoline.layout.custom'].browse(int(layout_custom_id))
        if not layout.exists():
            return {'error': 'Layout nicht gefunden.'}
        template = request.env['axoline.layout.template'].browse(int(template_id))
        if not template.exists():
            return {'error': 'Vorlage nicht gefunden.'}
        if self._axoline_template_is_locked(template):
            return {
                'error': 'pro_required',
                'pro_store_url': AXOLINE_PRO_STORE_URL,
            }
        raw = template.layout_json or '{"version":1,"blocks":[]}'
        data = json.loads(raw)
        self._regenerate_block_ids(data.get('blocks', []))
        layout.write({
            'layout_json': json.dumps(data, ensure_ascii=False),
            'active': True,
        })
        return {
            'success': True,
            'layout_json': data,
        }

    @http.route('/axoline_layout_editor/save_as_template', type='json', auth='user')
    def save_as_template(self, layout_custom_id, name, description=''):
        layout = request.env['axoline.layout.custom'].browse(int(layout_custom_id))
        if not layout.exists():
            return {'error': 'Layout nicht gefunden.'}
        template = request.env['axoline.layout.template'].create({
            'name': name,
            'description': description,
            'layout_json': layout.layout_json,
            'category': 'custom',
            'is_system': False,
        })
        return {
            'success': True,
            'template_id': template.id,
        }

    def _regenerate_block_ids(self, blocks):
        """Give every block a fresh unique id so there are no collisions."""
        import uuid as _uuid
        for block in blocks:
            block['id'] = 'blk_' + _uuid.uuid4().hex[:12]
            settings = block.get('settings', {})
            for key in ('left_blocks', 'right_blocks'):
                sub = settings.get(key)
                if sub:
                    self._regenerate_block_ids(sub)

    # ------------------------------------------------------------------
    #  Template editor endpoints (visual editing of templates)
    # ------------------------------------------------------------------

    @http.route('/axoline_layout_editor/load_template', type='json', auth='user')
    def load_template(self, template_id):
        tpl = request.env['axoline.layout.template'].browse(int(template_id))
        if not tpl.exists():
            return {'error': 'Vorlage nicht gefunden.'}
        LayoutCustom = request.env['axoline.layout.custom']
        return {
            'id': tpl.id,
            'template_name': tpl.name,
            'is_system': tpl.is_system,
            'layout_json': json.loads(tpl.layout_json or '{"version":1,"blocks":[]}'),
            'block_types': LayoutCustom.get_block_types(),
            'block_defaults': LayoutCustom.get_block_defaults(),
        }

    @http.route('/axoline_layout_editor/save_template', type='json', auth='user')
    def save_template(self, template_id, layout_json):
        tpl = request.env['axoline.layout.template'].browse(int(template_id))
        if not tpl.exists():
            return {'error': 'Vorlage nicht gefunden.'}
        if tpl.is_system:
            return {'error': 'System-Vorlagen können nicht bearbeitet werden.'}
        tpl.write({'layout_json': json.dumps(layout_json, ensure_ascii=False)})
        return {'success': True}

    @http.route('/axoline_layout_editor/get_sample_records', type='json', auth='user')
    def get_sample_records(self, model_name, limit=20):
        """Return a list of sample records for the preview picker."""
        Model = request.env.get(model_name)
        if Model is None:
            return []
        records = Model.search([], limit=limit, order='id desc')
        return [{'id': r.id, 'name': r.display_name} for r in records]
