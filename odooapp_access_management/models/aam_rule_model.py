from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class AamRuleModel(models.Model):
    """Per-model restrictions: CRUD, toolbar buttons, views, and record domains.

    Covers features B1-B14 (what you can do to a model) and D1-D6 (which
    records you can do it to). The two live together because they answer the
    same question for the same model, and splitting them would mean configuring
    ``sale.order`` in two places.
    """

    _name = 'aam.rule.model'
    _inherit = ['aam.rule.model.line.mixin']
    _description = 'Model Restriction'

    # -- CRUD (B1, B2) -----------------------------------------------------
    no_create = fields.Boolean('Block Create')
    no_read = fields.Boolean('Block Read')
    no_write = fields.Boolean('Block Edit')
    no_unlink = fields.Boolean('Block Delete')
    readonly_model = fields.Boolean(
        'Read-Only',
        help="Shorthand for blocking create, edit and delete on this model.")

    # -- Toolbar / record buttons (B3-B9, B14) -----------------------------
    hide_archive = fields.Boolean('Hide Archive / Unarchive')
    hide_duplicate = fields.Boolean('Hide Duplicate')
    hide_export = fields.Boolean('Hide Export')
    hide_import = fields.Boolean('Hide Import')
    hide_spreadsheet = fields.Boolean('Hide Insert in Spreadsheet')
    hide_print = fields.Boolean('Hide Print Menu')
    hide_action_button = fields.Boolean('Hide Action (cog) Menu')
    hide_edit_button = fields.Boolean('Hide Edit Button')

    # -- Views, reports and actions (B10-B13, B16-B17) ---------------------
    hide_view_ids = fields.Many2many(
        'ir.ui.view', 'aam_rule_model_view_rel', 'line_id', 'view_id',
        string='Hidden Views', domain="[('model', '=', model_name)]")
    hide_view_modes = fields.Char(
        'Hidden View Types',
        help="Comma-separated view types to remove from the action, e.g. "
             "'kanban,pivot'. Leaves the remaining types reachable.")
    hide_report_ids = fields.Many2many(
        'ir.actions.report', 'aam_rule_model_report_rel', 'line_id', 'report_id',
        string='Hidden Reports', domain="[('model', '=', model_name)]")
    hide_action_ids = fields.Many2many(
        'ir.actions.act_window', 'aam_rule_model_action_rel', 'line_id', 'action_id',
        string='Hidden Actions', domain="[('res_model', '=', model_name)]")
    hide_server_action_ids = fields.Many2many(
        'ir.actions.server', 'aam_rule_model_srv_action_rel', 'line_id', 'action_id',
        string='Hidden Server Actions', domain="[('model_name', '=', model_name)]")

    # -- Record-level domain (D1-D6) ---------------------------------------
    domain = fields.Text(
        'Restriction Domain',
        help="Records matching this domain stay accessible; everything else is "
             "hidden for the operations ticked below. Leave empty for no "
             "record-level restriction.",
    )
    domain_on_read = fields.Boolean('Apply to Read', default=True)
    domain_on_write = fields.Boolean('Apply to Edit', default=True)
    domain_on_unlink = fields.Boolean('Apply to Delete', default=True)
    domain_on_create = fields.Boolean('Apply to Create')

    soft_restrict = fields.Boolean(
        'Soft Restrict',
        help="Apply the domain only when the user browses this model directly. "
             "Related records reached through another model stay readable, so "
             "restricting Contacts does not blank out the customer on every "
             "order. Off by default because it is a weaker guarantee.",
    )
    related_field_id = fields.Many2one(
        'ir.model.fields', 'Restrict Through Field', ondelete='cascade',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['many2one', 'many2many', 'one2many'])]",
        help="Apply the domain to this relational field's records rather than to "
             "the model itself.",
    )
    hierarchy_field_id = fields.Many2one(
        'ir.model.fields', 'Hierarchy Field', ondelete='cascade',
        domain="[('model_id', '=', model_id), ('ttype', '=', 'many2one')]",
        help="Walk this parent field so a user who can see a record also sees "
             "everything beneath it.",
    )

    _sql_constraints = [
        ('model_uniq',
         'UNIQUE (rule_id, model_id)',
         'This model is already restricted by this rule. Edit the existing line instead.'),
    ]

    @api.constrains('domain')
    def _check_domain(self):
        for line in self.filtered('domain'):
            try:
                parsed = safe_eval(line.domain, {'user': self.env.user, 'time': None})
            except Exception as exc:
                raise ValidationError(_(
                    "The restriction domain on %(model)s is not valid Python: %(error)s",
                    model=line.model_name, error=exc)) from exc
            if not isinstance(parsed, (list, tuple)):
                raise ValidationError(_(
                    "The restriction domain on %s must be a list, e.g. "
                    "[('user_id', '=', user.id)].", line.model_name))

    @api.onchange('readonly_model')
    def _onchange_readonly_model(self):
        """Read-only is a shorthand, so reflect it in the individual flags."""
        for line in self:
            if line.readonly_model:
                line.no_create = line.no_write = line.no_unlink = True

    def _blocked_modes(self):
        """Return the CRUD modes this line blocks outright."""
        self.ensure_one()
        modes = set()
        if self.no_read:
            modes.add('read')
        if self.no_create or self.readonly_model:
            modes.add('create')
        if self.no_write or self.readonly_model:
            modes.add('write')
        if self.no_unlink or self.readonly_model:
            modes.add('unlink')
        return modes

    def _domain_modes(self):
        """Return the CRUD modes this line's domain applies to."""
        self.ensure_one()
        if not self.domain:
            return set()
        modes = set()
        for mode, flag in (('read', self.domain_on_read), ('write', self.domain_on_write),
                           ('unlink', self.domain_on_unlink), ('create', self.domain_on_create)):
            if flag:
                modes.add(mode)
        return modes
