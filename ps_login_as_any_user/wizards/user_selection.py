# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)


class UserSelection(models.Model):
    """
        class for a wizard for users selection
        _onchange_user_id:
            function to get corresponding user group
        action_switch:
            function for switching the user
    """
    _name = 'user.selection'
    _description = 'user selection'

    user_id = fields.Many2one('res.users', string="User", required=True,
                              help="Select the user here",
                              domain=lambda self: [
                                  ('id', '!=', self.env.user.id)])
    access_ids = fields.One2many('res.groups', 'user_id', help="User groups",
                                 string="Group", readonly=True)

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """
            Summary:
                change function to get users access group
        """
        self.access_ids = self.user_id.groups_id


    def action_switch(self):
        """
        Switch the current user to another user, preserving previous admin info.
        """
        self.ensure_one()
        dbname = self.env.cr.dbname
        current_user_id = self.env.user.id

        request.session.authenticate_without_password(dbname, self.user_id.login, self.env)

        new_session = request.session

        new_session['previous_user'] = current_user_id
        new_session['previous_user'] = current_user_id
        new_session['previous_session_id'] = request.session.sid
        new_session.modified = True

        request.update_env(user=request.env.user)

        return {
            'type': 'ir.actions.act_url',
            'url': '/',
            'target': 'self'
        }




