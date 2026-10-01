"""The Access Explainer: answers "why can't this user see that?"

Every comparable module can tell you the *state* of access. None of them tell
you the *cause*. When a user reports a missing button, an administrator has to
guess whether it was this module, a native ACL row, a record rule, or a missing
group - and then bisect by disabling things.

This wizard reports one line per effect, each naming what produced it, across
all four sources at once. It deliberately does not use the compiled policy:
that structure merges rules together and discards which one contributed what,
which is precisely the information needed here. Attribution costs a re-walk of
the rules, which is fine for a diagnostic run.
"""

from odoo import _, api, fields, models
from ..models.aam_group_compat import group_members, user_groups


SOURCES = [
    ('aam', 'Access Rule'),
    ('acl', 'Model Access (ACL)'),
    ('record_rule', 'Record Rule'),
    ('group', 'Security Group'),
    ('profile', 'Access Profile'),
]

CATEGORIES = [
    ('global', 'Everywhere'),
    ('menu', 'Menu'),
    ('model', 'Model'),
    ('field', 'Field'),
    ('button', 'Button / Tab'),
    ('search', 'Search Panel'),
    ('chatter', 'Chatter'),
    ('record', 'Records'),
]


class AamExplain(models.TransientModel):
    _name = 'aam.explain'
    _description = 'Explain Access'

    user_id = fields.Many2one(
        'res.users', 'User', required=True, default=lambda s: s.env.user,
        domain=[('share', '=', False)])
    model_id = fields.Many2one(
        'ir.model', 'Model', domain=[('transient', '=', False)],
        help="Leave empty to see only the user's database-wide restrictions.")
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda s: s.env.company)

    line_ids = fields.One2many('aam.explain.line', 'explain_id', string='Findings')
    summary = fields.Html('Summary', compute='_compute_summary')
    is_protected = fields.Boolean(compute='_compute_summary')
    #: Whether `action_explain` has run for the *current* selection. Empty
    #: `line_ids` means "not run yet" exactly as often as it means "ran and
    #: found nothing", and the summary used to read the second into the first -
    #: so a user who picked a user and a model was told "No restrictions found"
    #: before pressing anything.
    has_run = fields.Boolean(default=False)

    @api.onchange('user_id', 'model_id', 'company_id')
    def _onchange_selection(self):
        """Drop findings that belong to a selection the user has moved on from.

        `line_ids` is stored state, written only by `action_explain`. Without
        this, changing the model left the previous model's findings on screen
        and the summary presented them as the answer for the new one - the
        failure looked like "the Explainer does nothing when I change the
        model".
        """
        for wizard in self:
            wizard.line_ids = [fields.Command.clear()]
            wizard.has_run = False

    def write(self, vals):
        """Keep the stored findings tied to the selection that produced them.

        The onchange above clears the *display*, but `line_ids` is `readonly`
        in the form view and Odoo drops readonly fields from the write payload,
        so the rows survived in the database and came back on the next read.
        Clearing them here makes the stored state agree with the screen however
        the selection was changed - form, RPC or code.
        """
        watched = ('user_id', 'model_id', 'company_id')
        moved_on = self.filtered(lambda w: any(
            field in vals and vals[field] != w[field].id for field in watched))
        result = super().write(vals)
        if moved_on:
            moved_on.line_ids.unlink()
            moved_on.has_run = False
        return result

    @api.depends('user_id', 'model_id', 'line_ids', 'has_run')
    def _compute_summary(self):
        for wizard in self:
            protected = wizard.user_id and self.env['aam.policy']._is_protected(wizard.user_id)
            wizard.is_protected = bool(protected)
            if protected:
                # Stated before the run on purpose: it is a property of the
                # user, not a finding, and it is the answer most of the time.
                wizard.summary = _(
                    "<p><b>%s is an administrator and is never restricted by this "
                    "module.</b></p><p>Native access rights and record rules still "
                    "apply and are listed below.</p>", wizard.user_id.name)
            elif not wizard.has_run:
                wizard.summary = _(
                    "<p class='text-muted'>Choose a user and a model, then press "
                    "<b>Explain</b>.</p>")
            elif not wizard.line_ids:
                wizard.summary = _(
                    "<p>No restrictions found for %s%s.</p>",
                    wizard.user_id.name,
                    _(" on %s", wizard.model_id.name) if wizard.model_id else '')
            else:
                wizard.summary = wizard._summary_html()

    def _summary_html(self):
        """Totals, then each rule once with the path it took to reach the user.

        The path is identical for every effect a rule produces, so repeating it
        down a table column was 16 rows of the same sentence, clipped. Stating
        it once per rule is both shorter and more readable.
        """
        self.ensure_one()
        labels = dict(SOURCES)
        by_source = {}
        for line in self.line_ids:
            by_source[line.source] = by_source.get(line.source, 0) + 1
        counts = ', '.join('%s: %s' % (labels.get(src, src), n)
                           for src, n in sorted(by_source.items()))

        rows = []
        seen = set()
        for line in self.line_ids:
            if not line.rule_id or line.rule_id.id in seen:
                continue
            seen.add(line.rule_id.id)
            rows.append(
                "<tr><td style='padding-right:1.5rem'><b>%s</b></td><td>%s</td></tr>"
                % (line.rule_id.name, line.reason or ''))

        html = _("<p><b>%(total)s effect(s)</b> apply to %(user)s. &nbsp;"
                 "<span class='text-muted'>%(counts)s</span></p>",
                 total=len(self.line_ids), user=self.user_id.name, counts=counts)
        if rows:
            html += _("<p class='mb-1 text-muted'>Reached through:</p>"
                      "<table class='mb-3'>%s</table>", ''.join(rows))
        return html

    # ------------------------------------------------------------------

    def action_explain(self):
        """Rebuild the findings for the current selection."""
        self.ensure_one()
        self.line_ids.unlink()
        values = self._collect()
        if values:
            self.env['aam.explain.line'].create([
                dict(v, explain_id=self.id) for v in values])
        self.has_run = True
        # Recompute the summary against the freshly written lines.
        self.invalidate_recordset(['line_ids'])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aam.explain',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _("Access Explainer"),
            # Without this the dialog reopens at the default width and the
            # findings table loses its last column on the way back.
            'context': dict(self.env.context, dialog_size='extra-large'),
        }

    def _collect(self):
        self.ensure_one()
        user = self.user_id
        model_name = self.model_id.model or None
        out = []
        if not self.env['aam.policy']._is_protected(user):
            out += self._collect_from_rules(user, model_name)
        out += self._collect_native(user, model_name)
        return out

    # ------------------------------------------------------------------
    # Our own rules - the part that carries attribution
    # ------------------------------------------------------------------

    def _collect_from_rules(self, user, model_name):
        Policy = self.env['aam.policy']
        rules = Policy._rules_for_user(user, self.company_id.id or self.env.company.id)
        out = []
        for rule in rules:
            reason = self._rule_reason(rule, user)
            out += self._explain_globals(rule, reason)
            out += self._explain_menus(rule, reason)
            if model_name:
                out += self._explain_model(rule, reason, model_name)
        return out

    def _rule_reason(self, rule, user):
        """Why this rule reaches this user - the half administrators forget.

        Kept short on purpose: this is a table column, and a sentence long
        enough to be truncated tells you nothing. "Profile: Warehouse Operator
        (via Warehouse Crew)" is the whole chain in one glance.
        """
        if rule.target_type == 'all':
            return _("Everyone")
        if rule.target_type == 'user':
            return _("Direct")
        if rule.target_type == 'profile':
            profile = rule.profile_id
            if user in profile.user_ids:
                return _("Profile: %s", profile.name)
            groups = profile.group_ids.filtered(lambda g: user in group_members(g))
            if groups:
                return _("Profile: %(p)s (via %(g)s)", p=profile.name, g=groups[0].name)
            return _("Profile: %s", profile.name)
        groups = rule.group_ids.filtered(lambda g: user in group_members(g))
        if groups:
            # Odoo 18 cannot tell a direct member from an implied one - the
            # closure is materialised into res_groups_users_rel, so both are the
            # same row (see models/aam_group_compat.py). Name the sub-group that
            # explains the membership where one does, which is more useful than
            # the bare "(implied)" it replaces, and just the group otherwise.
            via = user_groups(user).filtered(
                lambda g: g != groups[0] and groups[0] in g.trans_implied_ids)
            if via:
                return _("Group: %(g)s (via %(v)s)", g=groups[0].name, v=via[0].name)
            return _("Group: %s", groups[0].name)
        return _("Group")

    def _line(self, rule, reason, category, target, effect, source='aam'):
        return {
            'source': source,
            'category': category,
            'target': target,
            'effect': effect,
            'rule_id': rule.id if rule else False,
            'reason': reason,
        }

    def _explain_globals(self, rule, reason):
        out = []
        labels = {
            f: rule._fields[f].string
            for f in rule._fields
            if f.startswith(('hide_', 'readonly_', 'disable_', 'restrict_'))
        }
        for flag, label in labels.items():
            if getattr(rule, flag, False):
                out.append(self._line(
                    rule, reason, 'global', _("Everywhere"), label))
        return out

    def _explain_menus(self, rule, reason):
        out = []
        for line in rule.menu_line_ids.filtered('active'):
            out.append(self._line(
                rule, reason, 'menu', line.menu_id.complete_name or line.menu_id.name,
                _("Hidden, with sub-menus") if line.include_children else _("Hidden")))
        return out

    def _explain_model(self, rule, reason, model_name):
        out = []
        for line in rule.model_line_ids.filtered(lambda l: l.active and l.model_name == model_name):
            for mode in sorted(line._blocked_modes()):
                out.append(self._line(
                    rule, reason, 'model', model_name, _("Blocked: %s", mode)))
            for flag in ('hide_archive', 'hide_duplicate', 'hide_export', 'hide_import',
                         'hide_spreadsheet', 'hide_print', 'hide_action_button',
                         'hide_edit_button'):
                if getattr(line, flag):
                    out.append(self._line(
                        rule, reason, 'model', model_name, line._fields[flag].string))
            modes = line._domain_modes()
            if modes:
                out.append(self._line(
                    rule, reason, 'record', model_name,
                    _("Limited to %(domain)s for %(modes)s%(soft)s",
                      domain=line.domain, modes=', '.join(sorted(modes)),
                      soft=_(" (soft)") if line.soft_restrict else '')))

        for line in rule.field_line_ids.filtered(lambda l: l.active and l.model_name == model_name):
            effects = [line._fields[f].string
                       for f in ('invisible', 'readonly', 'required', 'no_open', 'no_create',
                                 'no_quick_create', 'no_create_edit', 'no_export')
                       if getattr(line, f)]
            if line.mask_type and line.mask_type != 'none':
                effects.append(_("Masked (%s)", dict(
                    line._fields['mask_type'].selection).get(line.mask_type)))
            if effects:
                effect = ', '.join(effects)
                if line.condition:
                    effect = _("%(e)s when %(c)s", e=effect, c=line.condition)
                out.append(self._line(
                    rule, reason, 'field', '%s.%s' % (model_name, line.field_name), effect))

        for line in rule.button_line_ids.filtered(lambda l: l.active and l.model_name == model_name):
            kind = dict(line._fields['element_type'].selection).get(line.element_type)
            effect = _("Hidden")
            if line.condition:
                effect = _("Hidden when %s", line.condition)
            out.append(self._line(
                rule, reason, 'button', '%s: %s' % (kind, line.element_name), effect))

        for line in rule.search_line_ids.filtered(lambda l: l.active and l.model_name == model_name):
            for flag in ('hide_all_filters', 'hide_all_groupby', 'hide_custom_filter',
                         'hide_custom_groupby', 'hide_delete_filter', 'hide_favourite',
                         'hide_search_panel'):
                if getattr(line, flag):
                    out.append(self._line(
                        rule, reason, 'search', model_name, line._fields[flag].string))
            if line.filter_names:
                out.append(self._line(
                    rule, reason, 'search', model_name,
                    _("Filters hidden: %s", line.filter_names)))
            if line.groupby_names:
                out.append(self._line(
                    rule, reason, 'search', model_name,
                    _("Group By hidden: %s", line.groupby_names)))

        for line in rule.chatter_line_ids.filtered(lambda l: l.active and l.model_name == model_name):
            for flag in ('hide_chatter', 'hide_send_message', 'hide_log_note',
                         'hide_activity', 'hide_followers', 'hide_attachments'):
                if getattr(line, flag):
                    out.append(self._line(
                        rule, reason, 'chatter', model_name, line._fields[flag].string))
        return out

    # ------------------------------------------------------------------
    # Native Odoo access - the other half of the answer
    # ------------------------------------------------------------------

    def _collect_native(self, user, model_name):
        if not model_name:
            return []
        out = []
        env = self.env(user=user)

        for mode in ('read', 'write', 'create', 'unlink'):
            if not env[model_name].sudo(False).with_user(user).has_access(mode):
                out.append({
                    'source': 'acl',
                    'category': 'model',
                    'target': model_name,
                    'effect': _("No %s access from native rights", mode),
                    'reason': _("granted by ir.model.access rows on this user's groups"),
                })

        rules = self.env['ir.rule'].sudo().search([('model_id.model', '=', model_name)])
        held_groups = user_groups(user)
        for rule in rules:
            applies = not rule.groups or bool(rule.groups & held_groups)
            if not applies:
                continue
            modes = [m for m in ('read', 'write', 'create', 'unlink')
                     if rule['perm_%s' % ('unlink' if m == 'unlink' else m)]]
            out.append({
                'source': 'record_rule',
                'category': 'record',
                'target': model_name,
                'effect': _("%(name)s: %(domain)s (%(modes)s)",
                            name=rule.name, domain=rule.domain_force or '[]',
                            modes=', '.join(modes) or 'none'),
                'reason': _("global record rule") if not rule.groups
                          else _("record rule on group '%s'", rule.groups[0].name),
            })
        return out


class AamExplainLine(models.TransientModel):
    _name = 'aam.explain.line'
    _description = 'Access Explanation'
    _order = 'source, category, target'

    explain_id = fields.Many2one('aam.explain', required=True, ondelete='cascade')
    source = fields.Selection(SOURCES, required=True)
    category = fields.Selection(CATEGORIES, required=True)
    target = fields.Char('Applies To')
    effect = fields.Char('Effect')
    reason = fields.Char('Why This User')
    rule_id = fields.Many2one('aam.rule', 'Rule')

    def action_open_rule(self):
        self.ensure_one()
        if not self.rule_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aam.rule',
            'res_id': self.rule_id.id,
            'view_mode': 'form',
        }
