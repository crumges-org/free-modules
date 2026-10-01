from odoo import fields, models


class AamRuleMenu(models.Model):
    """Menus and sub-menus to hide (features A1, A2)."""

    _name = 'aam.rule.menu'
    _inherit = ['aam.rule.line.mixin']
    _description = 'Menu Restriction'

    menu_id = fields.Many2one(
        'ir.ui.menu', 'Menu', required=True, ondelete='cascade', index=True)
    include_children = fields.Boolean(
        'Hide Sub-Menus', default=True,
        help="Also hide everything nested under this menu. Leave off to hide only "
             "this entry while keeping its children reachable from elsewhere.",
    )

    _sql_constraints = [
        ('menu_uniq',
         'UNIQUE (rule_id, menu_id)',
         'This menu is already restricted by this rule.'),
    ]

    def _menu_ids_to_hide(self):
        """Expand each line into the full set of menu ids it hides.

        ``ir.ui.menu.full_list`` is not optional here. Odoo 18 overrides
        ``search_fetch`` to run every result through ``_filter_visible_menus()``
        unless that context key is set (``base/models/ir_ui_menu.py:142-152``),
        and the visibility it filters by comes from ``self.env.user`` - so
        ``sudo()`` does **not** lift it: ``sudo()`` sets superuser *mode* but
        leaves ``env.user`` alone. The policy is compiled as the restricted user,
        so without this the subtree silently comes back short and
        ``include_children`` under-hides. Odoo 19 does not override search at all,
        where the key is simply ignored - so this is correct on both.
        """
        ids = set()
        menus = self.env['ir.ui.menu'].sudo().with_context(**{
            'ir.ui.menu.full_list': True})
        for line in self:
            ids.add(line.menu_id.id)
            if line.include_children:
                ids.update(menus.search([('id', 'child_of', line.menu_id.id)]).ids)
        return ids
