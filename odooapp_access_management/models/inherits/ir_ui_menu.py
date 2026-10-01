from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _load_menus_blacklist(self):
        """Add the menus this user's policy hides (features A1, A2).

        This is the correct hook rather than ``_visible_menu_ids``: that one is
        ``@ormcache('frozenset(self.env.user._get_group_ids())', 'debug')``, so
        it is keyed on the *group set* and two users with identical groups would
        share an entry - per-user menu hiding would leak between them.
        ``_load_menus_blacklist`` is called from inside ``load_menus``, which is
        keyed on ``self.env.uid``.
        """
        blacklist = super()._load_menus_blacklist()
        hidden = self.env['aam.policy'].get_policy()['menus']
        if hidden:
            blacklist = list(blacklist) + list(hidden)
        return blacklist
