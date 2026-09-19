# -*- coding: utf-8 -*-
{
    'name': 'Temas de Login',
    'version': '17.0.1.0.0',
    'summary': 'Personaliza la pantalla de acceso con 3 diseños modernos, tus colores, tu logo e imagen de fondo, con vista previa en vivo',
    'description': """
Temas de Login
==============

Cambia la pantalla de acceso de Odoo por un diseño propio, sin tocar una línea
de código y sin instalar un tema completo.

- Tres diseños listos: Aurora (tarjeta centrada sobre fondo animado), Dividido
  (panel de marca a un lado y formulario al otro) y Reflector (imagen a pantalla
  completa con tarjeta de vidrio esmerilado).
- Color principal, degradado de fondo, redondeo y tarjeta clara, oscura o de
  vidrio: la pantalla queda con los colores de tu empresa.
- Logo propio o el de la compañía, título y subtítulo de bienvenida, y texto de
  pie personalizado.
- Imagen de fondo con control de intensidad de la capa superpuesta.
- Muestra u oculta el enlace de contraseña olvidada, el de crear cuenta, el
  gestor de bases de datos y el selector de base de datos.
- Vista previa en vivo dentro de Ajustes: ves el resultado mientras eliges, sin
  guardar ni abrir otra pestaña.
- Diseños responsivos: se ven bien en computadora, tableta y teléfono.
- El mismo diseño se aplica a restablecer contraseña y crear cuenta.
- Se desactiva con un clic y la pantalla vuelve a la de Odoo, sin rastro.
""",
    'category': 'Technical',
    'author': 'Codfy',
    'website': 'https://www.codfy.mx',
    'license': 'LGPL-3',
    'depends': ['base_setup', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/login_theme_data.xml',
        'views/login_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'c_login_theme/static/src/scss/login_theme.scss',
        ],
        'web.assets_backend': [
            'c_login_theme/static/src/scss/login_theme_preview.scss',
            'c_login_theme/static/src/js/login_preview.js',
            'c_login_theme/static/src/js/login_preview.xml',
        ],
    },
    'images': ['static/description/assets/images/main_screenshot.gif'],
    'installable': True,
    'application': False,
}
