# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class EasyLanguageSelector(http.Controller):

    @http.route('/get_idle_time/timer', auth='public', type='json')
    def get_idle_time(self):
        if request.env.user.enable_idle:
            return request.env.user.idle_time
