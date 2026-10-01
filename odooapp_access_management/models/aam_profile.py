from odoo import _, api, fields, models
from .aam_group_compat import group_members



class AamProfile(models.Model):
    """A reusable, named bundle of access rules.

    Assign a profile to users and/or groups instead of rebuilding the same
    restrictions per person. Blocking a profile (``active = False``) instantly
    lifts every rule it owns without deleting anything, which is the usual way
    to grant temporary elevated access.
    """

    _name = 'aam.profile'
    _description = 'Access Profile'
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    description = fields.Text(translate=True)

    user_ids = fields.Many2many(
        'res.users', 'aam_profile_users_rel', 'profile_id', 'user_id',
        string='Users', tracking=True,
        help="Users this profile applies to.",
    )
    group_ids = fields.Many2many(
        'res.groups', 'aam_profile_groups_rel', 'profile_id', 'group_id',
        string='Groups', tracking=True,
        help="Every user in these groups gets this profile.",
    )
    company_ids = fields.Many2many(
        'res.company', 'aam_profile_company_rel', 'profile_id', 'company_id',
        string='Companies',
        help="Restrict this profile to these companies. Empty means all companies.",
    )

    rule_ids = fields.One2many('aam.rule', 'profile_id', string='Rules')

    date_start = fields.Datetime(
        'Active From', tracking=True,
        help="Before this moment the profile has no effect. Empty means immediately.",
    )
    date_end = fields.Datetime(
        'Active Until', tracking=True,
        help="After this moment the profile has no effect. Empty means never expires.",
    )

    rule_count = fields.Integer(compute='_compute_rule_count')
    user_count = fields.Integer(compute='_compute_user_count')

    @api.depends('rule_ids')
    def _compute_rule_count(self):
        counts = dict(self.env['aam.rule']._read_group(
            [('profile_id', 'in', self.ids)],
            groupby=['profile_id'],
            aggregates=['__count'],
        ))
        for profile in self:
            profile.rule_count = counts.get(profile, 0)

    @api.depends('user_ids', 'group_ids.users')
    def _compute_user_count(self):
        for profile in self:
            profile.user_count = len(profile._effective_user_ids())

    def _effective_user_ids(self):
        """Return the set of user ids this profile reaches, groups expanded.

        ``group_members`` already accounts for implied groups, so a profile
        attached to "Sales / Administrator" also reaches everyone who merely
        implies it. On Odoo 18 that closure is materialised into
        ``res_groups_users_rel``, which is why the ``@api.depends`` above can
        watch ``group_ids.users`` directly - see [[aam_group_compat]].
        """
        self.ensure_one()
        return set(self.user_ids.ids) | set(group_members(self.group_ids).ids)

    # -- Cache invalidation ------------------------------------------------
    # Blocking a profile lifts every rule it owns, and changing its members
    # changes who those rules reach - both invalidate the compiled policy just
    # as surely as editing a rule does.

    def _invalidate_policy(self):
        self.env.registry.clear_cache('groups')
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        profiles = super().create(vals_list)
        profiles._invalidate_policy()
        return profiles

    def write(self, vals):
        res = super().write(vals)
        self._invalidate_policy()
        return res

    def unlink(self):
        res = super().unlink()
        self._invalidate_policy()
        return res

    def action_block(self):
        """Temporarily lift every rule in this profile."""
        self.write({'active': False})

    def action_unblock(self):
        self.write({'active': True})

    def action_view_rules(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Rules of %s", self.name),
            'res_model': 'aam.rule',
            'view_mode': 'list,form',
            'domain': [('profile_id', '=', self.id)],
            'context': {'default_profile_id': self.id, 'default_target_type': 'profile'},
        }
