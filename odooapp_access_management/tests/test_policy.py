"""The policy compiler: targeting, merge semantics, caching, safety rails.

Test names carry the parity-matrix id from the design (I1, I3, ...) so coverage
is checkable against the plan rather than asserted.
"""

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import AamCommon


@tagged('post_install', '-at_install')
class TestPolicyTargeting(AamCommon):

    def test_i1_target_user(self):
        rule = self.Rule.create({
            'name': 'Direct', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True,
        })
        self.assertEqual(rule._targeted_user_ids(), {self.user.id})
        self.assertTrue(self.policy_for()['globals']['hide_export'])
        self.assertFalse(self.policy_for(self.other_user)['globals']['hide_export'])

    def test_i2_target_group_includes_implied(self):
        parent = self.env['res.groups'].create({
            'name': 'AAM Test Lead', 'implied_ids': [(6, 0, [self.crew.id])]})
        lead = self.env['res.users'].create({
            'name': 'Lead', 'login': 'aam_test_lead',
            'groups_id': [(6, 0, [self.internal_group.id, parent.id])]})

        rule = self.Rule.create({
            'name': 'By group', 'target_type': 'group',
            'group_ids': [(6, 0, [self.crew.id])], 'hide_export': True,
        })
        # The lead only *implies* the crew group, but that is what grants access,
        # so the rule must reach them too.
        self.assertIn(lead.id, rule._targeted_user_ids())
        self.assertTrue(self.policy_for(lead)['globals']['hide_export'])

        # `include_implied_groups` cannot narrow the audience on Odoo 18.
        # Membership is materialised into res_groups_users_rel by
        # GroupsImplied.write (base/models/res_users.py:1494-1514), so a user who
        # only implies the crew and one added to it directly are the same row and
        # the distinction is not recoverable. The field is kept and shown
        # read-only so a rule imported from Odoo 19 round-trips and explains
        # itself; asserted here rather than skipped, because a silently skipped
        # test hides a real semantic change. See models/aam_group_compat.py.
        rule.include_implied_groups = False
        self.assertIn(lead.id, rule._targeted_user_ids())
        self.assertTrue(self.policy_for(lead)['globals']['hide_export'])

    def test_i3_target_profile(self):
        profile = self.Profile.create({
            'name': 'Ops', 'group_ids': [(6, 0, [self.crew.id])]})
        self.Rule.create({
            'name': 'Via profile', 'target_type': 'profile',
            'profile_id': profile.id, 'hide_import': True,
        })
        self.assertTrue(self.policy_for()['globals']['hide_import'])

    def test_i3_blocking_a_profile_lifts_its_rules(self):
        profile = self.Profile.create({
            'name': 'Ops', 'user_ids': [(6, 0, [self.user.id])]})
        self.Rule.create({
            'name': 'Via profile', 'target_type': 'profile',
            'profile_id': profile.id, 'hide_import': True,
        })
        self.assertTrue(self.policy_for()['globals']['hide_import'])

        profile.action_block()
        self.assertFalse(self.policy_for()['globals']['hide_import'])

        profile.action_unblock()
        self.assertTrue(self.policy_for()['globals']['hide_import'])

    def test_i5_company_scope(self):
        other = self.env['res.company'].create({'name': 'AAM Second Co'})
        self.user.write({'company_ids': [(4, other.id)]})
        self.Rule.create({
            'name': 'Other company only', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'company_ids': [(6, 0, [other.id])], 'hide_export': True,
        })
        self.assertFalse(self.policy_for()['globals']['hide_export'])

        policy = self.Policy.with_user(self.user).with_company(other).get_policy()
        self.assertTrue(policy['globals']['hide_export'])


@tagged('post_install', '-at_install')
class TestPolicyMerge(AamCommon):

    def test_deny_wins_across_rules(self):
        """A permissive rule can never undo a restrictive one."""
        self.Rule.create({
            'name': 'Restrictive', 'target_type': 'user', 'priority': 1,
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})],
        })
        self.Rule.create({
            'name': 'Permissive and higher priority', 'target_type': 'user',
            'priority': 99, 'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': False})],
        })
        entry = self.policy_for()['models']['res.partner']
        self.assertIn('unlink', entry['blocked'],
                      "priority must not turn a denial back into a permission")

    def test_c14_highest_priority_mask_wins(self):
        for priority, mask_type in ((20, 'full'), (5, 'partial')):
            self.Rule.create({'name': 'Mask %s' % priority, 'priority': priority,
                              'target_type': 'user', 'user_ids': [(6, 0, [self.user.id])],
                              'field_line_ids': [(0, 0, {
                                  'model_id': self.partner_model.id,
                                  'field_id': self.field_id('res.partner', 'phone'),
                                  'mask_type': mask_type})]})
        mask = self.policy_for()['fields']['res.partner']['phone']['mask']
        self.assertEqual(mask['type'], 'full')

    def test_domains_accumulate(self):
        for name, domain in (('A', "[('is_company', '=', True)]"),
                             ('B', "[('active', '=', True)]")):
            self.Rule.create({
                'name': name, 'target_type': 'user',
                'user_ids': [(6, 0, [self.user.id])],
                'model_line_ids': [(0, 0, {
                    'model_id': self.partner_model.id, 'domain': domain,
                    'domain_on_read': True})],
            })
        clauses = self.policy_for()['models']['res.partner']['domains']['read']
        self.assertEqual(len(clauses), 2, "both domains must survive the merge")

    def test_a1_menu_children_expand(self):
        settings = self.env.ref('base.menu_administration')
        self.Rule.create({
            'name': 'Hide settings', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'menu_line_ids': [(0, 0, {'menu_id': settings.id, 'include_children': True})],
        })
        hidden = self.policy_for()['menus']
        children = self.env['ir.ui.menu'].search([('id', 'child_of', settings.id)])
        self.assertTrue(set(children.ids) <= set(hidden))

    def test_a1_menu_without_children(self):
        settings = self.env.ref('base.menu_administration')
        child = self.env['ir.ui.menu'].search([('parent_id', '=', settings.id)], limit=1)
        self.Rule.create({
            'name': 'Hide settings only', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'menu_line_ids': [(0, 0, {'menu_id': settings.id, 'include_children': False})],
        })
        hidden = self.policy_for()['menus']
        self.assertIn(settings.id, hidden)
        if child:
            self.assertNotIn(child.id, hidden)


@tagged('post_install', '-at_install')
class TestPolicyCache(AamCommon):

    def test_l6_cache_returns_same_object(self):
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        first = self.Policy.with_user(self.user).get_policy()
        second = self.Policy.with_user(self.user).get_policy()
        self.assertIs(first, second, "a second call must hit the registry cache")

    def test_l6_cache_drops_on_rule_write(self):
        rule = self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        first = self.Policy.with_user(self.user).get_policy()
        rule.write({'hide_import': True})
        second = self.Policy.with_user(self.user).get_policy()
        self.assertIsNot(first, second)
        self.assertTrue(second['globals']['hide_import'])

    def test_l6_cache_drops_on_line_write(self):
        rule = self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})]})
        self.Policy.with_user(self.user).get_policy()
        rule.model_line_ids.write({'no_create': True})
        entry = self.Policy.with_user(self.user).get_policy()['models']['res.partner']
        self.assertIn('create', entry['blocked'])

    def test_policy_is_frozen(self):
        """The cached object is shared, so it must refuse mutation."""
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        policy = self.Policy.with_user(self.user).get_policy()
        self.assertIsInstance(policy['menus'], frozenset)
        with self.assertRaises(AttributeError):
            policy['menus'].add(1)

    def test_hot_path_reads_no_parameter_and_checks_no_group(self):
        """get_policy runs for every field of every record a user reads - some
        1,400 times for one 80-row list page of 17 columns. Each call used to
        read two system parameters and check the administrator group *before*
        reaching the cache, which made that read ~4x slower for every user,
        including users no rule applies to and administrators.

        Those inputs only change through writes that already clear the registry
        cache, so once compiled, a repeat call must touch neither.
        """
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        admin = self.env.ref('base.user_admin')
        users = (self.user, self.other_user, admin)
        for user in users:
            self.policy_for(user)  # compile once

        seen = []
        Param = type(self.env['ir.config_parameter'])
        Users = type(self.env['res.users'])
        real_param, real_group = Param.get_param, Users._has_group

        def spy_param(rec, key, default=False):
            seen.append(key)
            return real_param(rec, key, default)

        def spy_group(rec, group_ext_id):
            seen.append(group_ext_id)
            return real_group(rec, group_ext_id)

        with patch.object(Param, 'get_param', spy_param), \
                patch.object(Users, '_has_group', spy_group):
            for _ in range(20):
                for user in users:
                    self.Policy.with_user(user).get_policy()
        self.assertEqual(seen, [], "a repeat call must be a cache hit")

    def test_serialising_touches_no_parameter_and_no_group(self):
        """_read_format, name_search and _poll now run on every serialisation; for a
        user no rule reaches, and for a masked one, a repeat call must be cache hits."""
        self.mask_rule('res.partner', 'phone')
        ids = (self.company_partner | self.person_partner).ids
        for user in (self.user, self.other_user):
            self.env['res.partner'].with_user(user).browse(ids).read(['phone', 'name'])

        seen = []
        Param = type(self.env['ir.config_parameter'])
        Users = type(self.env['res.users'])
        real_param, real_group = Param.get_param, Users._has_group

        def spy_param(rec, key, default=False):
            seen.append(key)
            return real_param(rec, key, default)

        # Core itself checks the groups a field names (accounting puts some on
        # contacts, Discuss names the administrators' group) whenever it reads
        # the model. Those are not ours to avoid - so the administrator rail,
        # which asks for that same group, is watched by itself.
        named_by_fields = {
            group.strip().lstrip('!')
            for field in self.env['res.partner']._fields.values() if field.groups
            for group in field.groups.split(',')}
        Policy = type(self.env['aam.policy'])
        real_rail = Policy._is_protected

        def spy_group(rec, group_ext_id):
            if group_ext_id not in named_by_fields:
                seen.append(group_ext_id)
            return real_group(rec, group_ext_id)

        def spy_rail(policy, user):
            seen.append('the administrator rail')
            return real_rail(policy, user)

        with patch.object(Param, 'get_param', spy_param), \
                patch.object(Users, '_has_group', spy_group), \
                patch.object(Policy, '_is_protected', spy_rail):
            for _ in range(10):
                for user in (self.user, self.other_user):
                    records = self.env['res.partner'].with_user(user).browse(ids)
                    records.read(['phone', 'name'])
                    records.sudo()._read_format(['phone'])
                    self.env['res.partner'].with_user(user).name_search('AAM')
        self.assertEqual(seen, [], "serialisation must stay on the policy cache")

    def test_the_policy_of_the_uid_can_be_asked_for_under_sudo(self):
        """get_policy stands down under sudo(). A module that redacts values read
        under sudo() for the current user asks `_policy_parts_for_uid` instead."""
        self.mask_rule('res.partner', 'phone')
        Policy = self.as_user()['aam.policy'].sudo()
        self.assertFalse(Policy.get_policy()['fields'])
        static, active = Policy._policy_parts_for_uid()
        self.assertIn('res.partner', Policy._compose_policy(static, active)['fields'])
        self.assertFalse(self.env['aam.policy']._compose_policy(
            *self.env['aam.policy']._policy_parts_for_uid())['fields'], "never the superuser")

    def test_users_do_not_share_a_policy(self):
        self.Rule.create({
            'name': 'Only me', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        self.assertTrue(self.policy_for(self.user)['globals']['hide_export'])
        self.assertFalse(self.policy_for(self.other_user)['globals']['hide_export'])


@tagged('post_install', '-at_install')
class TestClientPolicyVersion(AamCommon):
    """The fingerprint the browser uses to decide its cached views are stale.

    The web client keeps `get_views` archs in IndexedDB and Odoo only drops that
    cache when `ir.ui.view` or `ir.filters` is written. Assigning a profile
    writes neither, so without this fingerprint the browser kept rendering the
    pre-restriction arch after a full reload while the server was already
    returning the restricted one - observed on Odoo 19 Enterprise, with
    `list_price` gone from `get_views` and still on screen.
    """

    def _version(self, user):
        return self.Policy.with_user(user).get_client_policy()['version']

    def test_client_policy_carries_a_version(self):
        version = self._version(self.user)
        self.assertTrue(version)
        self.assertEqual(len(version), 16)

    def test_version_is_stable_while_nothing_changes(self):
        """It must not churn, or every boot would throw the cache away."""
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        self.assertEqual(self._version(self.user), self._version(self.user))

    def test_version_moves_when_a_rule_changes(self):
        rule = self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        before = self._version(self.user)
        rule.write({'hide_import': True})
        self.assertNotEqual(before, self._version(self.user))

    def test_version_moves_when_a_profile_is_assigned(self):
        """The case that exposed this: assigning a profile writes no view."""
        profile = self.Profile.create({'name': 'Late Assignment'})
        self.Rule.create({
            'name': 'Profile rule', 'target_type': 'profile',
            'profile_id': profile.id,
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})]})
        before = self._version(self.user)
        profile.write({'user_ids': [(4, self.user.id)]})
        self.assertNotEqual(before, self._version(self.user))

    def test_versions_differ_between_users(self):
        self.Rule.create({
            'name': 'Only me', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        self.assertNotEqual(self._version(self.user), self._version(self.other_user))


@tagged('post_install', '-at_install')
class TestSafetyRails(AamCommon):

    def test_l7_cannot_target_everyone(self):
        with self.assertRaises(ValidationError):
            self.Rule.create({'name': 'All', 'target_type': 'all', 'readonly_user': True})

    def test_l7_cannot_target_an_administrator(self):
        admin = self.env.ref('base.user_admin')
        with self.assertRaises(ValidationError):
            self.Rule.create({
                'name': 'Admin', 'target_type': 'user',
                'user_ids': [(6, 0, [admin.id])], 'readonly_user': True})

    def test_l7_administrators_are_never_restricted(self):
        """Even a rule that reaches an admin through a group must not bite."""
        admin = self.env.ref('base.user_admin')
        self.env['ir.config_parameter'].sudo().set_param('aam.allow_restrict_admin', '1')
        rule = self.Rule.create({
            'name': 'Everyone', 'target_type': 'all', 'hide_export': True})
        self.env['ir.config_parameter'].sudo().set_param('aam.allow_restrict_admin', '0')
        self.env.registry.clear_cache()

        self.assertTrue(rule._applies_to_user(admin))
        self.assertFalse(self.policy_for(admin)['globals']['hide_export'],
                         "the rail must hold even for a rule created while it was off")

    def test_l7_kill_switch(self):
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        self.assertTrue(self.policy_for()['globals']['hide_export'])

        self.env['ir.config_parameter'].sudo().set_param('aam.enabled', '0')
        self.env.registry.clear_cache()
        self.assertFalse(self.policy_for()['globals']['hide_export'])

    def test_l7_kill_switch_needs_no_manual_cache_clear(self):
        """The kill switch is decided behind the policy cache, so it relies on
        set_param clearing that cache (Odoo clears 'stable', which cascades to
        'default'). test_l7_kill_switch clears the cache by hand, so it would
        pass even if nothing else did."""
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        self.assertTrue(self.policy_for()['globals']['hide_export'])

        self.env['ir.config_parameter'].sudo().set_param('aam.enabled', '0')
        self.assertFalse(self.policy_for()['globals']['hide_export'])

    def test_l7_promotion_to_administrator_lifts_restrictions_at_once(self):
        """The administrator rail is decided behind the cache too. Adding the
        user from the group's own member list is the path that bypasses the
        user form; it must still take effect without a restart."""
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        self.assertTrue(self.policy_for()['globals']['hide_export'])

        # Odoo 18 names a group's members `users` (19: `user_ids`).
        self.env.ref('base.group_system').write({'users': [(4, self.user.id)]})
        self.assertFalse(self.policy_for()['globals']['hide_export'],
                         "a new administrator must never stay restricted")

    def test_superuser_is_unrestricted(self):
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        self.assertFalse(self.Policy.get_policy()['globals']['hide_export'])

    def test_missing_user_yields_an_empty_policy(self):
        """A degenerate environment must restrict nothing rather than crash."""
        empty = self.env['res.users'].browse()
        self.assertTrue(self.Policy._is_protected(empty))


@tagged('post_install', '-at_install')
class TestRuleValidation(AamCommon):

    def test_dates_must_be_ordered(self):
        with self.assertRaises(ValidationError):
            self.Rule.create({
                'name': 'Bad dates', 'target_type': 'user',
                'user_ids': [(6, 0, [self.user.id])],
                'date_from': '2026-06-01 00:00:00', 'date_to': '2026-01-01 00:00:00'})

    def test_target_must_be_populated(self):
        with self.assertRaises(ValidationError):
            self.Rule.create({'name': 'No users', 'target_type': 'user'})

    def test_c_field_cannot_be_invisible_and_required(self):
        with self.assertRaises(ValidationError):
            self.Rule.create({
                'name': 'Contradictory', 'target_type': 'user',
                'user_ids': [(6, 0, [self.user.id])],
                'field_line_ids': [(0, 0, {
                    'model_id': self.partner_model.id,
                    'field_id': self.field_id('res.partner', 'phone'),
                    'invisible': True, 'required': True})]})

    def test_d_domain_must_parse(self):
        with self.assertRaises(ValidationError):
            self.Rule.create({
                'name': 'Bad domain', 'target_type': 'user',
                'user_ids': [(6, 0, [self.user.id])],
                'model_line_ids': [(0, 0, {
                    'model_id': self.partner_model.id, 'domain': "not a domain ("})]})

    def test_i9_expired_rules_are_revoked_by_cron(self):
        rule = self.Rule.create({
            'name': 'Short lived', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'date_to': '2020-01-01 00:00:00', 'auto_revoke': True, 'hide_export': True})
        self.assertEqual(rule.state, 'expired')
        self.Rule._cron_revoke_expired()
        self.assertFalse(rule.active)


@tagged('post_install', '-at_install')
class TestSqlConstraints(AamCommon):
    """All seven uniqueness constraints reach the database with their message.

    Odoo 19 declares these as `models.Constraint`; Odoo 18 has no such class and
    they are `_sql_constraints` tuples here. Both produce the *same* database
    constraint name - v19 strips one leading underscore from the attribute
    (`orm/table_objects.py:46`), v18 joins table and key (`models.py:3512`), and
    both give e.g. `aam_rule_field_field_uniq` - and that name is how
    `service/model.py:_as_validation_error` finds the friendly message again when
    Postgres raises.

    Asserted through `ir.model.constraint` rather than by provoking a real
    violation: the IntegrityError is only converted at the dispatch layer, so in
    a unit test a duplicate raises raw psycopg2 and aborts the cursor. What
    matters here is that the conversion pass kept every key and every message,
    and this checks exactly that. A mistyped key would land as a constraint with
    no message and degrade at runtime to an unreadable database error.
    """

    EXPECTED = {
        'aam_preset_key_uniq': 'Each catalogue entry may only appear once.',
        'aam_rule_button_element_uniq': 'This element is already restricted by this rule.',
        'aam_rule_chatter_chatter_uniq': 'This model already has a chatter restriction in this rule.',
        'aam_rule_field_field_uniq': 'This field is already restricted by this rule. Edit the existing line instead.',
        'aam_rule_menu_menu_uniq': 'This menu is already restricted by this rule.',
        'aam_rule_model_model_uniq': 'This model is already restricted by this rule. Edit the existing line instead.',
        'aam_rule_search_search_uniq': 'This model already has a search restriction in this rule.',
    }

    def test_every_uniqueness_constraint_is_registered_with_its_message(self):
        rows = self.env['ir.model.constraint'].sudo().search([
            ('module.name', '=', 'odooapp_access_management'),
            ('type', '=', 'u'),
        ])
        found = {row.name: row.message for row in rows}
        for name, message in self.EXPECTED.items():
            self.assertIn(name, found,
                          "%s is missing - a renamed or mistyped _sql_constraints key" % name)
            self.assertEqual(found[name], message,
                             "%s lost its message, so a violation would surface as a "
                             "raw database error" % name)


@tagged('post_install', '-at_install')
class TestTimeWindowCache(AamCommon):
    """A time window opening or closing writes nothing, so it clears no cache.

    Record rules (``ir.rule._compute_domain``) and model access
    (``ir.model.access._get_allowed_models``) are both ormcached until a rule
    changes. The time-windowed rules active right now are therefore part of both
    cache keys (``aam.policy._access_fingerprint``). Without that, whichever
    answer was computed first was served until something unrelated cleared the
    cache: a window that opened never applied, one that closed kept applying.
    """

    def _windowed_rule(self, line):
        rule = self.Rule.create({
            'name': 'Windowed', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, dict(line, model_id=self.partner_model.id))],
        })
        self.env['aam.time.window'].create({'rule_id': rule.id})
        self.as_user()
        return rule

    def _at(self, window_open):
        """Patch the clock's verdict; nothing is written or invalidated."""
        Window = type(self.env['aam.time.window'])
        return patch.object(Window, '_matches', return_value=window_open)

    def test_n1_windowed_model_block_follows_the_clock(self):
        self._windowed_rule({'no_read': True})
        Partner = self.env(user=self.user)['res.partner']
        with self._at(False):
            self.assertTrue(Partner.has_access('read'), "window closed: not blocked")
        with self._at(True):
            self.assertFalse(Partner.has_access('read'), "window open: blocked")
        with self._at(False):
            self.assertTrue(Partner.has_access('read'), "and released again")

    def test_n1_windowed_record_domain_follows_the_clock(self):
        self._windowed_rule({
            'domain': "[('is_company', '=', True)]", 'domain_on_read': True})
        Partner = self.env(user=self.user)['res.partner']
        person = [('id', '=', self.person_partner.id)]
        with self._at(False):
            self.assertTrue(Partner.search(person), "window closed: visible")
        with self._at(True):
            self.assertFalse(Partner.search(person), "window open: filtered out")
        with self._at(False):
            self.assertTrue(Partner.search(person), "and visible again")

    def test_n1_fingerprint_is_empty_without_time_windows(self):
        """The common case must not fragment the cache: no windows, empty key part."""
        self.Rule.create({
            'name': 'Plain rule', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True})
        env = self.as_user()
        self.assertEqual(env['aam.policy']._access_fingerprint(), ())
