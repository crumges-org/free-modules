from odoo import fields, models, api, _
from odoo.addons.web.controllers.utils import is_user_internal
from odoo.http import request
from markupsafe import Markup

class ResUsers(models.Model):
    _inherit = 'res.users'

    fleet_lang = fields.Selection(
        selection=[('en_US', 'English (US)'),('es_ES', 'Spanish (Spain)')],string='Fleet Mobile App Language',default='en_US')

    # Not Called in This APP
    # def get_driverbot_id(self):
    #     driverbot = self.env.ref('base.user_root').id
    #     return driverbot

    # NOTE: related record rule function:
    def get_allowed_shipment_ids(self):
        shipment_ids = []
        user = self.env.user
        if request and request.session.uid and not is_user_internal(request.session.uid):
            user_id = request.env['res.users'].browse(request.session.uid)
            # if hasattr(user_id, 'access_user_id') and user_id.access_user_id:
            #     user = user_id

        # domain = [('call_out_id', '!=', False)]
        domain = []
        allowed_company_ids = self.env.context.get('allowed_company_ids') if self.env.context and 'allowed_company_ids' in self.env.context else user.company_ids.ids


        # if user.user_type == 'driver_user':
        #     if len(allowed_company_ids) > 0:
        #         domain += ['|', '|', ('call_out_id.create_uid', '=', user.id), ('call_out_id.message_partner_ids', 'in', [user.partner_id.id]), ('call_out_id.company_id', 'in', allowed_company_ids)]
        #     else:
        #         domain += [('customer_id', 'in', user.company_ids.ids)]
        # elif user.user_type == 'customer_user':
        #     domain += ['|', ('call_out_id.create_uid', '=', user.id),  ('call_out_id.message_partner_ids', 'in', [user.partner_id.id])]



        # NOTE: [T2785] For offline availability of shipment documents all the domain is discarded for driver user, in order to
        #       access all the shipment assigned to driver user irrespective of  or company
        # if user.standard_template_integration_user_type == 'driver_user':
        if user.has_group('bista_driver_app.group_shipment_driver_user_access') and not user.has_group('bista_driver_app.group_shipment_dispatcher_access'):
            domain = [('driver_id.user_id.id','=',user.id)]

        shipment_ids = self.env['shipment.shipment'].sudo().search(domain).ids
        return shipment_ids

    @api.model
    def write(self, vals):

        # NOTE FIX: user obj has no function named message_post
        # for user in self:
        #     # Check if password is changed, then Create a Log message.
        #     if 'password' in vals:
        #         user.message_post(body=Markup(f"<p>Password Changed.</p>") )

        res = super(ResUsers, self).write(vals)
        # NOTE: Driver app
        shipment_status_user_group = self.env.ref('bista_driver_app.group_shipment_driver_user_access')
        for rec in self:
            if rec.is_driver and shipment_status_user_group not in rec.groups_id:
                rec.groups_id = [(4, shipment_status_user_group.id)]

        return res


### Comment For Removing the dependency on bista_driver_report module ###
    # @api.model
    # def get_view(self, view_id=None, view_type='form', **options):
    #     """
    #     Overrides orm field_view_get.
    #     @return: Dictionary of Fields, arch and toolbar.
    #     """
    #     if view_type == 'tree':
    #         if not self.env.user.has_group('base.group_system') and not self.env.user.has_group('bista_driver_app.group_call_out_readonly_user_access'):
    #             view_id = self.env.ref('bista_driver_report.view_users_tree_view').id
    #
    #     return super().get_view(view_id, view_type, **options)
