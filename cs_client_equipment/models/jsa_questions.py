# -*- coding: utf-8 -*-

#################################################################################
# Author      : Cyder Solutions (<www.cyder.com.au>)
# Copyright(c): 2021-now
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can't redistribute/reshare/recreate it for any purpose.
#################################################################################

from odoo import api, fields, models

class JsaQuestions(models.Model):
    _name = "jsa.questions"
    _description = "Jsa Questions"

    name = fields.Char('Reference')
    stage = fields.Selection([('pre', 'Pre-Works'), ('post', 'Post-Works')], string="Stage", default='post')
    active = fields.Boolean(default=True)
    question = fields.Char('Question')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('jsa.questions')
        return super().create(vals_list)
