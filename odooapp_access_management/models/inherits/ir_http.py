from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _handle_debug(cls):
        """Refuse to turn developer mode on from the URL (feature H2).

        ``?debug=1`` is the only way debug gets into the session, so blocking it
        here is the whole feature - there is no client switch to hide. Stripping
        it from ``session_info`` alone would not be enough: the user could
        re-enable it on the next request.
        """
        super()._handle_debug()
        if not request or not request.session.debug:
            return
        env = request.env
        if env.su or not env.uid:
            return
        if env['aam.policy'].get_policy()['globals'].get('disable_developer_mode'):
            request.session.debug = ''

    def session_info(self):
        """Ship the client policy at boot.

        Loading it with the session beats an RPC per view: the web client needs
        it before the first view renders, and a round trip would show a flash of
        un-restricted UI.
        """
        info = super().session_info()
        if self.env.su or not self.env.user or not self.env.user._is_internal():
            return info

        policy = self.env['aam.policy'].get_policy()
        if policy['globals'].get('disable_developer_mode'):
            info['is_system'] = False
            info['debug'] = ''

        info['aam_policy'] = self.env['aam.policy'].get_client_policy()
        return info
