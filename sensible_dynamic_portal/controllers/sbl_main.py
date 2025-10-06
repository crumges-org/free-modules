# Powered by Sensible Consulting Services
# -*- coding: utf-8 -*-
# © 2025 Sensible Consulting Services (<https://sensiblecs.com/>)
import ast
import re

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import content_disposition, request


class SblCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        sbl_dynamic_portals = request.env['sbl.dynamic.portal'].search([])
        for sbl_dynamic_portal in sbl_dynamic_portals:
            model_name = sbl_dynamic_portal.sbl_model_id.model
            ModelEnv = request.env[model_name]
            count_name = sbl_dynamic_portal.sbl_model_id.name.lower().replace(" ", "_") + "_count"
            domain = []
            if sbl_dynamic_portal.sbl_domain:
                domain = ast.literal_eval(sbl_dynamic_portal.sbl_domain)
            if count_name in counters:
                values[count_name] = ModelEnv.search_count(domain) if ModelEnv.has_access('read') else 0
        return values

    @http.route(['/my/<model("sbl.dynamic.portal"):sbl_dynamic_portal>/<string:model>',
                '/my/<model("sbl.dynamic.portal"):sbl_dynamic_portal>/<string:model>/page/<int:page>'], type="http", auth="user",
                website=True)
    def sbl_my_dynamic_portal_records(self, sbl_dynamic_portal, model, page=0, **kwargs):
        values = self._sbl_prepare_portal_rendering_values(sbl_dynamic_portal, model, page,
                                                           **kwargs)
        request.session['my_records_history'] = values['records'].ids[:100]
        return request.render("sensible_dynamic_portal.sbl_portal_my_details", values)

    def _sbl_get_searchbar_sortings(self, sbl_dynamic_portal):
        sort = {
            sbl_sortby.name: {'label': sbl_sortby.field_description, 'order': sbl_sortby.name}
            for sbl_sortby in sbl_dynamic_portal.sbl_sortby_ids}
        sort.update({'date': {'label': _('Create Date'), 'order': 'create_date desc'}})
        return sort

    def _sbl_prepare_portal_rendering_values(self, sbl_dynamic_portal, model, page, sortby=None, **kwargs):
        model_env = request.env[model]

        if not sortby:
            sortby = 'date'

        values = self._prepare_portal_layout_values()
        url = f"/my/{sbl_dynamic_portal.id}/model"

        domain = []
        if sbl_dynamic_portal.sbl_domain:
            domain = ast.literal_eval(sbl_dynamic_portal.sbl_domain)

        searchbar_sortings = self._sbl_get_searchbar_sortings(sbl_dynamic_portal)
        sort_order = searchbar_sortings[sortby]['order']
        pager_values = portal_pager(
            url=url,
            total=model_env.search_count(domain) if model_env.has_access('read') else 0,
            page=page,
            step=self._items_per_page,
            url_args={'sortby': sortby},
        )
        records = model_env.search(domain, order=sort_order, limit=self._items_per_page,
                                offset=pager_values['offset']) if model_env.has_access('read') else model_env

        values.update({
            'records': records.sudo(),
            'sbl_dynamic_portal': sbl_dynamic_portal.sudo(),
            'page_name': sbl_dynamic_portal.sbl_model_id.name,
            'pager': pager_values,
            'default_url': url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return values

    @http.route(['/my/<model("sbl.dynamic.portal"):sbl_dynamic_portal>/<string:model>/<int:record_id>'], type="http", auth="user",
                website=True)
    def sbl_my_dynamic_portal_record(self, sbl_dynamic_portal, model, record_id, **kwargs):
        try:
            record_sudo = self._document_check_access(model, record_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._sbl_get_page_view_values(record_sudo, sbl_dynamic_portal, **kwargs)

        return request.render("sensible_dynamic_portal.sbl_portal_my_detail", values)

    def _sbl_get_page_view_values(self, record, sbl_dynamic_portal, **kwargs):
        values = {
            'record': record.sudo(),
            'sbl_dynamic_portal': sbl_dynamic_portal,
            'page_name': sbl_dynamic_portal.sbl_model_id.name,
        }
        return self._get_page_view_values(record, False, values, 'my_records_history', False, **kwargs)

    @http.route(['/report/detail/<model("sbl.dynamic.portal"):sbl_dynamic_portal>/<string:model>/<int:record_id>/<string:report_type>'], type='http', auth="public", website=True)
    def sbl_report_detail(
        self,
        sbl_dynamic_portal,
        model,
        record_id,
        report_type='html',
        download=False,
        **kwargs
    ):
        try:
            record_sudo = self._document_check_access(model, record_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        return self._sbl_show_report(
            model=record_sudo,
            report_type=report_type,
            report_ref=sbl_dynamic_portal.sbl_report_id.report_name,
            download=download,
        )

    def _sbl_show_report(self, model, report_type, report_ref, download=False):
        if report_type not in ('html', 'pdf', 'text'):
            raise UserError(_("Invalid report type: %s", report_type))

        ReportAction = request.env['ir.actions.report'].sudo()

        if hasattr(model, 'company_id'):
            if len(model.company_id) > 1:
                raise UserError(_('Multi company reports are not supported.'))
            ReportAction = ReportAction.with_company(model.company_id)

        method_name = '_render_qweb_%s' % (report_type)
        pdf = getattr(ReportAction, method_name)(report_ref, list(model.ids), data={'report_type': report_type})[0]
        headers = self._sbl_get_http_headers(model, report_type, pdf, download)
        return request.make_response(pdf, headers=headers)

    def _sbl_get_http_headers(self, model, report_type, report, download):
        headers = {
            'Content-Type': 'application/pdf' if report_type == 'pdf' else 'text/html',
            'Content-Length': len(report),
        }
        if report_type == 'pdf' and download:
            if hasattr(model, '_get_report_base_filename'):
                filename = "%s.pdf" % (re.sub(r'\W+', '_', model._get_report_base_filename()))
            else:
                filename = "%s.pdf" % (re.sub(r'\W+', '_', model.display_name))
            headers['Content-Disposition'] = content_disposition(filename)
        return headers