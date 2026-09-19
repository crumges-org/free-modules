# -*- coding: utf-8 -*-
# Part of the Codfy module suite for Odoo. See LICENSE file for full terms.
# Copyright (C) 2026 Codfy (https://www.codfy.mx)
# License: LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.http import request

ASSET_FIELDS = ('logo', 'background_image')

TEXT_OVERRIDES = ('layout', 'card_mode', 'primary_color', 'bg_start', 'bg_end',
                  'headline', 'tagline', 'footer_note')
INT_OVERRIDES = ('radius', 'logo_height', 'overlay')
BOOL_OVERRIDES = ('use_own_logo', 'show_reset_password', 'show_signup',
                  'show_db_selector', 'show_db_manager')


class LoginTheme(http.Controller):

    @http.route('/c_login_theme/asset/<string:field>', type='http', auth='public', methods=['GET'])
    def login_theme_asset(self, field, **kwargs):
        """Sirve el logo y la imagen de fondo a quien todavía no ha iniciado sesión."""
        if field not in ASSET_FIELDS:
            raise NotFound()
        theme = request.env['c.login.theme'].sudo().search([], limit=1)
        if not theme or not theme[field]:
            raise NotFound()
        stream = request.env['ir.binary']._get_image_stream_from(theme, field)
        response = stream.get_response()
        response.headers['Cache-Control'] = 'public, max-age=604800'
        return response

    @http.route('/c_login_theme/preview', type='http', auth='user', methods=['GET'])
    def login_theme_preview(self, **kwargs):
        """Pantalla de acceso de mentira, para verla mientras se elige el tema."""
        if not request.env.user.has_group('base.group_system'):
            raise Forbidden()
        theme = request.env['c.login.theme'].sudo()._render_context(self._preview_overrides(kwargs))
        page = request.env['ir.qweb']._render('c_login_theme.preview_page', {
            'theme': theme,
            'db': request.db,
        })
        return request.make_response('<!DOCTYPE html>\n' + str(page), headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])

    def _preview_overrides(self, kwargs):
        overrides = {'enabled': True}
        for key in TEXT_OVERRIDES:
            if key in kwargs:
                overrides[key] = kwargs[key]
        for key in INT_OVERRIDES:
            if key in kwargs:
                try:
                    overrides[key] = int(kwargs[key])
                except (TypeError, ValueError):
                    continue
        for key in BOOL_OVERRIDES:
            if key in kwargs:
                overrides[key] = kwargs[key] in ('1', 'true', 'True')
        if not overrides.get('use_own_logo', True):
            overrides['logo_url'] = ''
        return overrides
