from odoo import api, fields, models

from .aam_constants import PARAM_ALLOW_RESTRICT_ADMIN, PARAM_ENABLED


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    aam_enabled = fields.Boolean(
        'Enable Access Management', default=True,
        config_parameter=PARAM_ENABLED,
        help="Master switch. Turning this off makes every access rule inert without "
             "uninstalling the module or losing any configuration - the fastest way "
             "back into a database that has been over-restricted.")

    aam_allow_restrict_admin = fields.Boolean(
        'Allow Restricting Administrators',
        config_parameter=PARAM_ALLOW_RESTRICT_ADMIN,
        help="By default, Settings administrators are never restricted, so a bad rule "
             "cannot lock you out. Only enable this if you understand that you may "
             "need shell access to recover.")

    aam_log_denials = fields.Boolean(
        'Log Access Denials', config_parameter='aam.log_denials',
        help="Record every blocked action. Useful while tuning rules; leave off in "
             "production, since a misconfigured rule on a busy model can write "
             "thousands of rows an hour.")

    aam_log_activity = fields.Boolean(
        'Log Login Activity', default=True, config_parameter='aam.log_activity')

    aam_log_retention_days = fields.Integer(
        'Keep Logs For (days)', default=90,
        config_parameter='aam.log_retention_days')

    aam_password_expiry_days = fields.Integer(
        'Password Expires After (days)', config_parameter='aam.password_expiry_days',
        help="0 disables password expiry.")

    aam_default_new_user_portal = fields.Boolean(
        'New Users Are Portal Users by Default',
        config_parameter='aam.default_new_user_portal')

    @api.onchange('aam_allow_restrict_admin')
    def _onchange_allow_restrict_admin(self):
        if self.aam_allow_restrict_admin:
            return {
                'warning': {
                    'title': "Administrator protection disabled",
                    'message': (
                        "Access rules will now be able to restrict Settings "
                        "administrators, including yourself.\n\n"
                        "If you lock every administrator out, the only way back in is "
                        "an odoo-bin shell session:\n\n"
                        "  env['ir.config_parameter'].set_param('aam.enabled', '0')\n"
                        "  env.cr.commit()"
                    ),
                }
            }

    def set_values(self):
        res = super().set_values()
        # Any of these can change what a user sees, so the compiled policies go.
        self.env.registry.clear_cache('groups')
        self.env.registry.clear_cache()
        return res
