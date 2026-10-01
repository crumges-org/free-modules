"""The Explainer, JSON portability, presets and masking helpers."""

import base64
import json
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged

from ..models.aam_masking import MASKERS, apply_mask, register_mask
from .common import AamCommon


@tagged('post_install', '-at_install')
class TestMasking(AamCommon):

    def test_full(self):
        self.assertEqual(apply_mask('secret', {'type': 'full', 'char': '*'}), '******')

    def test_partial_keeps_the_tail(self):
        self.assertEqual(
            apply_mask('1234567890', {'type': 'partial', 'char': '*', 'keep': 4}),
            '******7890')

    def test_partial_hides_everything_when_too_short(self):
        """Keeping four of four characters would reveal the whole value."""
        self.assertEqual(
            apply_mask('1234', {'type': 'partial', 'char': '*', 'keep': 4}), '****')

    def test_email_keeps_the_domain(self):
        self.assertEqual(
            apply_mask('alice@example.com', {'type': 'email', 'char': '*'}),
            'a****@example.com')

    def test_phone_keeps_formatting(self):
        masked = apply_mask('+91 98765 43210', {'type': 'phone', 'char': '*', 'keep': 4})
        self.assertTrue(masked.endswith('3210'))
        self.assertIn(' ', masked, "formatting should survive so the shape stays readable")

    def test_custom_pattern(self):
        self.assertEqual(
            apply_mask('anything', {'type': 'custom', 'pattern': '[redacted]'}),
            '[redacted]')

    def test_falsy_values_pass_through(self):
        for value in (False, None, ''):
            self.assertEqual(apply_mask(value, {'type': 'full', 'char': '*'}), value)

    def test_c14_a_mask_type_added_by_another_module_is_applied(self):
        self.addCleanup(MASKERS.pop, 'aam_test_upper', None)
        register_mask('aam_test_upper', lambda text, keep, char: text.upper())
        self.assertEqual(apply_mask('abc', {'type': 'aam_test_upper'}), 'ABC')

    def test_c14_a_registered_type_cannot_replace_a_built_in(self):
        self.addCleanup(MASKERS.pop, 'full', None)
        register_mask('full', lambda text, keep, char: text)
        self.assertEqual(apply_mask('abc', {'type': 'full', 'char': '*'}), '***')

    def test_c14_an_unknown_mask_type_leaves_the_value_alone(self):
        """A line whose mask type belonged to a module that is gone must not break reads."""
        self.assertEqual(apply_mask('abc', {'type': 'aam_test_nobody'}), 'abc')

    def test_mask_labels_do_not_promise_a_number_of_digits(self):
        """How many characters stay visible is set per line (Visible Characters);
        a label saying "show last 4" was wrong for every line that keeps 2."""
        labels = dict(self.env['aam.rule.field']._fields['mask_type']._description_selection(self.env))
        for key in ('partial', 'phone'):
            self.assertFalse(any(ch.isdigit() for ch in labels[key]), labels[key])

    def test_the_fields_list_of_a_rule_shows_how_many_characters_stay_visible(self):
        arch = self.env['aam.rule'].get_view(view_type='form')['arch']
        lines = arch[arch.index('<field name="field_line_ids"'):]
        listing = lines[:lines.index('</list>')]
        self.assertIn('name="mask_keep"', listing)

    def test_visible_characters_shows_where_the_mask_keeps_characters(self):
        """In the list and in the line form alike: shown for the types that keep
        characters, hidden for the ones that do not. Hiding by the types that do
        not keep any leaves a type another module adds (Pro's) shown."""
        from lxml import etree
        from odoo.tools.safe_eval import safe_eval
        arch = etree.fromstring(self.env['aam.rule'].get_view(view_type='form')['arch'])
        places = arch.xpath("//field[@name='field_line_ids']//field[@name='mask_keep']")
        self.assertEqual(len(places), 2, "the list column and the line form")
        for place in places:
            for mask_type, shown in (('partial', True), ('phone', True), ('none', False),
                                     ('full', False), ('email', False), ('custom', False)):
                hidden = safe_eval(place.get('invisible') or 'False', {'mask_type': mask_type})
                self.assertEqual(not hidden, shown, (mask_type, place.get('invisible')))


@tagged('post_install', '-at_install')
class TestExplainer(AamCommon):

    def test_l1_attributes_each_effect_to_its_rule(self):
        profile = self.Profile.create({
            'name': 'Ops', 'group_ids': [(6, 0, [self.crew.id])]})
        via_profile = self.Rule.create({
            'name': 'Profile rule', 'target_type': 'profile', 'profile_id': profile.id,
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})],
        })
        direct = self.Rule.create({
            'name': 'Direct rule', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'phone'),
                'mask_type': 'phone'})],
        })

        wizard = self.env['aam.explain'].create({
            'user_id': self.user.id, 'model_id': self.partner_model.id})
        wizard.action_explain()

        ours = wizard.line_ids.filtered(lambda l: l.source == 'aam')
        self.assertTrue(ours)
        named = set(ours.mapped('rule_id'))
        self.assertIn(via_profile, named)
        self.assertIn(direct, named)

    def test_l1_explains_how_the_rule_reaches_the_user(self):
        profile = self.Profile.create({
            'name': 'Ops', 'group_ids': [(6, 0, [self.crew.id])]})
        self.Rule.create({
            'name': 'Profile rule', 'target_type': 'profile', 'profile_id': profile.id,
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})],
        })
        wizard = self.env['aam.explain'].create({
            'user_id': self.user.id, 'model_id': self.partner_model.id})
        wizard.action_explain()

        reasons = ' '.join(wizard.line_ids.filtered(
            lambda l: l.source == 'aam').mapped('reason')).lower()
        self.assertIn('profile', reasons)
        self.assertIn(self.crew.name.lower(), reasons,
                      "the group that carries the profile should be named")

    def test_l1_includes_native_access(self):
        wizard = self.env['aam.explain'].create({
            'user_id': self.user.id, 'model_id': self.partner_model.id})
        wizard.action_explain()
        sources = set(wizard.line_ids.mapped('source'))
        self.assertTrue({'acl', 'record_rule'} & sources,
                        "native ACLs and record rules belong in the same answer")

    def test_l1_findings_do_not_survive_a_change_of_selection(self):
        """Change the model and the previous answer must not stay on screen.

        `line_ids` is real stored state on the wizard, written by
        `action_explain()`. Nothing used to clear it, so switching the model
        left the old findings in place and the summary presented them as the
        answer for the new model. The tours never caught it because they always
        press Explain immediately after changing a field.
        """
        self.Rule.create({
            'name': 'Partner rule', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})],
        })
        wizard = self.env['aam.explain'].create({
            'user_id': self.user.id, 'model_id': self.partner_model.id})
        wizard.action_explain()
        self.assertTrue(wizard.line_ids, "precondition: the first run found something")

        currency = self.env['ir.model']._get('res.currency')
        with Form(wizard) as form:
            form.model_id = currency

        self.assertFalse(
            wizard.line_ids,
            "findings from the previous model must be dropped when the model changes")

    def test_l1_summary_does_not_claim_a_clean_bill_before_it_has_run(self):
        """An unrun wizard must not assert "no restrictions found".

        Empty `line_ids` means "not run yet" just as often as it means "ran and
        found nothing", and the compute could not tell the two apart - so a user
        who picked a user and a model saw a confident, wrong answer before ever
        pressing Explain.
        """
        self.Rule.create({
            'name': 'Partner rule', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})],
        })
        wizard = self.env['aam.explain'].create({
            'user_id': self.user.id, 'model_id': self.partner_model.id})

        self.assertNotIn('No restrictions found', wizard.summary or '',
                         "the wizard has not run yet - it cannot claim a clean bill")

        wizard.action_explain()
        self.assertIn('effect(s)', wizard.summary or '')

    def test_l1_reports_administrators_as_protected(self):
        wizard = self.env['aam.explain'].create({
            'user_id': self.env.ref('base.user_admin').id,
            'model_id': self.partner_model.id})
        wizard.action_explain()
        self.assertTrue(wizard.is_protected)
        self.assertFalse(wizard.line_ids.filtered(lambda l: l.source == 'aam'))


@tagged('post_install', '-at_install')
class TestRulesIo(AamCommon):

    def _seed(self):
        return self.Rule.create({
            'name': 'Portable rule', 'target_type': 'group',
            'group_ids': [(6, 0, [self.crew.id])],
            'hide_export': True,
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True,
                'domain': "[('is_company', '=', True)]"})],
            'field_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'phone'),
                'mask_type': 'phone'})],
            'menu_line_ids': [(0, 0, {
                'menu_id': self.env.ref('base.menu_administration').id})],
        })

    def _export(self):
        wizard = self.env['aam.rules.export'].create({})
        wizard.action_export()
        return json.loads(base64.b64decode(wizard.data).decode())

    def test_l4_export_uses_symbolic_references_only(self):
        self._seed()
        payload = self._export()
        rule = next(r for r in payload['rules'] if r['name'] == 'Portable rule')

        # The crew group was made through the interface, so it has no external
        # id and must fall back to a name reference rather than vanishing.
        self.assertEqual(rule['group_ids'], ['name:AAM Test Crew'])
        self.assertEqual(rule['model_line_ids'][0]['model_id'], 'res.partner')
        self.assertEqual(rule['field_line_ids'][0]['field_id'], 'res.partner.phone')
        self.assertEqual(rule['menu_line_ids'][0]['menu_id'], 'base.menu_administration')

        blob = json.dumps(rule)
        self.assertNotIn('"model_id": %s' % self.partner_model.id, blob,
                         "database ids must never reach the file")

    def test_l4_the_rule_references_in_the_file_come_from_one_method(self):
        """A module that adds a reference field to the rule extends `_rule_refs`."""
        self._seed()
        Mixin = type(self.env['aam.rules.io.mixin'])
        real = Mixin._rule_refs

        def without_companies(records):
            refs = real(records)
            refs.pop('company_ids')
            return refs

        with patch.object(Mixin, '_rule_refs', without_companies):
            rule = next(r for r in self._export()['rules'] if r['name'] == 'Portable rule')
        self.assertNotIn('company_ids', rule)
        self.assertEqual(rule['group_ids'], ['name:AAM Test Crew'])

    def test_l4_dry_run_reports_every_unresolvable_reference(self):
        self._seed()
        payload = self._export()
        rule = next(r for r in payload['rules'] if r['name'] == 'Portable rule')
        rule['model_line_ids'].append({'model_id': 'no.such.model', 'no_unlink': True})
        rule['field_line_ids'].append({
            'model_id': 'res.partner', 'field_id': 'res.partner.no_such_field',
            'invisible': True})
        rule['group_ids'].append('missing_app.group_manager')

        wizard = self.env['aam.rules.import'].create({
            'data': base64.b64encode(json.dumps(payload).encode()), 'mode': 'dry_run'})
        wizard.action_run()

        self.assertEqual(wizard.problem_count, 3)
        self.assertEqual(wizard.imported_count, 0, "a dry run must write nothing")
        self.assertIn('no.such.model', wizard.report)
        self.assertIn('no_such_field', wizard.report)

    def test_l4_import_applies_and_skips_only_the_broken_parts(self):
        original = self._seed()
        payload = self._export()
        rule = next(r for r in payload['rules'] if r['name'] == 'Portable rule')
        rule['model_line_ids'].append({'model_id': 'no.such.model', 'no_unlink': True})
        original.unlink()

        wizard = self.env['aam.rules.import'].create({
            'data': base64.b64encode(json.dumps(payload).encode()),
            'mode': 'apply', 'on_conflict': 'replace'})
        wizard.action_run()

        imported = self.Rule.search([('name', '=', 'Portable rule')])
        self.assertEqual(len(imported), 1)
        self.assertEqual(len(imported.model_line_ids), 1,
                         "the unresolvable line is dropped, the good one survives")
        self.assertEqual(imported.group_ids, self.crew)
        self.assertTrue(imported.hide_export)

    def test_l4_group_without_an_external_id_survives_a_round_trip(self):
        """Customer-made groups have no xmlid; dropping them would silently
        strip a rule's target, which is the failure this format exists to
        prevent."""
        original = self._seed()
        payload = self._export()
        original.unlink()

        wizard = self.env['aam.rules.import'].create({
            'data': base64.b64encode(json.dumps(payload).encode()),
            'mode': 'apply', 'on_conflict': 'replace'})
        wizard.action_run()

        imported = self.Rule.search([('name', '=', 'Portable rule')])
        self.assertEqual(imported.group_ids, self.crew)
        self.assertEqual(wizard.problem_count, 0)

    def test_l4_clean_file_reports_no_problems(self):
        self._seed()
        payload = self._export()
        wizard = self.env['aam.rules.import'].create({
            'data': base64.b64encode(json.dumps(payload).encode()), 'mode': 'dry_run'})
        wizard.action_run()
        self.assertEqual(wizard.problem_count, 0)


@tagged('post_install', '-at_install')
class TestPresets(AamCommon):

    def _preset(self, key):
        return self.env['aam.preset'].search([('key', '=', key)], limit=1)

    def test_l9_preset_creates_a_profile_and_rule(self):
        # Count only what this test created. Searching by name alone passed on
        # an empty database and failed the moment somebody had already loaded
        # the same preset by hand - the assertion was about the database, not
        # about the wizard.
        before = self.Profile.search([]).ids
        wizard = self.env['aam.preset.wizard'].create({
            'preset_ids': [(6, 0, self._preset('auditor').ids)],
            'group_ids': [(6, 0, [self.crew.id])]})
        wizard.action_apply()

        profile = self.Profile.search([
            ('id', 'not in', before), ('name', '=', 'Read-only Auditor')])
        self.assertEqual(len(profile), 1)
        self.assertEqual(profile.group_ids, self.crew)
        self.assertTrue(profile.rule_ids)
        self.assertTrue(profile.rule_ids[0].readonly_user)

    def test_l9_bank_preset_masks_every_copy_of_the_number(self):
        """`sanitized_acc_number` stores the same account number, spaces
        stripped. Masking only `acc_number` left it readable over RPC."""
        bank = self.env['res.partner.bank'].create({
            'acc_number': 'BE68 5390 0754 7034', 'partner_id': self.company_partner.id})
        wizard = self.env['aam.preset.wizard'].create({
            'preset_ids': [(6, 0, self._preset('account_no_bank_details').ids)],
            'group_ids': [(6, 0, [self.crew.id])]})
        wizard.action_apply()

        values = self.as_user()['res.partner.bank'].browse(bank.id).read(
            ['acc_number', 'sanitized_acc_number'])[0]
        for fname in ('acc_number', 'sanitized_acc_number'):
            self.assertNotIn('53900754', values[fname].replace(' ', ''),
                             "%s must not show the full number" % fname)

    def test_l9_preset_skips_models_that_are_not_installed(self):
        """A preset must degrade, not explode, on a database without the app."""
        wizard = self.env['aam.preset.wizard'].create({
            'preset_ids': [(6, 0, self._preset('warehouse').ids)]})
        before = self.Profile.search([]).ids
        wizard.action_apply()
        rule = self.Profile.search([
            ('id', 'not in', before), ('name', '=', 'Warehouse Operator')]).rule_ids
        for line in rule.model_line_ids:
            self.assertIn(line.model_name, self.env,
                          "only models present in this database should be referenced")

    def test_l9_coverage_names_what_will_be_skipped(self):
        wizard = self.env['aam.preset.wizard'].create({
            'preset_ids': [(6, 0, self._preset('warehouse').ids)]})
        if 'stock.picking' not in self.env:
            self.assertIn('stock.picking', wizard.coverage)

    def test_l9_several_presets_apply_as_separate_profiles(self):
        """One profile each, so they can be assigned to different people later."""
        presets = self._preset('auditor') | self._preset('no_settings')
        wizard = self.env['aam.preset.wizard'].create({
            'preset_ids': [(6, 0, presets.ids)], 'profile_prefix': 'Zeta'})
        wizard.action_apply()

        created = self.Profile.search([('name', 'like', 'Zeta %')])
        self.assertEqual(len(created), 2)
        self.assertEqual(
            sorted(created.mapped('name')),
            ['Zeta No Settings, No Apps', 'Zeta Read-only Auditor'])
        for profile in created:
            self.assertEqual(len(profile.rule_ids), 1)

    def test_l9_catalogue_is_mirrored_into_the_table(self):
        """`init()` runs on install and on -u; every entry must be there once."""
        catalogue = self.env['aam.preset']._catalogue()
        records = self.env['aam.preset'].search([])
        self.assertEqual(len(records), len(catalogue))
        self.assertEqual(sorted(records.mapped('key')), sorted(catalogue))
        for record in records:
            self.assertEqual(record.name, catalogue[record.key]['name'])
            self.assertTrue(record.description, "every preset needs a description")
            self.assertTrue(
                record.restriction_count,
                "%s restricts nothing at all" % record.key)

    def test_l9_catalogue_names_resolve_where_the_app_is_installed(self):
        """The failure mode this guards is silent.

        A misspelt field is skipped rather than raised, so a preset can look
        applied and do nothing. Anywhere the app *is* installed, every name it
        mentions must resolve - which is how `hr.contract` (v19 renamed it to
        `hr.version`) and `maintenance.request.user_id` (it is
        `technician_user_id`) would have got through unnoticed.
        """
        installed = set(self.env['ir.module.module'].sudo().search(
            [('state', '=', 'installed')]).mapped('name'))
        for key, spec in self.env['aam.preset']._catalogue().items():
            for line in spec.get('field_lines', []):
                model = line['model']
                if model not in self.env:
                    continue
                if line.get('requires') and line['requires'] not in installed:
                    # Declared optional: the app that adds this field is absent.
                    continue
                self.assertIn(
                    line['field'], self.env[model]._fields,
                    "%s names %s.%s, which does not exist in this database"
                    % (key, model, line['field']))

    def test_l9_availability_search_agrees_with_the_compute(self):
        """The library's default filter must not disagree with the badge."""
        Preset = self.env['aam.preset']
        searched = set(Preset.search([('is_available', '=', True)]).ids)
        computed = {p.id for p in Preset.search([]) if p.is_available}
        self.assertEqual(searched, computed)
        self.assertEqual(
            set(Preset.search([('is_available', '=', False)]).ids),
            {p.id for p in Preset.search([])} - computed)

    def test_l9_use_this_preset_opens_the_wizard_preloaded(self):
        preset = self._preset('auditor')
        action = preset.action_use()
        self.assertEqual(action['res_model'], 'aam.preset.wizard')
        self.assertEqual(action['context']['default_preset_ids'], preset.ids)

    EXTRA = {
        'name': "AAM Test Extra", 'category': 'general', 'apps': "Any database",
        'description': "Added by a test.", 'rule': {'hide_export': True},
        'field_lines': [
            {'model': 'res.partner', 'field': 'phone', 'mask_type': 'phone'},
            {'model': 'res.partner', 'field': 'email', 'mask_type': 'email',
             'requires': 'base'},
            {'model': 'aam.test.absent', 'field': 'x', 'mask_type': 'phone',
             'requires': 'aam_test_absent_module'},
        ],
    }

    def _with_extra_preset(self):
        Preset = type(self.env['aam.preset'])
        real = Preset._catalogue
        patcher = patch.object(
            Preset, '_catalogue', lambda records: dict(real(records), aam_test_extra=self.EXTRA))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.env['aam.preset']._sync_catalogue()
        return self._preset('aam_test_extra')

    def test_l9_a_module_can_add_a_preset_to_the_catalogue(self):
        preset = self._with_extra_preset()
        self.assertTrue(preset, "synced from _catalogue(), not from the module-level dict")
        wizard = self.env['aam.preset.wizard'].create({
            'preset_ids': [(6, 0, preset.ids)], 'user_ids': [(6, 0, [self.user.id])]})
        wizard.action_apply()
        policy = self.policy_for()
        self.assertTrue(policy['globals']['hide_export'])
        self.assertEqual(policy['fields']['res.partner']['phone']['mask']['type'], 'phone')

    def test_l9_an_optional_line_does_not_make_a_preset_unavailable(self):
        """`requires` marks a line optional: skipped when that module is not installed."""
        preset = self._with_extra_preset()
        self.assertTrue(preset.is_available)
        wizard = self.env['aam.preset.wizard'].create({
            'preset_ids': [(6, 0, preset.ids)], 'user_ids': [(6, 0, [self.user.id])]})
        wizard.action_apply()
        fields_ = self.policy_for()['fields']['res.partner']
        self.assertEqual(fields_['email']['mask']['type'], 'email', "its module is installed")


@tagged('post_install', '-at_install')
class TestDashboard(AamCommon):

    def test_k1_dashboard_data_is_json_safe(self):
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})]})
        data = self.env['aam.dashboard'].get_dashboard_data()
        json.dumps(data)  # would raise on a set or a recordset
        self.assertTrue(data['tiles'])
        self.assertIn('insights', data)

    def test_k3_heatmap_counts_restrictions_per_model(self):
        """Assert the delta, never the absolute count.

        The heatmap counts every rule in the database, so a database that
        already has some - which is every real one, and this one once the
        presets or the screenshot fixtures have been loaded - makes an absolute
        assertion fail for the wrong reason.
        """
        def partner_cells():
            data = self.env['aam.dashboard'].get_heatmap_data()
            json.dumps(data)  # would raise on a set or a recordset
            row = next((r for r in data['rows'] if r['model'] == 'res.partner'), None)
            return row['cells'] if row else {'unlink': 0, 'export': 0}

        before = partner_cells()
        self.Rule.create({
            'name': 'Anything', 'target_type': 'user',
            'user_ids': [(6, 0, [self.user.id])],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id,
                'no_unlink': True, 'hide_export': True})]})
        after = partner_cells()
        self.assertEqual(after['unlink'], before['unlink'] + 1)
        self.assertEqual(after['export'], before['export'] + 1)

    def test_k8_access_map_reports_the_acl_matrix(self):
        data = self.env['aam.dashboard'].get_access_map_detail(self.internal_group.id)
        json.dumps(data)
        self.assertEqual(data['group']['id'], self.internal_group.id)
        self.assertTrue(data['models'])
        for row in data['models']:
            self.assertIn(row['status'], ('full', 'partial', 'readonly', 'none'))

    def test_k1_reporting_requires_the_module_group(self):
        outsider = self.env['res.users'].create({
            'name': 'Outsider', 'login': 'aam_outsider',
            'groups_id': [(6, 0, [self.internal_group.id])]})
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self.env['aam.dashboard'].with_user(outsider).get_dashboard_data()


@tagged('post_install', '-at_install')
class TestRuleWizard(AamCommon):
    """The guided setup wizard.

    It is a deliberate simplification of `aam.rule`, so what matters most is that
    the simplification is *faithful*: what the review step promises is what gets
    written, and a rule that has outgrown the wizard is refused rather than
    quietly flattened.
    """

    def _wizard(self, **values):
        base = {
            'target_type': 'user',
            'user_ids': [(6, 0, self.user.ids)],
            'model_ids': [(6, 0, self.partner_model.ids)],
        }
        base.update(values)
        return self.env['aam.rule.wizard'].create(base)

    def _applied(self, wizard):
        return self.Rule.search([('name', '=', wizard._default_name())], limit=1)

    def test_m1_view_only_blocks_create_write_and_unlink(self):
        wizard = self._wizard(access_level='readonly')
        wizard.action_apply()

        line = self._applied(wizard).model_line_ids
        self.assertTrue(line.readonly_model)
        self.assertEqual(sorted(line._blocked_modes()), ['create', 'unlink', 'write'],
                         "'View only' must block everything except reading")

    def test_m1_cannot_delete_leaves_create_and_write_alone(self):
        wizard = self._wizard(access_level='no_delete')
        wizard.action_apply()
        self.assertEqual(
            sorted(self._applied(wizard).model_line_ids._blocked_modes()), ['unlink'])

    def test_m1_own_records_resolves_the_domain_per_model(self):
        """The domain is derived from each model, not hard-coded.

        `res.partner` carries a `user_id`; a model with no link to `res.users` has
        to come back with no domain rather than a broken one that would deny
        everything.
        """
        wizard = self._wizard(record_scope='own')
        self.assertEqual(wizard._domain_for('res.partner'),
                         "[('user_id', '=', user.id)]")
        self.assertIsNone(wizard._domain_for('res.currency'),
                          "a model with no user link must get no domain at all")

    def test_m1_refuses_to_restrict_an_administrator(self):
        """Protection is reported before Apply, and enforced at Apply.

        Letting it through would surface the model's own ValidationError three
        screens later, naming a constraint the user never saw.
        """
        wizard = self._wizard(
            user_ids=[(6, 0, self.env.ref('base.user_admin').ids)],
            access_level='readonly')
        self.assertTrue(wizard.hits_protected)
        self.assertIn('cannot be restricted', wizard.audience)
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_m1_saves_a_reusable_profile_when_asked(self):
        before = self.Profile.search([]).ids
        wizard = self._wizard(access_level='no_delete', save_as_profile=True,
                              profile_name='Wizard Profile')
        wizard.action_apply()

        profile = self.Profile.search([('id', 'not in', before)])
        self.assertEqual(len(profile), 1)
        self.assertEqual(profile.name, 'Wizard Profile')
        self.assertEqual(profile.rule_ids.target_type, 'profile',
                         "the rule must be retargeted at the profile it created")
        self.assertIn(self.user, profile.user_ids)

    def test_m1_does_not_write_empty_chatter_or_search_lines(self):
        """Visiting a step must not leave a line behind that restricts nothing."""
        wizard = self._wizard(access_level='no_delete')
        wizard.action_apply()
        rule = self._applied(wizard)
        self.assertFalse(rule.chatter_line_ids)
        self.assertFalse(rule.search_line_ids)

    def test_m1_chatter_flags_produce_one_line_per_model(self):
        wizard = self._wizard(hide_log_note=True)
        wizard.action_apply()
        lines = self._applied(wizard).chatter_line_ids
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines.hide_log_note)
        self.assertFalse(lines.hide_followers)

    def test_m1_next_refuses_an_incomplete_step(self):
        wizard = self.env['aam.rule.wizard'].create({'target_type': 'user'})
        with self.assertRaises(UserError):
            wizard.action_next()

        wizard.user_ids = [(6, 0, self.user.ids)]
        wizard.action_next()
        self.assertEqual(wizard.state, 'what')
        with self.assertRaises(UserError):
            wizard.action_next()

    def test_m1_edit_refuses_a_rule_it_cannot_represent(self):
        """A rule that has outgrown the wizard is refused, never flattened."""
        rule = self.Rule.create({
            'name': 'Windowed', 'target_type': 'user',
            'user_ids': [(6, 0, self.user.ids)],
            'model_line_ids': [(0, 0, {
                'model_id': self.partner_model.id, 'no_unlink': True})],
            'time_window_ids': [(0, 0, {'day_of_week': '0'})],
        })
        self.assertTrue(self.env['aam.rule.wizard']._unsupported_reasons(rule))
        with self.assertRaises(UserError):
            rule.action_edit_in_wizard()

    def test_m1_edit_refuses_models_restricted_differently(self):
        currency = self.env['ir.model']._get('res.currency')
        rule = self.Rule.create({
            'name': 'Uneven', 'target_type': 'user',
            'user_ids': [(6, 0, self.user.ids)],
            'model_line_ids': [
                (0, 0, {'model_id': self.partner_model.id, 'no_unlink': True}),
                (0, 0, {'model_id': currency.id, 'readonly_model': True}),
            ],
        })
        self.assertTrue(self.env['aam.rule.wizard']._unsupported_reasons(rule),
                        "per-model differences are exactly what the wizard flattens")

    def test_m1_a_representable_rule_round_trips_unchanged(self):
        wizard = self._wizard(access_level='readonly', hide_export=True,
                              record_scope='own')
        wizard.action_apply()
        rule = self._applied(wizard)
        snapshot = {
            'readonly_model': rule.model_line_ids.readonly_model,
            'hide_export': rule.model_line_ids.hide_export,
            'domain': rule.model_line_ids.domain,
        }

        self.assertFalse(self.env['aam.rule.wizard']._unsupported_reasons(rule))
        rule.action_edit_in_wizard()
        loaded = self.env['aam.rule.wizard'].search(
            [('rule_id', '=', rule.id)], limit=1)
        self.assertTrue(loaded, "edit mode must leave a wizard pointing at the rule")
        loaded.action_apply()

        rule.invalidate_recordset()
        self.assertEqual(len(rule.model_line_ids), 1,
                         "re-applying must replace the lines, not add to them")
        self.assertEqual({
            'readonly_model': rule.model_line_ids.readonly_model,
            'hide_export': rule.model_line_ids.hide_export,
            'domain': rule.model_line_ids.domain,
        }, snapshot)

    def test_m1_field_treatment_maps_onto_the_rule_field_line(self):
        wizard = self._wizard(field_line_ids=[(0, 0, {
            'model_id': self.partner_model.id,
            'field_id': self.field_id('res.partner', 'email'),
            'treatment': 'mask', 'mask_type': 'email'})])
        wizard.action_apply()

        line = self._applied(wizard).field_line_ids
        self.assertEqual(line.mask_type, 'email')
        self.assertFalse(line.invisible)

    def test_m1_masking_a_field_that_cannot_be_masked_is_refused_early(self):
        """Mirrors `aam.rule.field._check_maskable` so the error names the field."""
        with self.assertRaises(ValidationError):
            self._wizard(field_line_ids=[(0, 0, {
                'model_id': self.partner_model.id,
                'field_id': self.field_id('res.partner', 'image_1920'),
                'treatment': 'mask'})])
