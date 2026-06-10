# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class ShipmetFleetMap(models.TransientModel):
    _name = 'fleet.map'
    _description = 'Fleet Map'

    name = fields.Char(string="Name")