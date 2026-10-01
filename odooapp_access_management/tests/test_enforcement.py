"""Enforcement: restrictions must hold on the server, not just in the browser.

The point of these tests is the distinction this module is built on. Competing
modules apply field and model rules at ``fields_get`` and view-arch level, so a
user calling ``read`` over XML-RPC gets everything back. Asserting through
``read()`` and ``search()`` - the same entry points RPC uses - is what proves
the difference.
"""

from unittest.mock import patch

from lxml import etree

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.http import root
from odoo.tests import tagged

from .common import AamCommon


@tagged('post_install', '-at_install')
class TestModelEnforcement(AamCommon):

    def test_b1_blocked_crud_raises(self):
        self.Rule.create({
            'name': 'No delete', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})],
        })
        env = self.as_user()
        self.assertFalse(env['res.partner'].has_access('unlink'))
        self.assertTrue(env['res.partner'].has_access('read'))
        with self.assertRaises(AccessError):
            env['res.partner'].browse(self.company_partner.id).unlink()

    def test_b2_readonly_model_blocks_all_writes(self):
        self.Rule.create({
            'name': 'Read only partners', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'readonly_model': True})],
        })
        env = self.as_user()
        self.assertTrue(env['res.partner'].has_access('read'))
        for mode in ('create', 'write', 'unlink'):
            self.assertFalse(env['res.partner'].has_access(mode), mode)

    def test_h1_readonly_user_blocks_everything(self):
        self.Rule.create({
            'name': 'Read only user', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'readonly_user': True,
        })
        env = self.as_user()
        for mode in ('create', 'write', 'unlink'):
            self.assertFalse(env['res.partner'].has_access(mode), mode)
        self.assertTrue(env['res.partner'].has_access('read'))


@tagged('post_install', '-at_install')
class TestRecordEnforcement(AamCommon):

    def _restrict_to_companies(self, **extra):
        values = {
            'model_id': self.partner_model.id,
            'domain': "[('is_company', '=', True)]",
            'domain_on_read': True,
        }
        values.update(extra)
        return self.Rule.create({
            'name': 'Companies only', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, values)],
        })

    def test_d1_domain_filters_search(self):
        self._restrict_to_companies()
        env = self.as_user()
        found = env['res.partner'].search(
            [('id', 'in', [self.company_partner.id, self.person_partner.id])])
        self.assertEqual(found.ids, [self.company_partner.id])

    def test_d4_soft_restrict_filters_lists_but_allows_direct_access(self):
        """The whole point of a soft restriction.

        A hard restriction on Contacts blanks the customer on every order it is
        referenced from. Soft keeps the record reachable while still keeping it
        out of lists.
        """
        rule = self._restrict_to_companies(soft_restrict=True)
        env = self.as_user()

        self.assertEqual(
            env['res.partner'].search(
                [('id', 'in', [self.company_partner.id, self.person_partner.id])]).ids,
            [self.company_partner.id],
            "a soft restriction should still filter lists")
        self.assertTrue(
            env['res.partner'].browse(self.person_partner.id).has_access('read'),
            "a soft restriction should leave the record reachable directly")

        rule.model_line_ids.write({'soft_restrict': False})
        env = self.as_user()
        self.assertFalse(
            env['res.partner'].browse(self.person_partner.id).has_access('read'),
            "a hard restriction should deny direct access too")

    def test_d4_skip_soft_flag_from_a_client_is_ignored(self):
        """The context is the caller's (call_kw). A client sending aam_skip_soft must not
        lift a soft restriction off its searches."""
        self._restrict_to_companies(soft_restrict=True)
        env = self.as_user()
        found = env['res.partner'].with_context(aam_skip_soft=True).search(
            [('id', 'in', [self.company_partner.id, self.person_partner.id])])
        self.assertEqual(found.ids, [self.company_partner.id])

    def test_d1_domain_modes_are_independent(self):
        self._restrict_to_companies(domain_on_read=False, domain_on_write=True)
        env = self.as_user()
        self.assertEqual(
            len(env['res.partner'].search(
                [('id', 'in', [self.company_partner.id, self.person_partner.id])])),
            2, "a write-only domain must not filter reads")


@tagged('post_install', '-at_install')
class TestFieldEnforcement(AamCommon):

    def test_c1_invisible_field_is_removed_from_fields_get(self):
        self.Rule.create({
            'name': 'Hide comment', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'comment'),
                'invisible': True})],
        })
        env = self.as_user()
        self.assertNotIn('comment', env['res.partner'].fields_get())
        self.assertIn('name', env['res.partner'].fields_get())

    def test_c1_invisible_field_is_stripped_from_read(self):
        """``fields_get`` hiding it is not enough - the value must not ship."""
        self.Rule.create({
            'name': 'Hide comment', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'comment'),
                'invisible': True})],
        })
        env = self.as_user()
        partner = env['res.partner'].browse(self.company_partner.id)
        values = partner.read(['comment', 'name'])[0]
        self.assertNotIn('comment', values)
        self.assertIn('name', values)

    def test_c1_hidden_field_does_not_break_a_compute_that_reads_it(self):
        """The bug that took a whole form down.

        Denying ``read`` in ``_has_field_access`` makes ``Field.__get__`` raise,
        and ``__get__`` is what *core computes* use internally. Hiding
        ``list_price`` made ``account``'s ``_compute_tax_string`` raise
        ``AccessError``, so ``web_read`` failed and the product form would not
        open at all for the restricted user - a far worse outcome than showing
        the price. Reproduced here on ``res.partner`` so it runs on any
        database: ``complete_name`` is computed from ``name``.
        """
        self.Rule.create({
            'name': 'Hide name', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'name'),
                'invisible': True})],
        })
        # Force the dependent compute to run inside the restricted env.
        self.company_partner.invalidate_recordset()
        env = self.as_user()
        partner = env['res.partner'].browse(self.company_partner.id)

        values = partner.read(['complete_name'])[0]
        self.assertEqual(values['complete_name'], self.company_partner.complete_name)
        self.assertNotIn('name', values)
        # And the raw attribute read the ORM itself performs must not raise.
        self.assertTrue(partner.name)

    def test_c1_hidden_field_asked_for_over_rpc_is_simply_absent(self):
        """A caller may ask; it just does not get an answer - or a traceback.

        ``web_read`` indexes its result for every relational entry in the
        specification, so a value stripped by ``read`` alone would come back as
        a ``KeyError`` and a 500 instead of a clean omission.
        """
        self.Rule.create({
            'name': 'Hide parent', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'parent_id'),
                'invisible': True})],
        })
        env = self.as_user()
        partner = env['res.partner'].browse(self.person_partner.id)
        values = partner.web_read({'parent_id': {'fields': {'display_name': {}}},
                                   'name': {}})[0]
        self.assertNotIn('parent_id', values)
        self.assertIn('name', values)

    def test_c1_hidden_field_still_refuses_writes(self):
        self.Rule.create({
            'name': 'Hide comment', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'comment'),
                'invisible': True})],
        })
        env = self.as_user()
        partner = env['res.partner'].browse(self.company_partner.id)
        self.assertFalse(
            partner._has_field_access(partner._fields['comment'], 'write'))

    def test_c2_readonly_field_is_marked_readonly(self):
        self.Rule.create({
            'name': 'Freeze website', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'website'),
                'readonly': True})],
        })
        env = self.as_user()
        self.assertTrue(env['res.partner'].fields_get()['website']['readonly'])

    def test_c14_masking_applies_through_read(self):
        """``read`` is the RPC path, so masking here is masking everywhere."""
        self.Rule.create({
            'name': 'Mask phone', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'phone'),
                'mask_type': 'phone', 'mask_keep': 4})],
        })
        env = self.as_user()
        masked = env['res.partner'].browse(self.company_partner.id).read(['phone'])[0]
        self.assertNotEqual(masked['phone'], self.company_partner.phone)
        self.assertTrue(masked['phone'].endswith('3210'),
                        "the last four digits stay readable")
        self.assertEqual(
            self.env['res.partner'].browse(self.company_partner.id).phone,
            '+91 98765 43210',
            "an unrestricted user still sees the real value")

    def test_c14_masking_applies_through_web_read(self):
        self.Rule.create({
            'name': 'Mask email', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'email'),
                'mask_type': 'email'})],
        })
        env = self.as_user()
        values = env['res.partner'].browse(self.company_partner.id).web_read({'email': {}})[0]
        self.assertNotEqual(values['email'], 'alpha@example.com')
        self.assertTrue(values['email'].endswith('@example.com'),
                        "the domain stays visible; the local part does not")

    def test_c14_masking_applies_through_search_read(self):
        """Odoo 19 search_read never calls read() - it went out in full over RPC."""
        self.mask_rule('res.partner', 'phone')
        env = self.as_user()
        rows = env['res.partner'].search_read([('id', '=', self.company_partner.id)], ['phone'])
        self.assertEqual(rows[0]['phone'], '+** ***** *3210')

    def test_c1_hidden_field_is_stripped_from_search_read(self):
        self.Rule.create({
            'name': 'Hide comment', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'comment'),
                'invisible': True})],
        })
        env = self.as_user()
        rows = env['res.partner'].search_read(
            [('id', '=', self.company_partner.id)], ['comment', 'name'])
        self.assertNotIn('comment', rows[0])
        self.assertIn('name', rows[0])

    def test_c14_attribute_access_and_raw_context_see_the_real_value(self):
        """Business code (SMS, WhatsApp sends) reads record.phone - never masked."""
        self.mask_rule('res.partner', 'phone')
        env = self.as_user()
        partner = env['res.partner'].browse(self.company_partner.id)
        self.assertEqual(partner.phone, '+91 98765 43210')
        raw = partner.sudo().with_context(aam_raw_values=True).read(['phone'])[0]['phone']
        self.assertEqual(raw, '+91 98765 43210')

    def test_c14_superuser_and_unrestricted_users_see_the_real_value(self):
        self.mask_rule('res.partner', 'phone')
        self.assertEqual(
            self.env['res.partner'].browse(self.company_partner.id).read(['phone'])[0]['phone'],
            '+91 98765 43210')
        other = self.as_user(self.other_user)
        self.assertEqual(
            other['res.partner'].sudo().browse(self.company_partner.id)._read_format(['phone'])[0]['phone'],
            '+91 98765 43210')

    def test_c14_each_masked_value_goes_through_one_hook(self):
        """`_aam_mask_value` is the single place a value is redacted, so another
        module can decide per value."""
        self.mask_rule('res.partner', 'phone')
        Base = type(self.env['base'])
        seen = []

        def spy(records, name, value, spec):
            seen.append((records._name, name, spec['type']))
            return 'X'

        with patch.object(Base, '_aam_mask_value', spy):
            values = self.as_user()['res.partner'].browse(self.company_partner.id).read(['phone'])[0]
        self.assertEqual(values['phone'], 'X')
        self.assertEqual(seen, [('res.partner', 'phone', 'phone')])

    def test_c14_a_module_may_redact_under_sudo_without_hiding(self):
        """`_aam_serialising` says whether values are redacted and `_aam_output_policy`
        with which policy. Under sudo() nothing is stripped: internal callers index
        the keys they asked for."""
        rule = self.mask_rule('res.partner', 'phone')
        rule.write({'field_line_ids': [(0, 0, {
            'model_id': self.partner_model.id,
            'field_id': self.field_id('res.partner', 'comment'),
            'invisible': True})]})
        env = self.as_user()
        policy = env['aam.policy'].get_policy()
        Base = type(self.env['base'])
        partner = env['res.partner'].sudo().browse(self.company_partner.id)
        with patch.object(Base, '_aam_serialising', lambda records: True), \
                patch.object(Base, '_aam_output_policy', lambda records: policy):
            values = partner._read_format(['phone', 'comment'])[0]
        self.assertEqual(values['phone'], '+** ***** *3210')
        self.assertIn('comment', values)

    def test_c14_a_module_may_mask_further_keys(self):
        """`_aam_value_masks` decides which keys of the payload are redacted."""
        self.mask_rule('res.partner', 'name', 'full')
        Base = type(self.env['base'])
        real = Base._aam_value_masks

        def with_display_name(records, entries):
            masks = real(records, entries)
            if 'name' in masks:
                masks['display_name'] = masks['name']
            return masks

        with patch.object(Base, '_aam_value_masks', with_display_name):
            values = self.as_user()['res.partner'].browse(self.company_partner.id).read(
                ['display_name'])[0]
        self.assertEqual(values['display_name'], '*' * len('AAM Alpha Ltd'))

    def test_c14_empty_values_are_not_masked(self):
        """Masking an empty field would only advertise that something is hidden."""
        blank = self.env['res.partner'].create({'name': 'AAM Blank'})
        self.Rule.create({
            'name': 'Mask phone', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'phone'),
                'mask_type': 'full'})],
        })
        env = self.as_user()
        self.assertFalse(env['res.partner'].browse(blank.id).read(['phone'])[0]['phone'])


    # ------------------------------------------------------------------
    # Odoo 18 enforcement points that core does not provide
    #
    # v19 routes all three of these through its own `_has_field_access` hook.
    # v18 has no such hook, so `models/inherits/base_records.py` wires them by
    # hand - and a rename-only port would pass every other test in this file
    # while silently enforcing nothing on create and marking nothing readonly.
    # These are the tests that would catch that.
    # ------------------------------------------------------------------

    def _freeze(self, field='website'):
        """A rule that makes one res.partner field read-only for self.user."""
        return self.Rule.create({
            'name': 'Freeze %s' % field, 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', field),
                'readonly': True})],
        })

    def test_c2_create_with_a_frozen_field_is_refused(self):
        """v18's `create` performs no field-level check of its own.

        `models.py:4985` goes straight from `check_access('create')` to
        `_prepare_create_values`, so without our override a user could set a
        frozen field on a new record even though `write` refuses it.
        """
        self._freeze()
        env = self.as_user()
        with self.assertRaises(AccessError):
            env['res.partner'].create({'name': 'AAM New', 'website': 'http://x.test'})

    def test_c2_create_with_a_frozen_field_in_context_default_is_refused(self):
        """`default_*` is the other way a value reaches `create`."""
        self._freeze()
        env = self.as_user()
        with self.assertRaises(AccessError):
            env['res.partner'].with_context(
                default_website='http://x.test').create({'name': 'AAM New'})

    def test_c2_create_without_the_frozen_field_still_works(self):
        """The guard must not block ordinary creates - it runs on every model."""
        self._freeze()
        env = self.as_user()
        partner = env['res.partner'].create({'name': 'AAM Allowed'})
        self.assertTrue(partner.id)

    def test_c2_frozen_field_write_still_works_for_su(self):
        """The `env.su` exits are load-bearing: installation writes as superuser."""
        self._freeze()
        self.as_user()
        partner = self.env['res.partner'].browse(self.company_partner.id)
        partner.write({'website': 'http://su.test'})
        self.assertEqual(partner.website, 'http://su.test')

    def test_c1_hidden_field_is_absent_from_the_readable_field_list(self):
        """The v18-only read branch of `check_field_access_rights`.

        On v19, `read(fields=None)` derives its list from `fields_get`, which our
        override already filters. On v18 it derives it from
        `check_field_access_rights('read', None)` (`models.py:3856`), which knows
        nothing about the policy - so without our filter the hidden column is
        fetched from the database and only then stripped on the way out. Correct
        output, wasted I/O, and any hidden *computed* field evaluated for nothing.

        Asserted on the returned list rather than by calling `read()` with no
        arguments: on a database with `account` installed that pulls in every
        relational field on the partner, and the test user cannot read
        `account.move` - so the test would fail for a reason that has nothing to
        do with this module. `test_c1_invisible_field_is_stripped_from_read`
        already covers the end-to-end path with an explicit field list.
        """
        self.Rule.create({
            'name': 'Hide comment', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'comment'),
                'invisible': True})],
        })
        env = self.as_user()
        readable = env['res.partner'].check_field_access_rights('read', None)
        self.assertNotIn('comment', readable)
        self.assertIn('name', readable, "only the hidden field is dropped")

    def test_c1_an_explicit_read_of_a_hidden_field_is_not_denied(self):
        """Read is deliberately never *denied*, only stripped.

        Denying it breaks core computes that touch the field internally - the
        `list_price` / `_compute_tax_string` incident. So asking for the field by
        name must still succeed; the value simply does not come back.
        """
        self.Rule.create({
            'name': 'Hide comment', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'comment'),
                'invisible': True})],
        })
        env = self.as_user()
        self.assertEqual(
            env['res.partner'].check_field_access_rights('read', ['comment', 'name']),
            ['comment', 'name'],
            "naming the field explicitly must not raise")


@tagged('post_install', '-at_install')
class TestViewEnforcement(AamCommon):

    def test_c14_a_module_is_told_about_each_masked_field_node(self):
        self.mask_rule('res.partner', 'phone')
        Base = type(self.env['base'])
        seen = []

        def spy(records, node, name, entry, hidden):
            seen.append((node.tag, name, entry['mask']['type'], hidden))

        with patch.object(Base, '_aam_mask_node', spy):
            self.as_user()['res.partner'].get_view(view_type='form')
        self.assertIn(('field', 'phone', 'phone', False), seen)

    def test_c2_arch_gets_readonly_injected(self):
        self.Rule.create({
            'name': 'Freeze website', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'website'),
                'readonly': True})],
        })
        arch = self.as_user()['res.partner'].get_view(view_type='form')['arch']
        self.assertIn('website', arch)
        self.assertIn('readonly', arch)

    def test_c1_invisible_field_node_leaves_the_arch(self):
        """A field the policy removes must not be left in the arch.

        `_has_field_access` drops the field from `fields_get`, so a `<field>`
        node the client cannot resolve makes the whole view throw
        *"field is undefined"* - a blank screen, not a hidden field.
        """
        self.Rule.create({
            'name': 'Hide website', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'website'),
                'invisible': True})],
        })
        env = self.as_user()
        self.assertNotIn('website', env['res.partner'].fields_get())
        for view_type in ('form', 'list'):
            arch = env['res.partner'].get_view(view_type=view_type)['arch']
            self.assertNotIn('name="website"', arch,
                             "%s arch still names a field that no longer exists"
                             % view_type)

    def test_c8_conditionally_invisible_field_stays_in_the_arch(self):
        """The mirror case: a condition means the field still exists.

        Here the modifier has to be injected rather than the node removed -
        the client evaluates the condition per record.
        """
        self.Rule.create({
            'name': 'Hide website for companies', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'website'),
                'invisible': True, 'condition': 'is_company'})],
        })
        env = self.as_user()
        self.assertIn('website', env['res.partner'].fields_get())
        arch = env['res.partner'].get_view(view_type='form')['arch']
        self.assertIn('name="website"', arch)
        self.assertIn('is_company', arch)

    def test_e2_tab_is_removed_from_the_arch(self):
        self.Rule.create({
            'name': 'Hide notes tab', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'button_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'element_type': 'tab', 'element_name': 'internal_notes'})],
        })
        arch = self.as_user()['res.partner'].get_view(view_type='form')['arch']
        self.assertNotIn('name="internal_notes"', arch)

    def _c15_rule(self, **line):
        return self.Rule.create({
            'name': 'C15 category restriction', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, dict({
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'category_id'),
                'invisible': True}, **line))],
        })

    def _c15_add_searchpanel(self):
        """Give the partner search view a two-section left panel."""
        self.env['ir.ui.view'].create({
            'name': 'aam test searchpanel',
            'model': 'res.partner',
            'inherit_id': self.env.ref('base.view_res_partner_filter').id,
            'arch': '<xpath expr="/search" position="inside">'
                    '<searchpanel>'
                    '<field name="category_id" select="multi"/>'
                    '<field name="user_id"/>'
                    '</searchpanel></xpath>',
        })

    def test_c15_search_scope_drops_one_searchpanel_section_only(self):
        """Hide a left-panel section without hiding the field itself.

        A `<searchpanel>` section is a `<field>` in the search view, so the only
        way to drop one used to be making the field invisible - which removed
        it from the form too, and from `fields_get`, because an unscoped
        invisible means "this field does not exist for you". Scoped to the
        search view it must be arch-only: that section goes, the panel and its
        other sections stay, and every other view is untouched.
        """
        self._c15_add_searchpanel()
        self._c15_rule(view_mode='search')
        env = self.as_user()

        search = etree.fromstring(env['res.partner'].get_view(view_type='search')['arch'])
        panel = search.xpath('//searchpanel')
        self.assertTrue(panel, "the panel itself must survive")
        self.assertFalse(panel[0].xpath("field[@name='category_id']"),
                         "the restricted section should be gone")
        self.assertTrue(panel[0].xpath("field[@name='user_id']"),
                        "the other section must stay")

        self.assertIn('category_id', env['res.partner'].fields_get(),
                      "a view-scoped restriction must not remove the field from the ORM")
        form = etree.fromstring(env['res.partner'].get_view(view_type='form')['arch'])
        node = form.xpath("//field[@name='category_id']")
        self.assertTrue(node, "the form must still carry the field")
        self.assertNotIn('invisible', node[0].attrib,
                         "a search-only restriction must not touch the form")

    def test_c15_form_scope_hides_on_the_form_and_spares_search(self):
        self._c15_rule(view_mode='form')
        env = self.as_user()
        form = etree.fromstring(env['res.partner'].get_view(view_type='form')['arch'])
        node = form.xpath("//field[@name='category_id']")
        self.assertTrue(node, "the field still exists, so the node stays")
        self.assertEqual(node[0].get('invisible'), '1')
        self.assertIn('name="category_id"',
                      env['res.partner'].get_view(view_type='search')['arch'])

    def test_c15_unscoped_invisible_still_hides_everywhere(self):
        """The default must not change: no view scope means every view."""
        self._c15_rule()
        env = self.as_user()
        self.assertNotIn('category_id', env['res.partner'].fields_get())
        for view_type in ('form', 'search'):
            self.assertNotIn(
                'name="category_id"',
                env['res.partner'].get_view(view_type=view_type)['arch'],
                "%s view still names the field" % view_type)

    def test_c15_view_scope_only_hides(self):
        """A scoped line that also sets read-only would silently apply that
        read-only everywhere - the ORM check has no view to scope by. Refuse it
        on save rather than let it look scoped when it is not."""
        with self.assertRaises(ValidationError):
            self._c15_rule(view_mode='search', readonly=True)

    def test_f1_named_filter_is_removed_from_the_search_arch(self):
        self.Rule.create({
            'name': 'Hide a filter', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'search_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'filter_names': 'type_company'})],
        })
        arch = self.as_user()['res.partner'].get_view(view_type='search')['arch']
        self.assertNotIn('name="type_company"', arch)

    def test_view_cache_does_not_leak_between_users(self):
        """The v19 view cache is keyed without a user, so this is the trap.

        Both users share a language, so a restriction injected on the cached
        side would reach the unrestricted one too.
        """
        self.Rule.create({
            'name': 'Hide notes tab', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'button_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'element_type': 'tab', 'element_name': 'internal_notes'})],
        })
        restricted = self.as_user(self.user)['res.partner'].get_view(view_type='form')['arch']
        bystander = self.env(user=self.other_user)['res.partner'].get_view(
            view_type='form')['arch']

        self.assertNotIn('name="internal_notes"', restricted)
        self.assertIn('name="internal_notes"', bystander,
                      "one user's restriction must not reach another")


@tagged('post_install', '-at_install')
class TestMenuAndChatterEnforcement(AamCommon):

    def test_a1_hidden_menus_are_absent_from_load_menus(self):
        settings = self.env.ref('base.menu_administration')
        self.Rule.create({
            'name': 'Hide settings', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'menu_line_ids': [(0, 0, {'menu_id': settings.id})],
        })
        menus = self.as_user()['ir.ui.menu'].load_menus(False)
        self.assertNotIn(settings.id, menus)

    def test_a1_menus_are_not_hidden_for_other_users(self):
        """Must use a menu the bystander can actually see.

        Settings is administrator-only, so its absence for a plain user would
        prove nothing about leakage.
        """
        shared = self.env.ref('base.menu_apps')
        self.assertIn(shared.id, self.env(user=self.other_user)['ir.ui.menu'].load_menus(False),
                      "fixture check: the bystander must see this menu to begin with")

        self.Rule.create({
            'name': 'Hide apps menu', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'menu_line_ids': [(0, 0, {'menu_id': shared.id})],
        })
        self.assertNotIn(shared.id, self.as_user()['ir.ui.menu'].load_menus(False))
        self.assertIn(shared.id, self.env(user=self.other_user)['ir.ui.menu'].load_menus(False),
                      "load_menus is uid-keyed; hiding must not leak across users")

    def test_g2_message_post_is_blocked_server_side(self):
        self.Rule.create({
            'name': 'No messages', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'chatter_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'hide_send_message': True})],
        })
        env = self.as_user()
        with self.assertRaises(AccessError):
            env['res.partner'].browse(self.company_partner.id).message_post(
                body='hello', subtype_xmlid='mail.mt_comment')

    def test_g3_log_note_and_message_are_independent(self):
        self.Rule.create({
            'name': 'No notes', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'chatter_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'hide_log_note': True})],
        })
        env = self.as_user()
        with self.assertRaises(AccessError):
            env['res.partner'].browse(self.company_partner.id).message_post(
                body='note', subtype_xmlid='mail.mt_note')
        # A broadcast message is a different switch and must still work.
        env['res.partner'].browse(self.company_partner.id).message_post(
            body='msg', subtype_xmlid='mail.mt_comment')


@tagged('post_install', '-at_install')
class TestExportImportEnforcement(AamCommon):
    """Hiding the Export button is not a restriction.

    ``/web/export/csv``, ``/web/export/xlsx`` and a direct RPC call all funnel
    through ``export_data``, so that is where the block has to live.
    """

    def setUp(self):
        super().setUp()
        # Export needs this group at all, restriction or not.
        self.user.write({'groups_id': [(4, self.env.ref('base.group_allow_export').id)]})

    def test_b5_export_is_blocked_at_the_data_layer(self):
        self.Rule.create({
            'name': 'No export', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'hide_export': True})],
        })
        env = self.as_user()
        with self.assertRaises(AccessError):
            env['res.partner'].browse(self.company_partner.id).export_data(['name'])

    def test_h5_global_export_block(self):
        self.Rule.create({
            'name': 'No export anywhere', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_export': True,
        })
        env = self.as_user()
        with self.assertRaises(AccessError):
            env['res.partner'].browse(self.company_partner.id).export_data(['name'])

    def test_c14_a_module_may_redact_exported_rows(self):
        """The hook gets the columns that were really exported, after no-export
        fields were dropped."""
        self.Rule.create({
            'name': 'Email stays in', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'email'),
                'no_export': True})],
        })
        Base = type(self.env['base'])
        seen = []

        def redact(records, fields_to_export, rows):
            seen.append(list(fields_to_export))
            for row in rows:
                row[fields_to_export.index('phone')] = 'X'

        with patch.object(Base, '_aam_postprocess_export', redact):
            rows = self.as_user()['res.partner'].browse(self.company_partner.id).export_data(
                ['name', 'email', 'phone'])['datas']
        self.assertEqual(seen, [['name', 'phone']])
        self.assertEqual(rows[0], ['AAM Alpha Ltd', 'X'])

    def test_c11_blocked_field_is_stripped_from_the_export(self):
        self.Rule.create({
            'name': 'Phone stays in', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'phone'),
                'no_export': True})],
        })
        env = self.as_user()
        rows = env['res.partner'].browse(self.company_partner.id).export_data(
            ['name', 'phone'])['datas']
        self.assertEqual(len(rows[0]), 1, "the blocked column must not be in the file")
        self.assertEqual(rows[0][0], 'AAM Alpha Ltd')

    def test_c1_invisible_field_cannot_be_exported(self):
        """An invisible field reappearing in a spreadsheet would defeat the point."""
        self.Rule.create({
            'name': 'Hide comment', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'comment'),
                'invisible': True})],
        })
        env = self.as_user()
        rows = env['res.partner'].browse(self.company_partner.id).export_data(
            ['name', 'comment'])['datas']
        self.assertEqual(len(rows[0]), 1)

    def test_b6_import_is_blocked(self):
        from odoo.exceptions import UserError
        self.Rule.create({
            'name': 'No import', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'hide_import': True})],
        })
        env = self.as_user()
        with self.assertRaises(UserError):
            env['res.partner'].load(['name'], [['Imported Co']])

    def test_export_still_works_without_a_rule(self):
        env = self.as_user()
        rows = env['res.partner'].browse(self.company_partner.id).export_data(
            ['name', 'phone'])['datas']
        self.assertEqual(len(rows[0]), 2, "fixture check: export works when unrestricted")


@tagged('post_install', '-at_install')
class TestToolbarEnforcement(AamCommon):
    """The cog menu's server half (features B8-B11, H7, H8).

    `ir.actions.actions.get_bindings` is where `get_views` gets both the
    `print` and `action` toolbar groups, so it decides what the cog can ever
    contain. It had no Python coverage at all - only a tour, on a model with no
    report bound, which is exactly the case that hid the bug below.
    """

    def setUp(self):
        super().setUp()
        self.report = self.env['ir.actions.report'].create({
            'name': 'AAM Test Report',
            'model': 'res.partner',
            'report_type': 'qweb-pdf',
            'report_name': 'odooapp_access_management.aam_test_report',
            'binding_model_id': self.partner_model.id,
            'binding_type': 'report',
        })

    def _bindings(self, env):
        return env['ir.actions.actions'].get_bindings('res.partner')

    def _report_ids(self, env):
        return [entry['id'] for entry in self._bindings(env).get('report', [])]

    def test_report_is_bound_without_any_rule(self):
        """The baseline the other two tests are differences from."""
        self.assertIn(self.report.id, self._report_ids(self.as_user()))

    def test_h7_hide_print_removes_the_reports(self):
        self.Rule.create({
            'name': 'No printing', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_print': True})
        self.assertEqual(self._bindings(self.as_user()).get('report', []), [])

    def test_h8_hide_action_button_takes_the_reports_too(self):
        """One cog holds both groups, so half-clearing it leaves it on screen.

        Found on `mrp.bom`: with "Hide Action (cog) Menu" set, the menu was
        still there holding "BoM Overview" - the flag's label promises the
        control goes away, and for any model with a report it did not.
        """
        self.Rule.create({
            'name': 'No cog', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_action_button': True})
        bindings = self._bindings(self.as_user())
        self.assertEqual(bindings.get('action', []), [])
        self.assertEqual(bindings.get('report', []), [])

    def test_hide_print_leaves_the_action_group_alone(self):
        """The narrower flag must stay narrow."""
        server_action = self.env['ir.actions.server'].create({
            'name': 'AAM Test Action',
            'model_id': self.partner_model.id,
            'state': 'code',
            'code': 'pass',
            'binding_model_id': self.partner_model.id,
        })
        self.Rule.create({
            'name': 'No printing', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])], 'hide_print': True})
        bindings = self._bindings(self.as_user())
        self.assertEqual(bindings.get('report', []), [])
        self.assertIn(server_action.id, [a['id'] for a in bindings.get('action', [])])


@tagged('post_install', '-at_install')
class TestViewSelectionEnforcement(AamCommon):

    def test_b14_hide_edit_button(self):
        self.Rule.create({
            'name': 'No inline edit', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'hide_edit_button': True})],
        })
        arch = self.as_user()['res.partner'].get_view(view_type='form')['arch']
        self.assertIn('edit="False"', arch)
        # Blocking the affordance is not the same as blocking the write.
        self.assertTrue(self.as_user()['res.partner'].has_access('write'))


@tagged('post_install', '-at_install')
class TestSessionControl(AamCommon):

    def _device(self, user, session_identifier):
        now = fields.Datetime.now()
        return self.env['res.device.log'].sudo().create({
            'session_identifier': session_identifier, 'user_id': user.id,
            'platform': 'linux', 'browser': 'chrome', 'ip_address': '127.0.0.1',
            'first_activity': now, 'last_activity': now,
            # Odoo 18's `res.device` view keeps only rows with `revoked = False`
            # (a NULL is dropped); core's own logger always writes it.
            'revoked': False,
        })

    def test_j3_the_module_adds_nothing_to_the_session_token(self):
        """Every field in this set is hashed into each session's token.

        Adding one signs every user out the moment the module is installed,
        and it broke odoo.sh's Connect button on a client's UAT (2026-09-27):
        Connect builds its session outside the normal login, the build then
        rejected it on the next request, and the administrator landed on the
        login page instead of the backend.
        """
        Users = self.env['res.users']
        ours = sorted(
            name for name in Users._get_session_token_fields()
            if name in Users._fields
            and Users._fields[name]._module == 'odooapp_access_management')
        self.assertEqual(ours, [])

    def test_j3_force_logout_revokes_every_session_of_that_user_only(self):
        mine = [self._device(self.user, 'aamsessiona'), self._device(self.user, 'aamsessionb')]
        theirs = self._device(self.other_user, 'aamsessionc')
        deleted = []
        admin = self.env.ref('base.user_admin')

        with patch.object(root.session_store, 'delete_from_identifiers',
                          side_effect=lambda ids: deleted.extend(ids)):
            self.user.with_user(admin).action_aam_force_logout()

        self.assertEqual(sorted(deleted), ['aamsessiona', 'aamsessionb'],
                         "both of this user's sessions must be deleted, and nothing else")
        self.assertTrue(all(d.revoked for d in mine))
        self.assertFalse(theirs.revoked, "another user's session must survive")


@tagged('post_install', '-at_install')
class TestUntouchedUser(AamCommon):
    """A user no rule reaches gets exactly what the superuser gets."""

    def test_output_is_the_same_as_without_any_rule(self):
        self.mask_rule('res.partner', 'phone')  # reaches the operator only
        # Odoo 18: a user's groups are `groups_id`.
        self.other_user.write({'groups_id': [(4, self.env.ref('base.group_allow_export').id)]})
        ids = (self.company_partner | self.person_partner).ids
        names = ['name', 'display_name', 'phone', 'email', 'parent_id']
        spec = {'name': {}, 'phone': {}, 'parent_id': {'fields': {'display_name': {}}}}
        domain = [('id', 'in', ids)]
        theirs = self.as_user(self.other_user)['res.partner']
        plain = self.env['res.partner']
        self.assertEqual(theirs.browse(ids).read(names), plain.browse(ids).read(names))
        self.assertEqual(theirs.search_read(domain, names, order='id'),
                         plain.search_read(domain, names, order='id'))
        self.assertEqual(theirs.browse(ids).web_read(spec), plain.browse(ids).web_read(spec))
        self.assertEqual(theirs.browse(ids).export_data(['name', 'phone'])['datas'],
                         plain.browse(ids).export_data(['name', 'phone'])['datas'])
        self.assertEqual(theirs.name_search('AAM Alpha'), plain.name_search('AAM Alpha'))
        # Odoo 18 groups through read_group (formatted_read_group came with 19).
        self.assertEqual(
            [g['phone'] for g in theirs.read_group(domain, ['phone'], ['phone'])],
            [g['phone'] for g in plain.read_group(domain, ['phone'], ['phone'])])
