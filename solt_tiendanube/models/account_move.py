# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api


_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'solt.integration.model.mixin']

    payment_method_id = fields.Many2one(
        string="Payment method", comodel_name='payment.method'
    )