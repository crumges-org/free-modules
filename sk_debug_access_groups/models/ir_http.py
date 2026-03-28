from odoo import models
from odoo.http import request


def _get_debug_group(user):
    if not user:
        user_id = request.session.uid
        user = request.env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
    result = (1 if user.has_group('sk_debug_access_groups.group_always_debug') else '' if user.has_group('sk_debug_access_groups.group_never_debug') else "Normal") if user else "Normal"
    return result



class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _handle_debug(cls):
        group = _get_debug_group(request.env.user)
        if group in ['', 1]:
            request.session.debug = str(group)
        else:
            return super(IrHttp, cls)._handle_debug()
