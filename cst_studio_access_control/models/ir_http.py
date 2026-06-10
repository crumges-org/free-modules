# -*- coding: utf-8 -*-

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        result['studio_control_access'] = self.env.user.has_group('cst_studio_access_control.studio_control_group_access')
        return result
