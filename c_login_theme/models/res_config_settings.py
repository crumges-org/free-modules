# -*- coding: utf-8 -*-
# Part of the Codfy module suite for Odoo. See LICENSE file for full terms.
# Copyright (C) 2026 Codfy (https://www.codfy.mx)
# License: LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    login_theme_id = fields.Many2one(
        'c.login.theme',
        string="Tema de acceso",
        default=lambda self: self.env['c.login.theme']._get_theme(),
    )
    login_theme_enabled = fields.Boolean(related='login_theme_id.enabled', readonly=False)
    login_theme_layout = fields.Selection(related='login_theme_id.layout', readonly=False)
    login_theme_card_mode = fields.Selection(related='login_theme_id.card_mode', readonly=False)
    login_theme_primary_color = fields.Char(related='login_theme_id.primary_color', readonly=False)
    login_theme_bg_start = fields.Char(related='login_theme_id.bg_start', readonly=False)
    login_theme_bg_end = fields.Char(related='login_theme_id.bg_end', readonly=False)
    login_theme_radius = fields.Integer(related='login_theme_id.radius', readonly=False)
    login_theme_use_own_logo = fields.Boolean(related='login_theme_id.use_own_logo', readonly=False)
    login_theme_logo = fields.Binary(related='login_theme_id.logo', readonly=False)
    login_theme_logo_height = fields.Integer(related='login_theme_id.logo_height', readonly=False)
    login_theme_headline = fields.Char(related='login_theme_id.headline', readonly=False)
    login_theme_tagline = fields.Char(related='login_theme_id.tagline', readonly=False)
    login_theme_footer_note = fields.Char(related='login_theme_id.footer_note', readonly=False)
    login_theme_background_image = fields.Binary(related='login_theme_id.background_image', readonly=False)
    login_theme_overlay = fields.Integer(related='login_theme_id.overlay', readonly=False)
    login_theme_show_reset_password = fields.Boolean(related='login_theme_id.show_reset_password', readonly=False)
    login_theme_show_signup = fields.Boolean(related='login_theme_id.show_signup', readonly=False)
    login_theme_show_db_selector = fields.Boolean(related='login_theme_id.show_db_selector', readonly=False)
    login_theme_show_db_manager = fields.Boolean(related='login_theme_id.show_db_manager', readonly=False)

    @api.onchange('login_theme_layout')
    def _onchange_login_theme_layout(self):
        """Cada diseño luce mejor con un estilo de formulario distinto."""
        self.login_theme_card_mode = 'glass' if self.login_theme_layout == 'spotlight' else 'light'
