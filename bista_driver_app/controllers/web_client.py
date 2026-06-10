# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.webclient import WebClient


class WebsiteWebClient(WebClient):
    
    @http.route('/api/web/webclient/translations/<string:unique>', type='http', auth="public", cors="*")
    def fleet_translations(self, unique, mods=None, lang=None):
        return self.translations(unique=unique, mods=mods, lang=lang)
