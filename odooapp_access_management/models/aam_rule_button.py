from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .aam_constants import ELEMENT_TYPES


class AamRuleButton(models.Model):
    """Buttons, notebook tabs, kanban links and navbar items to hide.

    Covers features E1-E6 and B18. Elements are matched by the attribute the
    view actually carries: a button by its ``name``, a page by its ``name`` or
    visible ``string``, a kanban link by its ``type``. We match on ``name``
    first because it survives translation - matching only on the label would
    silently stop working the moment someone switches language.
    """

    _name = 'aam.rule.button'
    _inherit = ['aam.rule.model.line.mixin']
    _description = 'Button and Tab Restriction'

    element_type = fields.Selection(
        ELEMENT_TYPES, required=True, default='button', string='Element')
    element_name = fields.Char(
        'Technical Name', required=True,
        help="The button's method name (e.g. action_confirm), the page's name "
             "attribute, or the kanban link type. Enable developer mode and hover "
             "the element to find it.")
    element_label = fields.Char(
        'Label',
        help="Only for reference in this list - matching is done on the technical name.")

    view_mode = fields.Selection(
        [('all', 'All Views'), ('form', 'Form'), ('list', 'List'),
         ('kanban', 'Kanban')],
        default='all', required=True, string='In View',
        help="Restrict the hiding to one view type.")

    condition = fields.Char(
        'Condition',
        help="Python expression over the record, e.g. state == 'done'. When set, "
             "the element is hidden only when it evaluates true.")

    _sql_constraints = [
        ('element_uniq',
         'UNIQUE (rule_id, model_id, element_type, element_name, view_mode)',
         'This element is already restricted by this rule.'),
    ]

    @api.constrains('condition')
    def _check_condition(self):
        for line in self.filtered('condition'):
            try:
                compile(line.condition, '<condition>', 'eval')
            except SyntaxError as exc:
                raise ValidationError(_(
                    "The condition on %(name)s is not a valid Python expression: "
                    "%(error)s", name=line.element_name, error=exc)) from exc

    @api.constrains('element_type', 'model_id')
    def _check_navbar_scope(self):
        for line in self:
            if line.element_type == 'navbar' and not line.model_id:
                raise ValidationError(
                    _("Navbar items are not tied to a model; pick any model as a placeholder "
                      "or use the global 'Hide Action (cog) Menu' toggle instead."))
