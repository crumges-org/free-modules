"""HTTP endpoints for impersonation.

Impersonation is the most abusable feature in this category, so the checks live
here rather than only on the button that leads here: a route is reachable by URL
whether or not the button was rendered. Everything is re-verified server-side,
and the audit row is written before the switch happens.
"""

import logging

from odoo import _, http
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)

#: Session key holding the real administrator while impersonating.
IMPERSONATOR_KEY = 'aam_impersonator_uid'


class AamController(http.Controller):

    @http.route('/aam/impersonate/<int:user_id>', type='http', auth='user',
                methods=['GET'], sitemap=False)
    def impersonate(self, user_id, **kwargs):
        """Switch this session to another user.

        Reuses ``Session.finalize`` so the session token is computed exactly the
        way a normal login computes it - hand-rolling that is how impersonation
        features end up accepting stale tokens.
        """
        env = request.env
        actor = env.user

        if not actor.has_group('base.group_system') or \
                not actor.has_group('odooapp_access_management.group_aam_manager'):
            _logger.warning(
                "Refused impersonation of uid %s by uid %s: insufficient rights",
                user_id, actor.id)
            raise AccessDenied(_("You are not allowed to sign in as another user."))

        target = env['res.users'].sudo().browse(user_id).exists()
        if not target:
            raise AccessDenied(_("No such user."))
        if target._is_system():
            raise AccessDenied(_(
                "Signing in as another administrator is not allowed."))
        if not target.active or target.share:
            raise AccessDenied(_("You can only sign in as an active internal user."))

        env['aam.audit.log'].sudo()._log(
            'impersonate', user_id=actor.id,
            detail=_("%(who)s signed in as %(target)s",
                     who=actor.name, target=target.name))

        original_uid = actor.id
        session = request.session
        session['pre_login'] = target.login
        session['pre_uid'] = target.id
        session.finalize(env)
        # Set after finalize: it clears pre_* but not our own key, and we want
        # the way back to survive the switch.
        session[IMPERSONATOR_KEY] = original_uid

        return request.redirect('/odoo')

    @http.route('/aam/impersonate/stop', type='http', auth='user',
                methods=['GET'], sitemap=False)
    def stop_impersonating(self, **kwargs):
        """Return to the administrator who started impersonating."""
        session = request.session
        original_uid = session.get(IMPERSONATOR_KEY)
        if not original_uid:
            return request.redirect('/odoo')

        original = request.env['res.users'].sudo().browse(original_uid).exists()
        if not original or not original.active:
            # Nothing safe to return to - end the session instead of guessing.
            session.logout(keep_db=True)
            return request.redirect('/web/login')

        request.env['aam.audit.log'].sudo()._log(
            'impersonate', user_id=original_uid,
            detail=_("%s returned to their own account", original.name))

        session.pop(IMPERSONATOR_KEY, None)
        session['pre_login'] = original.login
        session['pre_uid'] = original.id
        session.finalize(request.env)
        return request.redirect('/odoo')
