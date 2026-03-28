# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_pre_receipt = fields.Boolean(string='Print Pre Receipt')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_enable_pre_receipt = fields.Boolean(related='pos_config_id.enable_pre_receipt', readonly=False)