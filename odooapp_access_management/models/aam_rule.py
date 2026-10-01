from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .aam_constants import (
    ENFORCEMENT_MODES,
    GLOBAL_FLAGS,
    PARAM_ALLOW_RESTRICT_ADMIN,
    PROTECTED_UIDS,
    TARGET_TYPES,
)
from .aam_group_compat import group_members


class AamRule(models.Model):
    """One access rule: who it applies to, when, and what it restricts.

    A rule is a container. The actual restrictions live in the ``*_line_ids``
    one2many children (menus, models, fields, buttons, search, chatter), plus
    the user-wide boolean toggles declared directly on this model.

    Rules are never evaluated one at a time at runtime - ``aam.policy``
    compiles every rule that applies to a user into a single cached dict. See
    ``models/aam_policy.py``.
    """

    _name = 'aam.rule'
    _description = 'Access Rule'
    _inherit = ['mail.thread']
    _order = 'priority desc, sequence, id'

    name = fields.Char(required=True, translate=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(default=10)
    note = fields.Text('Internal Note')

    priority = fields.Integer(
        default=10, tracking=True,
        help="Higher wins when two rules disagree. Note that a denial always beats a "
             "permission regardless of priority; this only breaks ties between "
             "restrictions of the same kind.",
    )

    # -- Targeting ---------------------------------------------------------
    target_type = fields.Selection(
        TARGET_TYPES, required=True, default='user', tracking=True,
        help="Who this rule applies to. 'Everyone' makes it database-wide.",
    )
    profile_id = fields.Many2one('aam.profile', ondelete='cascade', index=True, tracking=True)
    user_ids = fields.Many2many(
        'res.users', 'aam_rule_users_rel', 'rule_id', 'user_id', string='Users', tracking=True)
    group_ids = fields.Many2many(
        'res.groups', 'aam_rule_groups_rel', 'rule_id', 'group_id', string='Groups', tracking=True)
    include_implied_groups = fields.Boolean(
        'Include Implied Groups', default=True, readonly=True,
        help="Has no effect on Odoo 18. Group membership is stored already-expanded here, so a user who only implies a group is indistinguishable from one added to it directly, and the rule always reaches both. Kept so a rules file exported from Odoo 19 still imports without losing the setting.",
    )
    company_ids = fields.Many2many(
        'res.company', 'aam_rule_company_rel', 'rule_id', 'company_id', string='Companies',
        help="Apply only when one of these is the active company. Empty means all companies.",
    )

    # -- Validity ----------------------------------------------------------
    date_from = fields.Datetime('Active From', tracking=True)
    date_to = fields.Datetime('Active Until', tracking=True)
    auto_revoke = fields.Boolean(
        'Auto-Revoke on Expiry', default=True,
        help="When 'Active Until' passes, archive this rule automatically instead of "
             "leaving an expired record active.",
    )
    time_window_ids = fields.One2many('aam.time.window', 'rule_id', string='Time Windows')

    enforcement = fields.Selection(
        ENFORCEMENT_MODES, required=True, default='enforced', tracking=True,
        help="Enforced restrictions are applied on the server, so they also hold over "
             "XML-RPC and the JSON API. 'Hide in UI only' merely removes things from "
             "the interface and can be bypassed by a determined user.",
    )

    state = fields.Selection(
        [('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired')],
        compute='_compute_state', store=True, tracking=True,
    )

    # -- Restriction lines -------------------------------------------------
    menu_line_ids = fields.One2many('aam.rule.menu', 'rule_id', string='Menu Restrictions')
    model_line_ids = fields.One2many('aam.rule.model', 'rule_id', string='Model Restrictions')
    field_line_ids = fields.One2many('aam.rule.field', 'rule_id', string='Field Restrictions')
    button_line_ids = fields.One2many(
        'aam.rule.button', 'rule_id', string='Button & Tab Restrictions')
    search_line_ids = fields.One2many(
        'aam.rule.search', 'rule_id', string='Search Panel Restrictions')
    chatter_line_ids = fields.One2many(
        'aam.rule.chatter', 'rule_id', string='Chatter Restrictions')

    # -- Global (user-wide) toggles ---------------------------------------
    readonly_user = fields.Boolean(
        'Read-Only User', help="Block create, write and delete everywhere.")
    disable_developer_mode = fields.Boolean('Disable Developer Mode')
    disable_login = fields.Boolean('Disable Login', tracking=True)
    restrict_rpc = fields.Boolean(
        'Block XML-RPC / Scripts',
        help="Refuse non-interactive authentication. Rarely needed: enforced rules "
             "already apply to RPC calls.",
    )
    restrict_module_manage = fields.Boolean(
        'Block Install / Upgrade Apps',
        help="Prevent installing, upgrading or uninstalling any module.")

    hide_import = fields.Boolean('Hide Import')
    hide_export = fields.Boolean('Hide Export')
    hide_spreadsheet = fields.Boolean('Hide Insert in Spreadsheet')
    hide_print = fields.Boolean('Hide Print Menu')
    hide_action_button = fields.Boolean('Hide Action (cog) Menu')
    hide_add_property = fields.Boolean('Hide Add a Property')

    hide_chatter = fields.Boolean('Hide Whole Chatter')
    hide_send_message = fields.Boolean('Hide Send Message')
    hide_log_note = fields.Boolean('Hide Log Note')
    hide_activity = fields.Boolean('Hide Activities')
    hide_followers = fields.Boolean('Hide Followers')
    hide_attachments = fields.Boolean('Hide Attachments')

    hide_filter = fields.Boolean('Hide Filters')
    hide_group_by = fields.Boolean('Hide Group By')
    hide_custom_filter = fields.Boolean('Hide Custom Filter')
    hide_custom_group_by = fields.Boolean('Hide Custom Group By')
    hide_delete_filter = fields.Boolean('Hide Delete Saved Filter')
    hide_search_panel = fields.Boolean('Hide Search Panel')
    hide_favourite = fields.Boolean('Hide Favourites')

    # -- Computes ----------------------------------------------------------

    @api.depends('active', 'date_from', 'date_to')
    def _compute_state(self):
        now = fields.Datetime.now()
        for rule in self:
            if rule.date_to and rule.date_to < now:
                rule.state = 'expired'
            elif not rule.active or (rule.date_from and rule.date_from > now):
                rule.state = 'draft'
            else:
                rule.state = 'active'

    # -- Constraints -------------------------------------------------------

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rule in self:
            if rule.date_from and rule.date_to and rule.date_from >= rule.date_to:
                raise ValidationError(
                    _("Rule %s: 'Active From' must come before 'Active Until'.", rule.name))

    @api.constrains('target_type', 'user_ids', 'group_ids', 'profile_id')
    def _check_target(self):
        for rule in self:
            if rule.target_type == 'user' and not rule.user_ids:
                raise ValidationError(
                    _("Rule %s targets users but none are selected.", rule.name))
            if rule.target_type == 'group' and not rule.group_ids:
                raise ValidationError(
                    _("Rule %s targets groups but none are selected.", rule.name))
            if rule.target_type == 'profile' and not rule.profile_id:
                raise ValidationError(
                    _("Rule %s targets a profile but none is selected.", rule.name))

    @api.constrains('target_type', 'user_ids', 'group_ids', 'profile_id', 'active')
    def _check_admin_protection(self):
        """Refuse to restrict an administrator unless explicitly allowed.

        This is the rail that keeps a database recoverable. Without it a single
        careless rule targeting "Everyone" can lock every administrator out of
        Settings, and the only way back in is a shell session.
        """
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param(PARAM_ALLOW_RESTRICT_ADMIN) in ('1', 'True', 'true'):
            return
        for rule in self.filtered('active'):
            reached = rule._targeted_user_ids()
            if reached is None:  # 'Everyone' - necessarily includes administrators
                raise ValidationError(_(
                    "Rule %s targets Everyone, which would also restrict administrators.\n\n"
                    "Target specific users or groups instead. If you really mean to "
                    "restrict administrators, enable 'Allow Restricting Administrators' "
                    "in Settings > Access Management first.", rule.name))
            if set(PROTECTED_UIDS) & reached:
                raise ValidationError(_(
                    "Rule %s would restrict the administrator account, which risks locking "
                    "you out of this database.\n\nRemove the administrator from the target, "
                    "or enable 'Allow Restricting Administrators' in "
                    "Settings > Access Management.", rule.name))
            admins = self.env['res.users'].sudo().browse(sorted(reached)).filtered(
                lambda u: u._is_system())
            if admins:
                raise ValidationError(_(
                    "Rule %(rule)s would restrict the following Settings administrator(s): "
                    "%(users)s.\n\nRemove them from the target, or enable 'Allow Restricting "
                    "Administrators' in Settings > Access Management.",
                    rule=rule.name, users=', '.join(admins.mapped('name'))))

    # -- Targeting helpers -------------------------------------------------

    def _targeted_user_ids(self):
        """Return the set of user ids this rule reaches, or ``None`` for everyone."""
        self.ensure_one()
        if self.target_type == 'all':
            return None
        if self.target_type == 'user':
            return set(self.user_ids.ids)
        if self.target_type == 'group':
            groups = self.group_ids
            # `include_implied_groups` is inert on Odoo 18: the closure is
            # materialised into res_groups_users_rel, so a direct member and an
            # implied one are the same row and the distinction cannot be
            # recovered. The flag is kept (and shown read-only) so a rules JSON
            # exported from 19 still round-trips. The error direction is safe -
            # the rule reaches a superset, and _check_admin_protection computes
            # its blast radius from this same call, so the safety rail widens
            # with it. See models/aam_group_compat.py.
            return set(group_members(groups).ids)
        if self.target_type == 'profile':
            profile = self.profile_id
            return profile._effective_user_ids() if profile else set()
        return set()

    def _applies_to_user(self, user):
        """Cheap membership test used by the policy compiler."""
        self.ensure_one()
        reached = self._targeted_user_ids()
        return reached is None or user.id in reached

    # -- Cache invalidation ------------------------------------------------
    # Any write to a rule can change what any user sees, so the compiled policy
    # cache must go. 'groups' is the widest bucket and also drops the cached
    # view archs, which we need because our arch injection rides on top of them.

    def _invalidate_policy(self):
        self.env.registry.clear_cache('groups')
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        rules._invalidate_policy()
        return rules

    def write(self, vals):
        res = super().write(vals)
        self._invalidate_policy()
        return res

    def unlink(self):
        res = super().unlink()
        self._invalidate_policy()
        return res

    # -- Actions -----------------------------------------------------------

    def action_activate(self):
        self.write({'active': True})

    def action_deactivate(self):
        self.write({'active': False})

    def action_edit_in_wizard(self):
        """Re-open this rule in the guided setup wizard.

        Raises if the rule has grown past what the wizard can show - the check
        lives in `aam.rule.wizard._unsupported_reasons`, so the two definitions of
        "representable" can never drift apart.
        """
        self.ensure_one()
        return self.env['aam.rule.wizard'].action_open_for_rule(self)

    @api.model
    def _cron_revoke_expired(self):
        """Archive rules whose 'Active Until' has passed (features I9/I10)."""
        expired = self.search([
            ('active', '=', True),
            ('auto_revoke', '=', True),
            ('date_to', '!=', False),
            ('date_to', '<', fields.Datetime.now()),
        ])
        if expired:
            expired.write({'active': False})
        return len(expired)


def _assert_global_flags_exist():
    """Keep GLOBAL_FLAGS and the actual fields on aam.rule from drifting apart."""
    declared = set(GLOBAL_FLAGS)
    missing = declared - set(AamRule.__dict__)
    if missing:  # pragma: no cover - developer error, surfaces at import time
        raise AssertionError(
            "GLOBAL_FLAGS names with no matching field on aam.rule: %s" % sorted(missing))


_assert_global_flags_exist()
