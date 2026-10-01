from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

from .aam_constants import MASK_TYPES, VIEW_SCOPES


class AamRuleField(models.Model):
    """Per-field restrictions, including server-side value masking.

    Covers features C1-C15. Note the difference between ``invisible`` and
    ``mask_type``: invisible removes the field from the view and, when the rule
    is enforced, from the record payload entirely. Masking keeps the field
    present but replaces the value, which is what you want for a phone number a
    support agent must know exists but should not read in full.
    """

    _name = 'aam.rule.field'
    _inherit = ['aam.rule.model.line.mixin']
    _description = 'Field Restriction'

    field_id = fields.Many2one(
        'ir.model.fields', 'Field', required=True, ondelete='cascade', index=True,
        domain="[('model_id', '=', model_id)]")
    field_name = fields.Char(related='field_id.name', store=True, index=True)
    field_ttype = fields.Selection(related='field_id.ttype', string='Field Type')

    # -- Visibility and editability (C1-C3) --------------------------------
    invisible = fields.Boolean(
        'Invisible',
        help="Removes the field from form, list, kanban, search, group-by, pivot "
             "and export. When the rule is enforced it is also stripped from the "
             "server response, so it cannot be read over RPC.")
    readonly = fields.Boolean('Read-Only')
    required = fields.Boolean('Required')
    view_mode = fields.Selection(
        VIEW_SCOPES, default='all', required=True, string='In View',
        help="Hide the field in one view type only - for example Search, to drop "
             "a section from the left-hand search panel while the field stays on "
             "the form. A scoped line only hides: the field still exists for the "
             "user, so it is not stripped from the server response.")

    # -- Relational widget options (C4-C7, C15) ----------------------------
    no_open = fields.Boolean(
        'Remove Internal Link',
        help="Hides the arrow that opens the linked record.")
    no_create = fields.Boolean(
        'Remove "Create"',
        help="Users may only pick from existing records.")
    no_quick_create = fields.Boolean('Remove Quick Create')
    no_create_edit = fields.Boolean('Remove "Create and edit..."')

    # -- Conditional access (C8, C9) ---------------------------------------
    condition = fields.Char(
        'Condition',
        help="Python expression over the record, e.g. state != 'draft'. When set, "
             "the restrictions above apply only when it evaluates true. Leave "
             "empty to always apply.")
    field_domain = fields.Char(
        'Limit Choices To',
        help="Extra domain merged into this relational field's dropdown, e.g. "
             "[('country_id.code', '=', 'IN')].")

    # -- Export (C11) ------------------------------------------------------
    no_export = fields.Boolean(
        'Block Export',
        help="Keep the field visible but exclude it from exports.")

    # -- Masking (C14) -----------------------------------------------------
    mask_type = fields.Selection(
        MASK_TYPES, default='none', required=True, string='Masking')
    mask_char = fields.Char('Mask Character', default='*', size=1)
    mask_keep = fields.Integer(
        'Visible Characters', default=4,
        help="How many trailing characters stay readable for partial and phone masking.")
    mask_pattern = fields.Char(
        'Custom Pattern',
        help="Literal text shown instead of the value, e.g. [redacted].")

    _sql_constraints = [
        ('field_uniq',
         'UNIQUE (rule_id, field_id)',
         'This field is already restricted by this rule. Edit the existing line instead.'),
    ]

    @api.constrains('invisible', 'required')
    def _check_not_invisible_and_required(self):
        for line in self:
            if line.invisible and line.required:
                raise ValidationError(_(
                    "Field %s cannot be both invisible and required - the user would "
                    "be unable to save the record and could not see why.",
                    line.field_name))

    @api.constrains('view_mode', 'invisible', 'readonly', 'required', 'no_open',
                    'no_create', 'no_quick_create', 'no_create_edit', 'no_export',
                    'mask_type', 'condition', 'field_domain')
    def _check_view_scope(self):
        """A view scope can only hide.

        Read-only, masking, export blocking and the rest are enforced by the ORM,
        which has no view to scope by - so on a scoped line they would quietly
        apply everywhere while the line claimed otherwise.
        """
        for line in self.filtered(lambda l: l.view_mode and l.view_mode != 'all'):
            others = [
                label for flag, label in (
                    ('readonly', _('Read-Only')), ('required', _('Required')),
                    ('no_open', _('Remove Internal Link')),
                    ('no_create', _('Remove "Create"')),
                    ('no_quick_create', _('Remove Quick Create')),
                    ('no_create_edit', _('Remove "Create and edit..."')),
                    ('no_export', _('Block Export')),
                    ('condition', _('Condition')),
                    ('field_domain', _('Limit Choices To')),
                ) if line[flag]
            ]
            if line.mask_type and line.mask_type != 'none':
                others.append(_('Masking'))
            if not line.invisible or others:
                raise ValidationError(_(
                    "%(field)s is limited to one view, which only works for hiding it. "
                    "Tick Invisible, and put %(others)s on a line for All Views.",
                    field=line.field_name,
                    others=', '.join(others) or _('any other restriction')))

    @api.constrains('mask_type', 'field_ttype')
    def _check_maskable(self):
        maskable = ('char', 'text', 'html', 'selection', 'integer', 'float', 'monetary')
        for line in self.filtered(lambda l: l.mask_type and l.mask_type != 'none'):
            if line.field_ttype and line.field_ttype not in maskable:
                raise ValidationError(_(
                    "%(field)s is a %(ttype)s field and cannot be masked. Mask text or "
                    "numeric fields, or make this one invisible instead.",
                    field=line.field_name, ttype=line.field_ttype))

    @api.constrains('condition')
    def _check_condition(self):
        for line in self.filtered('condition'):
            try:
                compile(line.condition, '<condition>', 'eval')
            except SyntaxError as exc:
                raise ValidationError(_(
                    "The condition on %(field)s is not a valid Python expression: "
                    "%(error)s", field=line.field_name, error=exc)) from exc

    @api.constrains('field_domain')
    def _check_field_domain(self):
        for line in self.filtered('field_domain'):
            try:
                parsed = safe_eval(line.field_domain, {'user': self.env.user})
            except Exception as exc:
                raise ValidationError(_(
                    "'Limit Choices To' on %(field)s is not valid: %(error)s",
                    field=line.field_name, error=exc)) from exc
            if not isinstance(parsed, (list, tuple)):
                raise ValidationError(_(
                    "'Limit Choices To' on %s must be a domain list.", line.field_name))

    @api.onchange('model_id')
    def _onchange_model_id(self):
        """Clear a field that no longer belongs to the selected model."""
        for line in self:
            if line.field_id and line.field_id.model_id != line.model_id:
                line.field_id = False
