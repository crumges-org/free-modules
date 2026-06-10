from odoo import api, fields, models,_
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"
    
    fleet_token_ids = fields.One2many("fleet.api.access_token", "user_id", string="Access Tokens")
    # standard_template_integration_user_type = fields.Selection(
    #     [('standard_user', 'Standard User'), ('template_user', 'Template User'),
    #      ('integration_user', 'Integration User'), ('driver_user', 'Driver User')], tracking=True,
    #     string="System User Type", help="The System User Type helps assign the user their system status.\n\n"
    #                                      "Standard User: Regular active licensed user.\n"
    #                                      "Template User: Used to give module permissions to the Portal User. If the user is a Template User, then the account will not be able to sign in to Driver App and will not be archived through the archive user scheduled action.\n"
    #                                      "Integration User: Used to integrate Driver App data with another system. If the user is a Integration User, then the account will not be able to sign in to Driver App and will not be archived through the archive user scheduled action.\n"
    #                                      "Driver User: Used for login and driver management for Shipment.")
    # user_type = fields.Selection([("driver_user", "Driver User"), ("customer_user", "Customer User")],
    #                              string="Driver User Type", tracking=True,
    #                              help="Helps system differentiate between internal Driver App User or external Customer User.")

    def write(self, values):
        """Method inherit for trigger groups changes"""
        res = super().write(values)
        for rec in self:
            # if rec.standard_template_integration_user_type == 'driver_user':
            if rec.has_group('bista_driver_app.group_shipment_driver_user_access') and not rec.has_group('bista_driver_app.group_shipment_dispatcher_access'):
                rec.partner_id.write({'company_ids': [(5, 0, 0)], 'company_id': False})
            else:
                updated_dict = {
                    'company_ids': [(6, 0, rec.company_ids.ids if rec.company_ids else [])],
                    'is_driver': False,
                }
                if rec.company_id.id != rec.partner_id.company_id.id:
                    updated_dict.update({'company_id': rec.company_id.id})
                rec.partner_id.sudo().write(updated_dict)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Used user type value"""
        res = super(ResUsers, self).create(vals_list)
        for rec in res:
            # if rec.standard_template_integration_user_type == 'driver_user':
            if rec.has_group('bista_driver_app.group_shipment_driver_user_access') and not rec.has_group('bista_driver_app.group_shipment_dispatcher_access'):
                rec.partner_id.write({
                    'company_ids': [(5, 0, 0)],
                    'company_id': False,
                })
        return res
    # TODO: shifted to bista_password_security module
    def _check_password_policy(self, passwords):
        """
            bypass checking for Driver User as OTP is used for login instead of passwords.
        """
        # if self.has_group('base.group_portal') and self.standard_template_integration_user_type == 'driver_user':
        if self.has_group('bista_driver_app.group_shipment_driver_user_access') and not self.has_group('bista_driver_app.group_shipment_dispatcher_access'):
            return True
        else:
            super(ResUsers, self)._check_password_policy(passwords)

    def _check_password_rules(self, password):
        """
            bypass checking for Driver User as OTP is used for login instead of passwords.
        """
        # if self.has_group('base.group_portal') and self.standard_template_integration_user_type == 'driver_user':
        if self.has_group('bista_driver_app.group_shipment_driver_user_access') and not self.has_group('bista_driver_app.group_shipment_dispatcher_access'):
            return True
        else:
            return super(ResUsers, self)._check_password_rules(password)


    def unlink(self):
        """
            Prevent iOS test driver user unlink.
        """
        for rec in self:
            driver_id = rec.env['fleet.driver'].search([('user_id', '=', rec.id)])
            if driver_id and driver_id.id == self.env.ref('bista_driver_app.ios_test_driver_rec').id:
                raise UserError(_("You cannot delete this iOS test driver."))
        return super().unlink()


    def action_archive(self):
        """
            Prevent iOS test driver user active toggle.
        """
        for rec in self:
            driver_id = rec.env['fleet.driver'].search([('user_id', '=', rec.id)])
            if driver_id and driver_id.id == self.env.ref('bista_driver_app.ios_test_driver_rec').id:
                raise UserError(_("You cannot archive iOS test driver user."))
        return super().action_archive()