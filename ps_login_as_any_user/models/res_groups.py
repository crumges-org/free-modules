# -*- coding: utf-8 -*-


from odoo import fields, models, api
from odoo.http import request, root, Session


class ResGroups(models.Model):
    """class to inherit a new field to res groups"""
    _inherit = 'res.groups'

    user_id = fields.Many2one('user.selection', string="User",
                              help="Select User")


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def check_previous_admin_access(self):
        """
        Returns True if the session was switched from an admin (base.group_system).
        Used by JS systray widget to decide whether to show 'Back to Admin' button.
        """

        session = request.session
        prev_user_id = session.get('previous_user')
        current_user = self.env.user
        if not prev_user_id:
            return False

        prev_user = self.sudo().browse(prev_user_id)

        is_prev_admin = prev_user.has_group('base.group_system')
        is_different_user = prev_user.id != current_user.id

        return bool(is_prev_admin and is_different_user)

