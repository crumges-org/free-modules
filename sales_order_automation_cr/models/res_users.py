# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by CandidRoot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = "res.users"

    so_auto_complete = fields.Boolean('Sales Order Auto Complete', default=False, copy=False)