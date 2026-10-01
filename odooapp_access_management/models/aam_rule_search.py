from odoo import fields, models


class AamRuleSearch(models.Model):
    """Search-panel restrictions for one model (features F1-F7).

    Named filters and group-bys live in the search view arch, not as records,
    so they are matched by their ``name`` attribute. Comma-separated because a
    rule almost always hides several at once and a one2many of single names
    would be tedious to fill in.
    """

    _name = 'aam.rule.search'
    _inherit = ['aam.rule.model.line.mixin']
    _description = 'Search Panel Restriction'

    filter_names = fields.Char(
        'Hidden Filters',
        help="Comma-separated filter names from the search view, e.g. my_orders,late.")
    groupby_names = fields.Char(
        'Hidden Group By',
        help="Comma-separated group-by names from the search view.")

    hide_all_filters = fields.Boolean('Hide All Filters')
    hide_all_groupby = fields.Boolean('Hide All Group By')
    hide_custom_filter = fields.Boolean('Hide Custom Filter')
    hide_custom_groupby = fields.Boolean('Hide Custom Group By')
    hide_delete_filter = fields.Boolean('Hide Delete Saved Filter')
    hide_favourite = fields.Boolean('Hide Favourites')
    hide_search_panel = fields.Boolean('Hide Search Panel')

    _sql_constraints = [
        ('search_uniq',
         'UNIQUE (rule_id, model_id)',
         'This model already has a search restriction in this rule.'),
    ]

    @staticmethod
    def _split_names(value):
        return [n.strip() for n in (value or '').split(',') if n.strip()]

    def _hidden_filter_names(self):
        self.ensure_one()
        return self._split_names(self.filter_names)

    def _hidden_groupby_names(self):
        self.ensure_one()
        return self._split_names(self.groupby_names)
