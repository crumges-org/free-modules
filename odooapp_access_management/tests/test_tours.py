"""Browser tours.

Two crash-level bugs shipped past the whole Python suite during development -
a `t-inherit` xpath that stopped matching (every list view went blank) and a
kanban `t-if` reading an undeclared field (the default Profiles screen went
blank). Neither is reachable from Python, because Python never renders an OWL
template. These tours are the layer that catches that class of mistake.

`test_restricted_ui` is the only place the client-side half of the policy is
tested at all: the JS patches decide what a restricted user sees, and until now
nothing asserted they ran.
"""

from odoo import Command
from odoo.tests import HttpCase, tagged

from .common import ChromeSpawnTolerance


@tagged('post_install', '-at_install')
class TestAamTours(ChromeSpawnTolerance, HttpCase):
    """Fixtures shared by every tour.

    Everything a tour asserts on is created here rather than relying on demo
    data: these tests have to pass on a database installed with `--without-demo`
    as well as one with it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Onboarding tours hijack the browser before ours gets to run.
        # `tour_enabled` computes to True for an admin whenever the database has
        # no demo modules (web_tour/models/res_users.py:13) - and these dev
        # databases are deliberately demo-free, to match the Odoo 19 pair. With
        # `project` installed, `project_tour` then clicks into the Project app
        # the moment the page loads and every admin tour times out on its first
        # step. Disabled for everyone, so a module added later cannot
        # reintroduce it.
        cls.env['res.users'].sudo().search([]).tour_enabled = False

        cls.env['ir.config_parameter'].sudo().set_param('aam.enabled', '1')
        cls.env['ir.config_parameter'].sudo().set_param('aam.allow_restrict_admin', '0')

        # A group of our own, so the Access Map's filter and matrix assertions
        # do not depend on whichever groups happen to exist in the database.
        cls.marker_group = cls.env['res.groups'].create({
            'name': 'AAM Tour Marker',
            'category_id': cls.env.ref(
                'odooapp_access_management.module_category_access_management').id,
        })
        cls.env['ir.model.access'].create({
            'name': 'aam_tour_marker_partner_readonly',
            'model_id': cls.env['ir.model']._get('res.partner').id,
            'group_id': cls.marker_group.id,
            'perm_read': True,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
        })

        # The restricted user. `start_tour` authenticates with the login as the
        # password, so the two have to match.
        cls.operator = cls.env['res.users'].create({
            'name': 'AAM Tour Operator',
            'login': 'aam_tour_operator',
            'password': 'aam_tour_operator',
            'groups_id': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('base.group_partner_manager').id,
                # Without this the Export entry is absent for everyone, and the
                # restricted tour's "Export is gone" assertion would pass while
                # proving nothing about the policy.
                cls.env.ref('base.group_allow_export').id,
                cls.env.ref('odooapp_access_management.group_aam_manager').id,
            ])],
        })

        # No properties fixture here on Odoo 18. `res.partner` has no
        # `properties` field at all - it comes from `properties.base.definition.mixin`,
        # which is v19-only - so the properties coverage lives in
        # TestAamToursProperties below, on `project.task.task_properties`.

        cls.partner = cls.env['res.partner'].create({
            'name': 'AAM Tour Contact',
            'is_company': True,
            'email': 'tour@example.com',
            'website': 'https://example.com',
        })

        # A favourite every user sees (no action, no users), so both halves of
        # the differential pair have one to open. Without it the favourites
        # menu holds no item and "the edit icon is gone" would pass vacuously.
        cls.env['ir.filters'].create({
            'name': 'AAM Tour Favourite',
            'model_id': 'res.partner',
            'domain': "[('email', '!=', False)]",
        })

        partner_model = cls.env['ir.model']._get('res.partner').id
        cls.rule = cls.env['aam.rule'].create({
            'name': 'AAM Tour Restrictions',
            'target_type': 'user',
            'user_ids': [Command.set(cls.operator.ids)],
            'enforcement': 'enforced',
            # Each line leaves a neighbouring control alone, so the tour's
            # negative assertions all have a positive anchor beside them.
            'hide_add_property': True,
            'menu_line_ids': [Command.create({
                'menu_id': cls.env.ref(
                    'odooapp_access_management.menu_aam_reporting').id,
                'include_children': True,
            })],
            'model_line_ids': [Command.create({
                'model_id': partner_model,
                'hide_export': True,
                'hide_duplicate': True,
            })],
            'field_line_ids': [Command.create({
                'model_id': partner_model,
                'field_id': cls.env['ir.model.fields']._get(
                    'res.partner', 'website').id,
                'invisible': True,
            })],
            'search_line_ids': [Command.create({
                'model_id': partner_model,
                'hide_all_groupby': True,
                'hide_custom_filter': True,
                'hide_delete_filter': True,
            })],
            'chatter_line_ids': [Command.create({
                'model_id': partner_model,
                'hide_log_note': True,
            })],
        })

        # A second user whose whole cog menu is switched off. Separate from
        # `operator`, whose rule deliberately leaves the menu up so its Archive
        # entry can anchor the "Export is gone" assertion.
        cls.no_cog_user = cls.env['res.users'].create({
            'name': 'AAM Tour No-Cog',
            'login': 'aam_tour_nocog',
            'password': 'aam_tour_nocog',
            'groups_id': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('base.group_partner_manager').id,
                cls.env.ref('base.group_allow_export').id,
            ])],
        })
        cls.env['aam.rule'].create({
            'name': 'AAM Tour No Cog Menu',
            'target_type': 'user',
            'user_ids': [Command.set(cls.no_cog_user.ids)],
            'enforcement': 'enforced',
            'model_line_ids': [Command.create({
                'model_id': partner_model,
                'hide_action_button': True,
            })],
        })
        # Bind a report to Contacts so the no-cog tour means something. Without
        # one the assertion passed on a model whose cog only ever held Action
        # entries, and missed that `hide_action_button` left the menu on screen
        # wherever a report existed - which is how it behaved on `mrp.bom`.
        cls.env['ir.actions.report'].create({
            'name': 'AAM Tour Report',
            'model': 'res.partner',
            'report_type': 'qweb-pdf',
            'report_name': 'odooapp_access_management.aam_tour_report',
            'binding_model_id': partner_model,
            'binding_type': 'report',
        })

        # A profile with a rule of its own, for the configuration screens.
        cls.profile = cls.env['aam.profile'].create({
            'name': 'AAM Tour Profile',
            'description': 'Seeded by the browser tours.',
            'rule_ids': [Command.create({
                'name': 'AAM Tour Profile Rule',
                'target_type': 'profile',
                'readonly_user': True,
            })],
        })
        cls.blocked_profile = cls.env['aam.profile'].create({
            'name': 'AAM Tour Blocked Profile',
            'description': 'Blocked, to prove the badge renders.',
            'active': False,
        })

        cls.env.registry.clear_cache('groups')
        cls.env.registry.clear_cache()

    # -- screens ------------------------------------------------------------

    def test_dashboard(self):
        self.start_tour('/odoo', 'aam_dashboard_tour', login='admin')

    def test_access_map_and_explainer(self):
        self.start_tour('/odoo', 'aam_access_map_tour', login='admin')

    def test_config_screens(self):
        self.start_tour('/odoo', 'aam_config_tour', login='admin')

    # -- the two halves of the differential pair ----------------------------

    def test_core_views_unrestricted(self):
        """Core views still render with our template extensions loaded."""
        self.start_tour('/odoo', 'aam_core_views_tour', login='admin')

    def test_restricted_ui(self):
        """The same views, seen through a policy - the client-side half."""
        self.start_tour('/odoo', 'aam_restricted_tour', login='aam_tour_operator')

    def test_cog_menu_can_be_hidden_entirely(self):
        """B9/H8 takes the whole menu, not just the bound toolbar actions."""
        self.start_tour('/odoo', 'aam_no_cog_tour', login='aam_tour_nocog')


@tagged('post_install', '-at_install')
class TestAamToursEnterprise(ChromeSpawnTolerance, HttpCase):
    """Enterprise-only coverage.

    Insert-in-Spreadsheet is a cogMenu item from `spreadsheet_edition`, so it
    cannot be exercised on Community at all - which is how the gate came to
    reference three registry keys that do not exist. Skipped cleanly when the
    Enterprise apps are not installed, so the same suite still runs on CE.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.documents_user = cls.env.ref('documents.group_documents_user',
                                         raise_if_not_found=False)
        if not cls.documents_user:
            return

        # Onboarding tours hijack the browser before ours gets to run.
        # `tour_enabled` computes to True for an admin whenever the database has
        # no demo modules (web_tour/models/res_users.py:13) - and these dev
        # databases are deliberately demo-free, to match the Odoo 19 pair. With
        # `project` installed, `project_tour` then clicks into the Project app
        # the moment the page loads and every admin tour times out on its first
        # step. Disabled for everyone, so a module added later cannot
        # reintroduce it.
        cls.env['res.users'].sudo().search([]).tour_enabled = False

        cls.env['ir.config_parameter'].sudo().set_param('aam.enabled', '1')
        cls.env['ir.config_parameter'].sudo().set_param('aam.allow_restrict_admin', '0')

        # `session.can_insert_in_spreadsheet` is what actually puts the entry in
        # the menu, and `documents_spreadsheet` ties it to this group. Both the
        # unrestricted and the restricted user need it, or the negative
        # assertion passes for the wrong reason.
        cls.env.ref('base.user_admin').sudo().groups_id += cls.documents_user

        cls.operator = cls.env['res.users'].create({
            'name': 'AAM Spreadsheet Operator',
            'login': 'aam_ss_operator',
            'password': 'aam_ss_operator',
            'groups_id': [Command.set([
                cls.env.ref('base.group_user').id,
                cls.env.ref('base.group_partner_manager').id,
                cls.documents_user.id,
            ])],
        })
        cls.env['res.partner'].create({'name': 'AAM Spreadsheet Contact'})

        cls.env['aam.rule'].create({
            'name': 'AAM Spreadsheet Restriction',
            'target_type': 'user',
            'user_ids': [Command.set(cls.operator.ids)],
            'enforcement': 'enforced',
            'model_line_ids': [Command.create({
                'model_id': cls.env['ir.model']._get('res.partner').id,
                # Export deliberately left alone: it is the positive anchor the
                # restricted tour checks alongside the missing entry.
                'hide_spreadsheet': True,
            })],
        })
        cls.env.registry.clear_cache('groups')
        cls.env.registry.clear_cache()

    def setUp(self):
        super().setUp()
        if not self.documents_user:
            self.skipTest("Enterprise spreadsheet apps are not installed")

    def test_spreadsheet_entry_is_offered(self):
        self.start_tour('/odoo', 'aam_spreadsheet_tour', login='admin')

    def test_spreadsheet_entry_is_hidden(self):
        self.start_tour('/odoo', 'aam_spreadsheet_restricted_tour',
                        login='aam_ss_operator')


@tagged('post_install', '-at_install')
class TestAamToursProperties(ChromeSpawnTolerance, HttpCase):
    """`web.PropertiesField` coverage, on a model that has one.

    Odoo 18's `res.partner` carries no `properties` field - it comes from
    `properties.base.definition.mixin`, which is v19-only - so this cannot ride
    along in the core-views tour the way it does on the 19 branch. `project.task`
    has `task_properties` (project/models/project_task.py:188) and ships in both
    Community and Enterprise.

    Guarded rather than assumed: `project` is installed in both dev databases on
    purpose, but a customer database need not have it, and a tour that silently
    skips is worse than one that is honestly absent.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.has_project = 'project.task' in cls.env
        if not cls.has_project:
            return

        # Onboarding tours hijack the browser before ours gets to run.
        # `tour_enabled` computes to True for an admin whenever the database has
        # no demo modules (web_tour/models/res_users.py:13) - and these dev
        # databases are deliberately demo-free, to match the Odoo 19 pair. With
        # `project` installed, `project_tour` then clicks into the Project app
        # the moment the page loads and every admin tour times out on its first
        # step. Disabled for everyone, so a module added later cannot
        # reintroduce it.
        cls.env['res.users'].sudo().search([]).tour_enabled = False

        cls.env['ir.config_parameter'].sudo().set_param('aam.enabled', '1')
        cls.env['ir.config_parameter'].sudo().set_param('aam.allow_restrict_admin', '0')

        project_group = cls.env.ref('project.group_project_user')
        cls.operator = cls.env['res.users'].create({
            'name': 'AAM Properties Operator',
            'login': 'aam_prop_operator',
            'password': 'aam_prop_operator',
            'email': 'aam_prop_operator@example.com',
            'groups_id': [Command.set([
                cls.env.ref('base.group_user').id,
                project_group.id,
            ])],
        })

        # With no property defined the widget collapses to a zero-height div, and
        # a tour cannot assert on what it cannot see. The definition lives on the
        # project, not the task.
        cls.project = cls.env['project.project'].create({
            'name': 'AAM Tour Project',
            'task_properties_definition': [{
                'name': 'aam_tour_prop',
                'string': 'Tour Property',
                'type': 'char',
            }],
        })
        cls.task = cls.env['project.task'].create({
            'name': 'AAM Tour Task',
            'project_id': cls.project.id,
            'user_ids': [Command.set(cls.operator.ids)],
            'task_properties': {'aam_tour_prop': 'set'},
        })

        cls.env['aam.rule'].create({
            'name': 'AAM Properties Restriction',
            'target_type': 'user',
            'user_ids': [Command.set(cls.operator.ids)],
            'enforcement': 'enforced',
            'hide_add_property': True,
        })
        cls.env.registry.clear_cache('groups')
        cls.env.registry.clear_cache()

    def setUp(self):
        super().setUp()
        if not self.has_project:
            self.skipTest("`project` is not installed, so there is no properties host")

    def test_properties_widget_renders(self):
        """The `t-inherit` on web.PropertiesField still applies to core."""
        self.start_tour('/odoo', 'aam_properties_tour', login='admin')

    def test_add_property_control_is_hidden(self):
        """H6 removes the control while the properties keep working."""
        self.start_tour('/odoo', 'aam_properties_restricted_tour',
                        login='aam_prop_operator')
