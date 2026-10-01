"""Guided restriction setup.

The Access Rule form exposes everything this module can do, across nine notebook
pages and six kinds of line. That is the right form for someone who already knows
the schema, and the wrong first experience for everyone else: to say "the Sales
team should not delete quotations" you first have to learn that `aam.rule.model`
exists and that it has a `no_unlink`.

This wizard asks four questions instead - who, what, how, and "is this right?" -
and phrases them as intent rather than as schema. "View only" is a word people
already have; `no_create` + `no_write` + `no_unlink` is not.

It is deliberately a *simplification*, not a second editor. One set of choices is
applied to every model you pick. What comes out is an ordinary `aam.rule`, so
anything the wizard cannot say is a short edit on the rule form afterwards - and
`_unsupported_reasons` makes sure a rule that has grown past the wizard is never
loaded back into it and silently flattened.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..models.aam_constants import ENFORCEMENT_MODES
from ..models.aam_group_compat import group_members


#: The four steps, in order. `_STEP_ORDER` drives Next/Back so adding a step means
#: touching this list only.
STEPS = [
    ('who', 'Who'),
    ('what', 'What'),
    ('restrict', 'Restrict'),
    ('review', 'Review'),
]
_STEP_ORDER = [key for key, _label in STEPS]

#: What "View only" and friends mean in terms of the four CRUD booleans on
#: `aam.rule.model`. `readonly_model` is the model's own shorthand and
#: `_blocked_modes()` honours it without the onchange having to fire, which is why
#: the read-only level sets that rather than three separate booleans.
ACCESS_LEVELS = [
    ('none', 'No change'),
    ('readonly', 'View only'),
    ('no_delete', 'Cannot delete'),
    ('no_create_delete', 'Cannot create or delete'),
    ('custom', 'Custom'),
]

RECORD_SCOPES = [
    ('all', 'All records they can already see'),
    ('own', 'Only their own records'),
    ('company', 'Only their own company'),
    ('custom', 'Custom domain'),
]

FIELD_TREATMENTS = [
    ('hide', 'Hide it'),
    ('readonly', 'Read-only'),
    ('required', 'Make it required'),
    ('mask', 'Show a masked value'),
]

#: `aam.rule.field._check_maskable` refuses anything else. Mirrored here so the
#: wizard can say so while you are typing rather than at save time.
MASKABLE_TYPES = ('char', 'text', 'html', 'selection', 'integer', 'float', 'monetary')

#: Toolbar switches offered on step 3. Every one is a real boolean on
#: `aam.rule.model` under the same name, which is what lets `_model_values()` copy
#: them across by name instead of maintaining a mapping.
TOOLBAR_FLAGS = [
    'hide_export', 'hide_import', 'hide_print', 'hide_duplicate',
    'hide_archive', 'hide_spreadsheet', 'hide_action_button', 'hide_edit_button',
]

#: Same trick for the two per-model line models that are nothing but booleans.
CHATTER_FLAGS = [
    'hide_chatter', 'hide_send_message', 'hide_log_note',
    'hide_activity', 'hide_followers', 'hide_attachments',
]
SEARCH_FLAGS = [
    'hide_all_filters', 'hide_all_groupby', 'hide_custom_filter',
    'hide_custom_groupby', 'hide_delete_filter', 'hide_favourite',
    'hide_search_panel',
]

#: Account-wide switches. Only the ones with no per-model equivalent are offered,
#: so a tick in this wizard never means two different things.
GLOBAL_FLAGS = [
    'readonly_user', 'disable_login', 'disable_developer_mode',
    'restrict_rpc', 'restrict_module_manage',
]


class AamRuleWizard(models.TransientModel):
    _name = 'aam.rule.wizard'
    _description = 'Guided Restriction Setup'

    state = fields.Selection(STEPS, default='who', required=True)
    #: Set only in edit mode. Its presence is what makes Apply update instead of
    #: create, and what the review step reads to say which it will do.
    rule_id = fields.Many2one('aam.rule', 'Editing Rule', ondelete='cascade')

    # -- step 1: who -------------------------------------------------------
    # `target_type` deliberately omits 'all' and 'profile'. 'all' always trips
    # admin protection, and 'profile' is what the Save-as-profile checkbox on the
    # last step produces - offering it here too would be two doors to one room.
    target_type = fields.Selection(
        [('user', 'Specific Users'), ('group', 'Security Groups')],
        string='Apply To', required=True, default='user')
    user_ids = fields.Many2many('res.users', string='Users',
                                domain=[('share', '=', False)])
    group_ids = fields.Many2many('res.groups', string='Groups')
    preset_id = fields.Many2one(
        'aam.preset', 'Start From Preset',
        help="Optional. Fills in the later steps from a ready-made preset, which "
             "you can then change. Leave empty to start from nothing.")
    audience = fields.Html(compute='_compute_audience')
    #: Drives the warning banner, and blocks Apply. Computed rather than checked
    #: at save time so the answer arrives while there is still something to do
    #: about it.
    hits_protected = fields.Boolean(compute='_compute_audience')

    # -- step 2: what ------------------------------------------------------
    model_ids = fields.Many2many(
        'ir.model', string='Models', domain=[('transient', '=', False)])
    menu_ids = fields.Many2many('ir.ui.menu', string='Menus To Hide')

    # -- step 3: restrict --------------------------------------------------
    access_level = fields.Selection(
        ACCESS_LEVELS, string='They Can', required=True, default='none')
    no_create = fields.Boolean('Cannot create')
    no_read = fields.Boolean('Cannot open')
    no_write = fields.Boolean('Cannot edit')
    no_unlink = fields.Boolean('Cannot delete')

    hide_export = fields.Boolean('Export')
    hide_import = fields.Boolean('Import')
    hide_print = fields.Boolean('Print')
    hide_duplicate = fields.Boolean('Duplicate')
    hide_archive = fields.Boolean('Archive')
    hide_spreadsheet = fields.Boolean('Insert in Spreadsheet')
    hide_action_button = fields.Boolean('Cog menu')
    hide_edit_button = fields.Boolean('Edit button')

    record_scope = fields.Selection(
        RECORD_SCOPES, string='Which Records', required=True, default='all')
    domain = fields.Text(
        'Domain', help="A domain evaluated with `user` in scope, e.g. "
                       "[('user_id', '=', user.id)].")
    domain_on_read = fields.Boolean('On read', default=True)
    domain_on_write = fields.Boolean('On edit', default=True)
    domain_on_unlink = fields.Boolean('On delete', default=True)
    domain_on_create = fields.Boolean('On create')

    field_line_ids = fields.One2many(
        'aam.rule.wizard.field', 'wizard_id', string='Fields')
    button_line_ids = fields.One2many(
        'aam.rule.wizard.button', 'wizard_id', string='Buttons & Tabs')

    hide_chatter = fields.Boolean('Whole chatter')
    hide_send_message = fields.Boolean('Send message')
    hide_log_note = fields.Boolean('Log note')
    hide_activity = fields.Boolean('Activities')
    hide_followers = fields.Boolean('Followers')
    hide_attachments = fields.Boolean('Attachments')

    hide_all_filters = fields.Boolean('All filters')
    hide_all_groupby = fields.Boolean('All group-bys')
    hide_custom_filter = fields.Boolean('Custom filter')
    hide_custom_groupby = fields.Boolean('Custom group-by')
    hide_delete_filter = fields.Boolean('Delete favourites')
    hide_favourite = fields.Boolean('Favourites')
    hide_search_panel = fields.Boolean('Search panel')

    readonly_user = fields.Boolean('Read-only everywhere')
    disable_login = fields.Boolean('Cannot log in')
    disable_developer_mode = fields.Boolean('No developer mode')
    restrict_rpc = fields.Boolean('No external API')
    restrict_module_manage = fields.Boolean('No app install or upgrade')

    # -- step 4: review ----------------------------------------------------
    rule_name = fields.Char('Rule Name')
    enforcement = fields.Selection(
        ENFORCEMENT_MODES, string='Enforcement', required=True, default='enforced')
    save_as_profile = fields.Boolean(
        'Save As Reusable Profile',
        help="Also create an Access Profile holding this rule, so the same policy "
             "can be handed to other users or groups later.")
    profile_name = fields.Char('Profile Name')
    summary = fields.Html(compute='_compute_summary')

    # ------------------------------------------------------------------
    # Audience
    # ------------------------------------------------------------------

    @api.depends('target_type', 'user_ids', 'group_ids')
    def _compute_audience(self):
        """Who this will reach, and whether that includes someone protected.

        The count comes from `aam.rule._targeted_user_ids()` rather than from
        counting members here, so the wizard and the enforcement layer can never
        disagree about who a target means - group expansion through implied
        groups included.
        """
        Policy = self.env['aam.policy']
        for wizard in self:
            users = wizard._resolved_users()
            protected = users.filtered(lambda u: Policy._is_protected(u))
            wizard.hits_protected = bool(protected)
            if not users:
                wizard.audience = _(
                    "<p class='text-muted'>Nobody selected yet.</p>")
            elif protected:
                wizard.audience = _(
                    "<p><b>%(count)s user(s)</b> would be affected.</p>"
                    "<div class='alert alert-warning mb-0'><b>%(names)s</b> "
                    "cannot be restricted: administrators are protected so that a "
                    "rule can never lock everyone out. Remove them, or turn on "
                    "<i>Allow restricting administrators</i> in Settings.</div>",
                    count=len(users),
                    names=', '.join(protected.mapped('name')))
            else:
                wizard.audience = _(
                    "<p><b>%s user(s)</b> would be affected.</p>", len(users))

    def _resolved_users(self):
        """The audience, resolved exactly the way the policy layer resolves it."""
        self.ensure_one()
        if self.target_type == 'user':
            return self.user_ids
        # `include_implied_groups` defaults to True on aam.rule, so mirror that.
        # On Odoo 18 it is inert anyway - see models/aam_group_compat.py.
        return group_members(self.group_ids)

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def action_next(self):
        return self._step(+1)

    def action_back(self):
        return self._step(-1)

    def _step(self, delta):
        self.ensure_one()
        index = _STEP_ORDER.index(self.state) + delta
        index = max(0, min(index, len(_STEP_ORDER) - 1))
        if delta > 0:
            self._validate_step()
        self.state = _STEP_ORDER[index]
        return self._reopen()

    def _validate_step(self):
        """Refuse to move on from a step that cannot produce a valid rule.

        Catching this here rather than at create time means the message names the
        step you are on, instead of arriving three screens later as a constraint
        violation.
        """
        self.ensure_one()
        if self.state == 'who':
            if self.target_type == 'user' and not self.user_ids:
                raise UserError(_("Pick at least one user."))
            if self.target_type == 'group' and not self.group_ids:
                raise UserError(_("Pick at least one group."))
        elif self.state == 'what':
            if not self.model_ids and not self.menu_ids:
                raise UserError(_(
                    "Pick at least one model or one menu - otherwise there is "
                    "nothing for the rule to restrict."))

    def _reopen(self):
        """Re-render the dialog at the same record.

        The same idiom the import wizard uses to move between its phases
        (`aam_rules_io.py`): write, then return an act_window at self. Without
        the `dialog_size` the dialog would snap back to its default width on
        every step.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _("Restriction Setup"),
            'context': dict(self.env.context, dialog_size='large'),
        }

    # ------------------------------------------------------------------
    # Preset seeding
    # ------------------------------------------------------------------

    @api.onchange('preset_id')
    def _onchange_preset_id(self):
        """Fill the later steps from a preset, as a starting point you can edit.

        Seeds only what the wizard can represent - the models, the menus, and the
        access level and toolbar switches from the spec's first model line. A
        preset whose models differ from each other seeds from the first and the
        rest is yours to adjust, which is the same trade the wizard makes
        everywhere else.
        """
        Model = self.env['ir.model'].sudo()
        for wizard in self:
            if not wizard.preset_id:
                continue
            spec = self.env['aam.preset']._catalogue().get(wizard.preset_id.key) or {}

            names = [name for name in self.env['aam.preset']._spec_models(spec)
                     if name in self.env]
            wizard.model_ids = [(6, 0, Model.search(
                [('model', 'in', names)]).ids if names else [])]

            menus = [self.env.ref(line['xmlid'], raise_if_not_found=False)
                     for line in spec.get('menu_lines', [])]
            wizard.menu_ids = [(6, 0, [menu.id for menu in menus if menu])]

            if not wizard.rule_name:
                wizard.rule_name = wizard.preset_id.name

            lines = spec.get('model_lines') or [{}]
            first = lines[0]
            if first.get('readonly_model'):
                wizard.access_level = 'readonly'
            elif first.get('no_create') and first.get('no_unlink'):
                wizard.access_level = 'no_create_delete'
            elif first.get('no_unlink'):
                wizard.access_level = 'no_delete'
            for flag in TOOLBAR_FLAGS:
                wizard[flag] = bool(first.get(flag))
            if first.get('domain'):
                wizard.record_scope = 'custom'
                wizard.domain = first['domain']

            wizard.field_line_ids = [(5, 0, 0)] + [
                (0, 0, values) for values in wizard._preset_field_lines(spec)]

    def _preset_field_lines(self, spec):
        """Field lines from a preset spec, dropping what this database lacks."""
        Model = self.env['ir.model'].sudo()
        Field = self.env['ir.model.fields'].sudo()
        out = []
        for line in spec.get('field_lines', []):
            model_name, field_name = line['model'], line['field']
            if model_name not in self.env or field_name not in self.env[model_name]._fields:
                continue
            model = Model.search([('model', '=', model_name)], limit=1)
            field = Field.search(
                [('model', '=', model_name), ('name', '=', field_name)], limit=1)
            if not model or not field:
                continue
            mask = line.get('mask_type', 'none')
            out.append({
                'model_id': model.id,
                'field_id': field.id,
                'treatment': ('mask' if mask and mask != 'none'
                              else 'readonly' if line.get('readonly')
                              else 'hide'),
                'mask_type': mask if mask and mask != 'none' else 'full',
            })
        return out

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    @api.depends('state', 'target_type', 'user_ids', 'group_ids', 'model_ids',
                 'menu_ids', 'access_level', 'record_scope', 'field_line_ids',
                 'button_line_ids', 'rule_id')
    def _compute_summary(self):
        for wizard in self:
            wizard.summary = wizard._summary_html()

    def _summary_html(self):
        self.ensure_one()
        users = self._resolved_users()
        target = ', '.join(
            (self.user_ids if self.target_type == 'user' else self.group_ids)
            .mapped('name')) or _("nobody")

        effects = []
        level = dict(ACCESS_LEVELS).get(self.access_level)
        if self.access_level != 'none':
            effects.append(_("Access on each model: <b>%s</b>", level))
        hidden = [self._fields[flag].string for flag in TOOLBAR_FLAGS
                  if self[flag]]
        if hidden:
            effects.append(_("Hidden: %s", ', '.join(hidden)))
        if self.record_scope != 'all':
            effects.append(_("Records limited to: <b>%s</b>",
                             dict(RECORD_SCOPES).get(self.record_scope)))
        if self.field_line_ids:
            effects.append(_("%s field restriction(s)", len(self.field_line_ids)))
        if self.button_line_ids:
            effects.append(_("%s button or tab hidden", len(self.button_line_ids)))
        if self.menu_ids:
            effects.append(_("%s menu(s) hidden", len(self.menu_ids)))
        chatter = [self._fields[f].string for f in CHATTER_FLAGS if self[f]]
        if chatter:
            effects.append(_("Chatter: %s", ', '.join(chatter)))
        search = [self._fields[f].string for f in SEARCH_FLAGS if self[f]]
        if search:
            effects.append(_("Search: %s", ', '.join(search)))
        globals_ = [self._fields[f].string for f in GLOBAL_FLAGS if self[f]]
        if globals_:
            effects.append(_("Everywhere: %s", ', '.join(globals_)))

        if not effects:
            body = _("<div class='alert alert-warning mb-0'>Nothing selected yet - "
                     "this rule would not do anything.</div>")
        else:
            body = "<ul>%s</ul>" % ''.join("<li>%s</li>" % e for e in effects)

        verb = _("Update") if self.rule_id else _("Create")
        head = _("<p><b>%(verb)s</b> a rule for <b>%(target)s</b> "
                 "(%(count)s user(s)), covering %(models)s.</p>",
                 verb=verb, target=target, count=len(users),
                 models=', '.join(self.model_ids.mapped('model')) or _("no model"))
        return head + body

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def action_apply(self):
        self.ensure_one()
        if self.hits_protected:
            raise UserError(_(
                "This selection includes an administrator, who cannot be "
                "restricted. Remove them, or turn on 'Allow restricting "
                "administrators' in Settings."))

        values = self._rule_values()
        if self.rule_id:
            # Replace the lines wholesale: an edit only ever reaches a rule that
            # `_unsupported_reasons` has already cleared as representable, so
            # there is nothing here the wizard could be discarding.
            self.rule_id.write(values)
            rule = self.rule_id
        else:
            rule = self.env['aam.rule'].create(values)

        if self.save_as_profile and not rule.profile_id:
            profile = self.env['aam.profile'].create({
                'name': self.profile_name or rule.name,
                'user_ids': [(6, 0, self.user_ids.ids)],
                'group_ids': [(6, 0, self.group_ids.ids)],
            })
            rule.write({'target_type': 'profile', 'profile_id': profile.id})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aam.rule',
            'res_id': rule.id,
            'view_mode': 'form',
            'name': _("Restriction applied"),
        }

    def _rule_values(self):
        self.ensure_one()
        values = {
            'name': self.rule_name or self._default_name(),
            'target_type': self.target_type,
            'user_ids': [(6, 0, self.user_ids.ids)],
            'group_ids': [(6, 0, self.group_ids.ids)],
            'enforcement': self.enforcement,
            'model_line_ids': [(5, 0, 0)] + [
                (0, 0, line) for line in self._model_values()],
            'field_line_ids': [(5, 0, 0)] + [
                (0, 0, line) for line in self._field_values()],
            'menu_line_ids': [(5, 0, 0)] + [
                (0, 0, {'menu_id': menu.id, 'include_children': True})
                for menu in self.menu_ids],
            'chatter_line_ids': [(5, 0, 0)] + [
                (0, 0, line) for line in self._flag_values(CHATTER_FLAGS)],
            'search_line_ids': [(5, 0, 0)] + [
                (0, 0, line) for line in self._flag_values(SEARCH_FLAGS)],
            'button_line_ids': [(5, 0, 0)] + [
                (0, 0, line) for line in self._button_values()],
        }
        values.update({flag: self[flag] for flag in GLOBAL_FLAGS})
        return values

    def _default_name(self):
        who = ', '.join(
            (self.user_ids if self.target_type == 'user' else self.group_ids)
            .mapped('name')[:2])
        return _("Restrictions for %s", who or _("selection"))

    def _model_values(self):
        """One `aam.rule.model` line per chosen model, all identical.

        Uniform by design - the wizard trades per-model tuning for a single
        screen, and what it produces is an ordinary rule you can tune afterwards.
        """
        out = []
        for model in self.model_ids:
            line = {'model_id': model.id}
            if self.access_level == 'readonly':
                # The model's own shorthand. `_blocked_modes()` expands it, so
                # this works even though the onchange never fires here.
                line['readonly_model'] = True
            elif self.access_level == 'no_delete':
                line['no_unlink'] = True
            elif self.access_level == 'no_create_delete':
                line.update({'no_create': True, 'no_unlink': True})
            elif self.access_level == 'custom':
                line.update({
                    'no_create': self.no_create, 'no_read': self.no_read,
                    'no_write': self.no_write, 'no_unlink': self.no_unlink,
                })
            line.update({flag: self[flag] for flag in TOOLBAR_FLAGS})

            domain = self._domain_for(model.model)
            if domain:
                line.update({
                    'domain': domain,
                    'domain_on_read': self.domain_on_read,
                    'domain_on_write': self.domain_on_write,
                    'domain_on_unlink': self.domain_on_unlink,
                    'domain_on_create': self.domain_on_create,
                })
            out.append(line)
        return out

    def _domain_for(self, model_name):
        """The record limit for one model, or None when it cannot carry one.

        "Their own records" is resolved per model rather than hard-coded: most
        models use a `user_id` many2one, some (project.task) a `user_ids`
        many2many, and a model with neither simply gets no domain instead of a
        broken one.
        """
        self.ensure_one()
        if self.record_scope == 'all':
            return None
        if self.record_scope == 'custom':
            return self.domain or None

        model_fields = self.env[model_name]._fields
        if self.record_scope == 'own':
            for name in ('user_id', 'user_ids'):
                field = model_fields.get(name)
                if field and field.comodel_name == 'res.users':
                    if field.type in ('many2many', 'one2many'):
                        return "[('%s', 'in', [user.id])]" % name
                    return "[('%s', '=', user.id)]" % name
            return None
        # company
        field = model_fields.get('company_id')
        if field and field.comodel_name == 'res.company':
            return "[('company_id', '=', user.company_id.id)]"
        return None

    def _field_values(self):
        out = []
        for line in self.field_line_ids:
            values = {'model_id': line.model_id.id, 'field_id': line.field_id.id}
            if line.treatment == 'hide':
                values['invisible'] = True
            elif line.treatment == 'readonly':
                values['readonly'] = True
            elif line.treatment == 'required':
                values['required'] = True
            else:
                values['mask_type'] = line.mask_type
            out.append(values)
        return out

    def _flag_values(self, flags):
        """One line per model for the boolean-only line models.

        Skipped entirely when nothing is ticked, so a rule never carries an empty
        chatter or search line just because the step was visited.
        """
        chosen = {flag: self[flag] for flag in flags if self[flag]}
        if not chosen:
            return []
        return [dict(chosen, model_id=model.id) for model in self.model_ids]

    def _button_values(self):
        return [{
            'model_id': line.model_id.id,
            'element_type': line.element_type,
            'element_name': line.element_name,
            'view_mode': line.view_mode,
        } for line in self.button_line_ids]

    # ------------------------------------------------------------------
    # Edit mode
    # ------------------------------------------------------------------

    @api.model
    def action_open_for_rule(self, rule):
        """Load an existing rule back into the steps, or explain why not."""
        reasons = self._unsupported_reasons(rule)
        if reasons:
            raise UserError(_(
                "This rule uses settings the guided wizard cannot show:\n\n%s\n\n"
                "Edit it on the rule form instead - nothing is lost there.",
                '\n'.join('  - %s' % reason for reason in reasons)))
        wizard = self.create(self._values_from_rule(rule))
        return wizard._reopen()

    @api.model
    def _unsupported_reasons(self, rule):
        """Everything about `rule` the wizard would flatten if it loaded it.

        The guard is a check on open, not a merge on save. A partial-preservation
        merge is the kind of code that quietly drops somebody's `condition` two
        releases later; refusing is honest, and the rule form can still do
        everything.
        """
        reasons = []
        if rule.target_type not in ('user', 'group'):
            reasons.append(_("it targets %s",
                             dict(rule._fields['target_type'].selection).get(
                                 rule.target_type)))
        if rule.time_window_ids:
            reasons.append(_("it has %s time window(s)", len(rule.time_window_ids)))

        lines = rule.model_line_ids
        if lines:
            # The wizard writes one identical line per model. Anything else came
            # from the rule form and cannot survive the round trip.
            compared = [
                {name: line[name] for name in (
                    ['no_create', 'no_read', 'no_write', 'no_unlink',
                     'readonly_model'] + TOOLBAR_FLAGS)}
                for line in lines
            ]
            if any(values != compared[0] for values in compared[1:]):
                reasons.append(_("its models are restricted differently from "
                                 "each other"))
            if any(line.related_field_id or line.hierarchy_field_id
                   or line.soft_restrict for line in lines):
                reasons.append(_("it uses a related field, a hierarchy field or "
                                 "soft restriction"))
            domains = {line.domain or '' for line in lines}
            if len(domains) > 1:
                reasons.append(_("its models carry different record domains"))

        if any(line.condition for line in rule.field_line_ids):
            reasons.append(_("a field restriction is conditional"))
        if any(line.condition for line in rule.button_line_ids):
            reasons.append(_("a button restriction is conditional"))
        if any(line.field_domain or line.no_open or line.no_create
               or line.no_quick_create or line.no_create_edit or line.no_export
               for line in rule.field_line_ids):
            reasons.append(_("a field restriction uses an option the wizard does "
                             "not offer"))
        return reasons

    @api.model
    def _values_from_rule(self, rule):
        """Invert `_rule_values`. Only ever called on a representable rule."""
        first = rule.model_line_ids[:1]
        values = {
            'state': 'who',
            'rule_id': rule.id,
            'rule_name': rule.name,
            'enforcement': rule.enforcement,
            'target_type': rule.target_type,
            'user_ids': [(6, 0, rule.user_ids.ids)],
            'group_ids': [(6, 0, rule.group_ids.ids)],
            'model_ids': [(6, 0, rule.model_line_ids.model_id.ids)],
            'menu_ids': [(6, 0, rule.menu_line_ids.menu_id.ids)],
            'field_line_ids': [(0, 0, {
                'model_id': line.model_id.id,
                'field_id': line.field_id.id,
                'treatment': ('hide' if line.invisible
                              else 'readonly' if line.readonly
                              else 'required' if line.required
                              else 'mask'),
                'mask_type': line.mask_type,
            }) for line in rule.field_line_ids],
            'button_line_ids': [(0, 0, {
                'model_id': line.model_id.id,
                'element_type': line.element_type,
                'element_name': line.element_name,
                'view_mode': line.view_mode,
            }) for line in rule.button_line_ids],
        }
        values.update({flag: rule[flag] for flag in GLOBAL_FLAGS})

        if first:
            values['access_level'] = (
                'readonly' if first.readonly_model
                else 'no_create_delete' if first.no_create and first.no_unlink
                else 'no_delete' if first.no_unlink
                else 'custom' if (first.no_create or first.no_read
                                  or first.no_write)
                else 'none')
            values.update({
                'no_create': first.no_create, 'no_read': first.no_read,
                'no_write': first.no_write, 'no_unlink': first.no_unlink,
            })
            values.update({flag: first[flag] for flag in TOOLBAR_FLAGS})
            if first.domain:
                values.update({
                    'record_scope': 'custom',
                    'domain': first.domain,
                    'domain_on_read': first.domain_on_read,
                    'domain_on_write': first.domain_on_write,
                    'domain_on_unlink': first.domain_on_unlink,
                    'domain_on_create': first.domain_on_create,
                })

        chatter = rule.chatter_line_ids[:1]
        if chatter:
            values.update({flag: chatter[flag] for flag in CHATTER_FLAGS})
        search = rule.search_line_ids[:1]
        if search:
            values.update({flag: search[flag] for flag in SEARCH_FLAGS})
        return values


class AamRuleWizardField(models.TransientModel):
    _name = 'aam.rule.wizard.field'
    _description = 'Guided Setup Field Restriction'

    wizard_id = fields.Many2one('aam.rule.wizard', required=True,
                                ondelete='cascade')
    model_id = fields.Many2one('ir.model', 'Model', required=True,
                               ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', 'Field', required=True,
                               ondelete='cascade')
    field_ttype = fields.Selection(related='field_id.ttype')
    #: One choice instead of four booleans. `aam.rule.field` refuses `invisible`
    #: and `required` together; a single selection makes that unrepresentable
    #: rather than merely invalid.
    treatment = fields.Selection(FIELD_TREATMENTS, required=True, default='hide')
    mask_type = fields.Selection(
        [('full', 'Everything'), ('partial', 'All but the last few'),
         ('email', 'Email'), ('phone', 'Phone')],
        string='Mask', default='full')

    @api.onchange('model_id')
    def _onchange_model_id(self):
        """Drop a field that no longer belongs to the chosen model."""
        for line in self:
            if line.field_id and line.field_id.model_id != line.model_id:
                line.field_id = False

    @api.constrains('treatment', 'field_id')
    def _check_maskable(self):
        """Mirror `aam.rule.field._check_maskable` so the error arrives here.

        Without it the wizard would accept a masked binary field and only fail on
        Apply, three steps later, naming a model the user never typed.
        """
        for line in self:
            if line.treatment == 'mask' and line.field_ttype not in MASKABLE_TYPES:
                raise ValidationError(_(
                    "%(field)s is a %(type)s field and cannot be masked. Hide it "
                    "or make it read-only instead.",
                    field=line.field_id.field_description or line.field_id.name,
                    type=line.field_ttype))


class AamRuleWizardButton(models.TransientModel):
    _name = 'aam.rule.wizard.button'
    _description = 'Guided Setup Button Restriction'

    wizard_id = fields.Many2one('aam.rule.wizard', required=True,
                                ondelete='cascade')
    model_id = fields.Many2one('ir.model', 'Model', required=True,
                               ondelete='cascade')
    element_type = fields.Selection(
        [('button', 'Button'), ('tab', 'Tab'), ('kanban_link', 'Kanban Link')],
        string='Type', required=True, default='button')
    element_name = fields.Char(
        'Name', required=True,
        help="The button's method name, or the notebook page's `name` attribute. "
             "Turn on developer mode and hover the element to find it.")
    view_mode = fields.Selection(
        [('all', 'All Views'), ('form', 'Form'), ('list', 'List'),
         ('kanban', 'Kanban')],
        string='In', required=True, default='all')
