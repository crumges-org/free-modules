# Powered by SCRIMO GmbH
# -*- coding: utf-8 -*-
# © 2025 SCRIMO GmbH (<http://www.scrimo.com>)
import ast
from odoo.http import request, route
from odoo import http, _
from odoo.addons.sensible_dynamic_portal.controllers.sbl_main import SblCustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError


class SblMyDashboard(CustomerPortal):
    _sbl_items_per_page = 50

    @route(['/my/dashboard'], type='http', auth="user", website=True)
    def my_dashboard(self, **kw):
        SblDynamicPortalDashboard = request.env['sbl.dynamic.portal'].search([])
        records = request.env['sbl.dynamic.portal']
        dynamic_portal_records = SblDynamicPortalDashboard.search([]) if SblDynamicPortalDashboard.has_access(
            'read') else SblDynamicPortalDashboard
        for sbl_dynamic_portal in dynamic_portal_records:
            model_env = request.env[sbl_dynamic_portal.sbl_model_id.model]
            if model_env.has_access('read'):
                records |= sbl_dynamic_portal.sudo()

        values = {
            'records': records.sudo() if records else False,
            'page_name': 'home'
        }
        return request.render("sensible_dynamic_portal_dashboard.sbl_portal_my_dashboard", values)

    @route(['/my/dashboard/<model("sbl.dynamic.portal"):sbl_dynamic_portal>'], type="http",
           auth="user", website=True)
    def sbl_my_dynamic_portal_dashboard_record(self, sbl_dynamic_portal, **kwargs):

        values = {
            'sbl_dynamic_portal': sbl_dynamic_portal,
            'page_name': sbl_dynamic_portal.sbl_model_id.name,
        }

        return request.render("sensible_dynamic_portal_dashboard.sbl_portal_my_dashboard_detail", values)

    @route(
        ['/my/dashboard/<model("sbl.dynamic.portal"):sbl_dynamic_portal>/<model("sbl.dynamic.portal.kpis.line"):record>',
         '/my/dashboard/<model("sbl.dynamic.portal"):sbl_dynamic_portal>/<model("sbl.dynamic.portal.kpis.line"):record>/page/<int:page>'],
        type="http", auth="user", website=True)
    def sbl_my_dynamic_portal_dashboard_record_detail(self, sbl_dynamic_portal, record, page=0, **kwargs):
        try:
            record_sudo = self._document_check_access("sbl.dynamic.portal.kpis.line", record.id)
        except (AccessError, MissingError):
            return request.redirect('/my/dashboard')
        values = self._sbl_prepare_portal_dashboard_rendering_values(sbl_dynamic_portal, record_sudo, page)

        return request.render("sensible_dynamic_portal_dashboard.sbl_portal_my_dashboard_record_detail", values)

    def _sbl_dashboard_get_searchbar_sortings(self):
        sort = {}
        sort.update({'date': {'label': _('Create Date'), 'order': 'create_date desc'}})
        return sort

    def _sbl_prepare_portal_dashboard_rendering_values(self, sbl_dynamic_portal, record, page, sortby=None,
                                                       **kwargs):
        model_env = request.env[sbl_dynamic_portal.sbl_model_id.model]

        if not sortby:
            sortby = 'date'

        values = self._prepare_portal_layout_values()
        url = f"/my/dashboard/{sbl_dynamic_portal.id}/{record.id}"

        domain = []
        if record.sbl_domain:
            domain = ast.literal_eval(record.sbl_domain)

        searchbar_sortings = self._sbl_dashboard_get_searchbar_sortings()
        sort_order = searchbar_sortings[sortby]['order']
        pager_values = portal_pager(
            url=url,
            total=model_env.search_count(domain) if model_env.has_access('read') else 0,
            page=page,
            step=self._sbl_items_per_page,
            url_args={'sortby': sortby},
        )
        records = model_env.search(domain, order=sort_order, limit=self._sbl_items_per_page,
                                   offset=pager_values['offset']) if model_env.has_access('read') else model_env

        values.update({
            'records': records.sudo(),
            'sbl_dynamic_portal': sbl_dynamic_portal.sudo(),
            'record': record,
            'page_name': sbl_dynamic_portal.sbl_model_id.name,
            'pager': pager_values,
            'default_url': url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return values

    @http.route('/get_chart_info', type="json", auth="user")
    def get_chart_info(self, sbl_dynamic_portal_id=None):
        if not sbl_dynamic_portal_id:
            return []

        records = request.env['sbl.dynamic.portal.kpis.line'].search([('sbl_dynamic_portal_dashboard_id', '=', int(sbl_dynamic_portal_id))])
        vals = []
        for record in records:
            domain = ast.literal_eval(record.sbl_domain or '[]')
            model_name = record.sbl_dynamic_portal_dashboard_id.sbl_model_id.model

            if model_name:
                model = request.env[model_name]
                count = model.search_count(domain)

                vals.append({
                    'label': record.name,
                    'value': count,
                    'backgroundColor': record.sbl_chart_color
                })
        return vals


class SblCustomerPortalDashboard(SblCustomerPortal):

    def _sbl_prepare_portal_rendering_values(self, sbl_dynamic_portal, model, page, sortby=None, kpi=None, **kwargs):
        model_env = request.env[model]

        if not sortby:
            sortby = 'date'

        values = self._prepare_portal_layout_values()
        url = f"/my/{sbl_dynamic_portal.id}/model"

        domain = []
        if sbl_dynamic_portal.sbl_domain:
            domain = ast.literal_eval(sbl_dynamic_portal.sbl_domain)
        if kpi:
            line = request.env['sbl.dynamic.portal.kpis.line'].sudo().search([('id', '=', int(kpi))])
            domain += ast.literal_eval(line.sbl_domain)

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
