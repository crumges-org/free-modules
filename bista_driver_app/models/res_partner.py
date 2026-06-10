from odoo import fields, models, api, _
from odoo.http import request
from odoo.addons.web.controllers.utils import is_user_internal


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    is_driver = fields.Boolean(string="Is Driver")
    dispatcher_contact_type = fields.Selection([
                                ("dispatcher", "Dispatcher"),
                                ],
                                string="Contact Type", tracking=True, copy=False)
    company_ids = fields.Many2many("res.company", string="Allowed Companies")

    # @api.model_create_multi
    # def create(self, vals_list):
    #     if request and request.session.uid and not is_user_internal(request.session.uid):
    #         user = request.env['res.users'].browse(request.session.uid)
    #         if hasattr(user, 'access_user_id') and user.access_user_id:
    #             self = self.with_user(request.session.uid).sudo()
    #     return super(ResPartner, self).create(vals_list)

    # def write(self, values):
    #     if request and request.session.uid and not is_user_internal(request.session.uid):
    #         user = request.env['res.users'].browse(request.session.uid)
    #         if hasattr(user, 'access_user_id') and user.access_user_id:
    #             self = self.with_user(request.session.uid).sudo()
    #     return super(ResPartner, self).write(values)
