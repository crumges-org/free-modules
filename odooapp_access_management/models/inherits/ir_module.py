from odoo import _, api, models
from odoo.exceptions import AccessError


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def _aam_check_module_manage(self):
        """Block app install, upgrade and uninstall (feature B15)."""
        if self.env.su:
            return
        if self.env['aam.policy'].get_policy()['globals'].get('restrict_module_manage'):
            raise AccessError(_(
                "You are not allowed to install, upgrade or uninstall applications."))

    def button_immediate_install(self):
        self._aam_check_module_manage()
        return super().button_immediate_install()

    def button_immediate_upgrade(self):
        self._aam_check_module_manage()
        return super().button_immediate_upgrade()

    def button_immediate_uninstall(self):
        self._aam_check_module_manage()
        return super().button_immediate_uninstall()

    def button_install(self):
        self._aam_check_module_manage()
        return super().button_install()

    def button_upgrade(self):
        self._aam_check_module_manage()
        return super().button_upgrade()

    def button_uninstall(self):
        self._aam_check_module_manage()
        return super().button_uninstall()
