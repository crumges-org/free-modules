# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    firebase_name = fields.Char("Firebase Project Name")
    firebase_id = fields.Char("Firebase Project ID")
    firebase_key_file = fields.Binary("Firebase Admin Key File")

    @api.model
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        set_param = self.env["ir.config_parameter"].set_param
        set_param("bista_mobile_base.firebase_project_name", self.firebase_name)
        set_param("bista_mobile_base.firebase_project_id", self.firebase_id)
        set_param("bista_mobile_base.firebase_admin_key_file", self.firebase_key_file)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        firebase_project_name = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("bista_mobile_base.firebase_project_name")
        )
        firebase_project_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("bista_mobile_base.firebase_project_id")
        )
        firebase_admin_key_file = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("bista_mobile_base.firebase_admin_key_file")
        )
        res.update(
            firebase_name=firebase_project_name,
            firebase_id=firebase_project_id,
            firebase_key_file=firebase_admin_key_file,
        )
        return res
