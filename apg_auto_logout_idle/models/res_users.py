# -*- coding: utf-8 -*-

from odoo import fields, models


class Users(models.Model):
    _inherit = "res.users"

    enable_idle = fields.Boolean(string="Enable Idle Time",
                                 help="Enable Idle Timer")
    idle_time = fields.Integer(string="Idle Time (In minutes)", default=10,
                               help="Set Idle Time For theis User")
    # SQL constraints
    _sql_constraints = [
        ('positive_idle_time', 'CHECK(idle_time >= 1)',
         'Idle Time should be a positive number.'),
    ]
