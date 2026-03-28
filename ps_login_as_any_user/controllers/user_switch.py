# -*- coding: utf-8 -*-

import odoo
from odoo import http
from odoo.http import request, root, Session
from odoo.addons.portal.controllers.portal import CustomerPortal, route
import logging

_logger = logging.getLogger(__name__)

class UserSwitch(http.Controller):
    """This is a controller to switch user and switch back to admin
        user_switch:
            this function is to check weather the user is admin or not
        switch_admin:
            function to switch back to admin
    """

    @http.route('/switch/user', type='json', auth='public')
    def user_switch(self):
        """
            Summary:
                function to check weather the user is admin
            Return:
                weather the current user is admin or not
        """
        return request.env.user.has_group("base.group_system")  # Administrator setting access

    @http.route('/switch/admin', type='json', auth='public')
    def switch_admin(self):
        """
            Summary:
                function to move back to admin
            Return:
                the home page to be loaded
                """
        session = request.session
        pre_user = request.env['res.users'].browse(session.previous_user)

        request.session['previous_user'] = request.env.user.id
        request.session.modified = True
        request.update_env(user=request.env.user)

        if pre_user and pre_user.has_group("base.group_system"):
            session.authenticate_without_password(request.env.cr.dbname,
                                                  pre_user.login, request.env)
            request.session.modified = True
            request.update_env(user=request.env.user)
            return {
                'type': 'ir.actions.act_url',
                'url': '/',
                'target': 'self'
            }
        return True


    @http.route('/switch/admin/portal', type='http', auth='public', website=True)
    def switch_admin_http(self, **kwargs):
        """
        Called from portal button click
        """
        session = request.session
        prev_user_id = session.get('previous_user')
        if not prev_user_id:
            return request.redirect('/my')

        pre_user = request.env['res.users'].sudo().browse(prev_user_id)

        current_user = request.env.user.sudo()
        if current_user.has_group("base.group_system"):
            request.session['previous_user'] = request.env.user.id

        request.session.modified = True
        request.update_env(user=request.env.user)

        if pre_user.has_group("base.group_system"):
            session.authenticate_without_password(
                request.env.cr.dbname,
                pre_user.login,
                request.env['res.users'].sudo().env  # ✅ safe env
            )
            return request.redirect('/web')

        return request.redirect('/my')

    @http.route('/user/check_previous_admin', type='json', auth='user')
    def check_previous_admin(self):
        """Return True if current session has a previous admin."""
        return request.env['res.users'].check_previous_admin_access()

    @http.route('/user/has_admin_group', type='json', auth='user')
    def has_admin_group(self):
        return request.env.user.has_group("base.group_system")

    @http.route('/', type='http', auth='public', website=True)
    def website_home(self, **kwargs):
        view = request.env.ref("ps_login_as_any_user.portal_back_to_admin")
        if view:
            view.clear_caches()

            prev_user = request.session.get('previous_user')
            curr_user = request.env.user.id

            show_back = request.env['res.users'].check_previous_admin_access() \
                        and prev_user and prev_user != curr_user

            request.update_context(show_back_to_admin=show_back)

            return request.render('website.homepage')


class CustomPortal(CustomerPortal):

    @route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):

        view = request.env.ref("ps_login_as_any_user.portal_back_to_admin")
        if view:
            view.clear_caches()

        values = self._prepare_portal_layout_values()
        values.update({
            'show_back_to_admin': request.env['res.users'].check_previous_admin_access(),
            'prs_user_id': request.session.get('previous_user'),
            'crt_user_id': request.env.user.id,
        })

        request.update_context(show_back_to_admin=values['show_back_to_admin'])

        return request.render("portal.portal_my_home", values)

