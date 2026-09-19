# -*- coding: utf-8 -*-
# Part of the Codfy module suite for Odoo. See LICENSE file for full terms.
# Copyright (C) 2026 Codfy (https://www.codfy.mx)
# License: LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import re

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

HEX_COLOR = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

ASSET_ROUTE = '/c_login_theme/asset/'

LAYOUTS = [
    ('aurora', "Aurora"),
    ('split', "Dividido"),
    ('spotlight', "Reflector"),
]

CARD_MODES = [
    ('light', "Clara"),
    ('dark', "Oscura"),
    ('glass', "Vidrio esmerilado"),
]


def _normalize(color, fallback):
    """Devuelve el color en formato #RRGGBB, o el de respaldo si no es válido."""
    if not color or not HEX_COLOR.match(color.strip()):
        return fallback
    color = color.strip()
    if len(color) == 4:
        return '#' + ''.join(c * 2 for c in color[1:])
    return color.upper()


def _to_rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def _to_hex(rgb):
    return '#%02X%02X%02X' % tuple(max(0, min(255, round(c))) for c in rgb)


def _mix(color, other, ratio):
    """Mezcla dos colores; ratio 0 devuelve el primero y 1 el segundo."""
    return _to_hex([a + (b - a) * ratio for a, b in zip(_to_rgb(color), _to_rgb(other))])


def _luminance(color):
    channels = []
    for value in _to_rgb(color):
        value = value / 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


class LoginTheme(models.Model):
    _name = 'c.login.theme'
    _description = "Tema de la pantalla de acceso"

    name = fields.Char(default="Tema de acceso", required=True)
    enabled = fields.Boolean(
        string="Aplicar el tema",
        default=False,
        help="Mientras esté desactivado, la pantalla de acceso es la original de Odoo.",
    )
    layout = fields.Selection(LAYOUTS, string="Diseño", default='aurora', required=True)
    card_mode = fields.Selection(CARD_MODES, string="Estilo del formulario", default='light', required=True)

    primary_color = fields.Char(string="Color principal", default='#0B6EFF', required=True)
    bg_start = fields.Char(string="Fondo (inicio)", default='#132B6B', required=True)
    bg_end = fields.Char(string="Fondo (fin)", default='#080B16', required=True)
    radius = fields.Integer(string="Redondeo", default=20)

    use_own_logo = fields.Boolean(string="Usar un logo propio")
    logo = fields.Binary(string="Logo")
    logo_height = fields.Integer(string="Alto del logo (px)", default=48)

    headline = fields.Char(string="Título", default="Bienvenido")
    tagline = fields.Char(string="Subtítulo", default="Inicia sesión para continuar")
    footer_note = fields.Char(string="Texto de pie")

    background_image = fields.Binary(string="Imagen de fondo")
    overlay = fields.Integer(
        string="Intensidad de la capa",
        default=60,
        help="Qué tanto se oscurece la imagen de fondo para que el texto se lea bien.",
    )

    show_reset_password = fields.Boolean(string="Contraseña olvidada", default=True)
    show_signup = fields.Boolean(string="Crear cuenta", default=True)
    show_db_selector = fields.Boolean(string="Selector de base de datos", default=True)
    show_db_manager = fields.Boolean(string="Gestor de bases de datos", default=True)

    @api.constrains('primary_color', 'bg_start', 'bg_end')
    def _check_colors(self):
        for theme in self:
            for value in (theme.primary_color, theme.bg_start, theme.bg_end):
                if value and not HEX_COLOR.match(value.strip()):
                    raise ValidationError(_(
                        "«%s» no es un color válido. Elige el color con el selector o "
                        "escríbelo en formato #RRGGBB, por ejemplo #0B6EFF.", value))

    @api.constrains('overlay', 'radius', 'logo_height')
    def _check_ranges(self):
        for theme in self:
            if not 0 <= theme.overlay <= 100:
                raise ValidationError(_("La intensidad de la capa va de 0 a 100."))
            if not 0 <= theme.radius <= 40:
                raise ValidationError(_("El redondeo va de 0 a 40 píxeles."))
            if not 16 <= theme.logo_height <= 160:
                raise ValidationError(_("El alto del logo va de 16 a 160 píxeles."))

    @api.model
    def _get_theme(self):
        theme = self.sudo().search([], limit=1)
        if not theme:
            theme = self.sudo().create({})
        return theme

    def _asset_url(self, field):
        self.ensure_one()
        stamp = int(self.write_date.timestamp()) if self.write_date else 0
        return '%s%s?v=%s' % (ASSET_ROUTE, field, stamp)

    def _render_context(self, overrides=None):
        """Contexto que consumen las plantillas del acceso.

        Devuelve False cuando el tema está desactivado, para que la pantalla
        original de Odoo quede intacta.
        """
        theme = self.sudo().search([], limit=1)
        if not theme:
            return False
        values = theme._theme_values()
        if overrides:
            values.update(overrides)
        if not values.get('enabled'):
            return False
        if values['layout'] not in dict(LAYOUTS):
            values['layout'] = 'aurora'
        if values['card_mode'] not in dict(CARD_MODES):
            values['card_mode'] = 'light'
        values['use_own_logo'] = bool(values.get('use_own_logo') and values.get('logo_url'))
        values['css'] = theme._build_css(values)
        return values

    def _theme_values(self):
        self.ensure_one()
        return {
            'enabled': self.enabled,
            'layout': self.layout if self.layout in dict(LAYOUTS) else 'aurora',
            'card_mode': self.card_mode if self.card_mode in dict(CARD_MODES) else 'light',
            'primary_color': self.primary_color,
            'bg_start': self.bg_start,
            'bg_end': self.bg_end,
            'radius': self.radius,
            'use_own_logo': self.use_own_logo and bool(self.logo),
            'logo_url': self._asset_url('logo') if self.logo else '',
            'logo_height': self.logo_height,
            'headline': self.headline or '',
            'tagline': self.tagline or '',
            'footer_note': self.footer_note or '',
            'image_url': self._asset_url('background_image') if self.background_image else '',
            'overlay': self.overlay,
            'show_reset_password': self.show_reset_password,
            'show_signup': self.show_signup,
            'show_db_selector': self.show_db_selector,
            'show_db_manager': self.show_db_manager,
        }

    def _build_css(self, values):
        """Variables CSS del tema, con todos los valores saneados."""
        primary = _normalize(values.get('primary_color'), '#0B6EFF')
        start = _normalize(values.get('bg_start'), '#132B6B')
        end = _normalize(values.get('bg_end'), '#080B16')
        radius = max(0, min(40, int(values.get('radius') or 0)))
        overlay = max(0, min(100, int(values.get('overlay') or 0)))
        logo_height = max(16, min(160, int(values.get('logo_height') or 48)))
        image_url = values.get('image_url') or ''
        dark_card = values.get('card_mode') in ('dark', 'glass')
        if dark_card:
            link = _mix(primary, '#FFFFFF', 0.5)
        else:
            link = primary if _luminance(primary) < 0.5 else _mix(primary, '#000000', 0.35)

        declarations = {
            '--c-login-primary': primary,
            '--c-login-primary-rgb': ','.join(str(c) for c in _to_rgb(primary)),
            '--c-login-primary-strong': _mix(primary, '#000000', 0.18),
            '--c-login-primary-soft': _mix(primary, '#FFFFFF', 0.86),
            '--c-login-on-primary': '#FFFFFF' if _luminance(primary) < 0.45 else '#0B1120',
            '--c-login-link': link,
            '--c-login-bg-start': start,
            '--c-login-bg-end': end,
            '--c-login-bg-start-rgb': ','.join(str(c) for c in _to_rgb(start)),
            '--c-login-bg-end-rgb': ','.join(str(c) for c in _to_rgb(end)),
            '--c-login-glow': _mix(primary, start, 0.45),
            '--c-login-radius': '%dpx' % radius,
            '--c-login-radius-inner': '%dpx' % max(6, radius - 8),
            '--c-login-logo-height': '%dpx' % logo_height,
            '--c-login-overlay': '%.2f' % (overlay / 100.0),
        }
        if image_url.startswith(ASSET_ROUTE):
            declarations['--c-login-image'] = 'url("%s")' % image_url
        body = ''.join('%s:%s;' % (key, value) for key, value in declarations.items())
        return Markup(':root{%s}') % Markup(body)
