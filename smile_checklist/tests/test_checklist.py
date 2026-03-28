# -*- coding: utf-8 -*-
# (C) 2025 Smile (<http://www.smile.fr>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError
from lxml import etree
from odoo.tools import convert


class TestChecklist(TransactionCase):
    def setUp(self):
        super().setUp()
        convert.convert_file(self.env, 'smile_checklist', 'demo/checklist_demo.xml', None, mode='init', kind='data')
        self.Checklist = self.env["checklist"]
        self.Checklist.search([]).unlink()
        self.ChecklistTask = self.env["checklist.task"]
        self.ResPartner = self.env["res.partner"]
        self.IrActionsServer = self.env["ir.actions.server"]
        # Initialize the checklist and ensure hooks are registered
        self.checklist = self.Checklist.create(
            {
                "name": "Partner Checklist",
                "model_id": self.env.ref("base.model_res_partner").id,
            }
        )
        # Force register hooks after checklist creation
        self.Checklist._register_hook()
        self.checklist._update_models()
        # Create tasks after hook registration
        self.task_name = self.ChecklistTask.create(
            {
                "name": "Name Filled",
                "checklist_id": self.checklist.id,
                "complete_domain": "[('name', '!=', False)]",
            }
        )
        self.task_city = self.ChecklistTask.create(
            {
                "name": "City Filled",
                "checklist_id": self.checklist.id,
                "complete_domain": "[('city', '!=', False)]",
            }
        )
        self.task_country = self.ChecklistTask.create(
            {
                "name": "Country Filled",
                "checklist_id": self.checklist.id,
                "complete_domain": "[('country_id', '!=', False)]",
            }
        )
        # Create and assign server action
        self.server_action = self.IrActionsServer.create(
            {
                "name": "Add RSA Comment",
                "model_id": self.env.ref("base.model_res_partner").id,
                "state": "code",
                "code": 'record.write({"comment": "<p>RSA</p>"})',
            }
        )
        self.checklist.write({"action_id": self.server_action.id})
        # Load the views from the demo file
        self.form_view_with_checklist = self.env.ref(
            "smile_checklist.view_res_partner_form_with_checklist"
        )
        self.form_view_without_checklist = self.env.ref(
            "smile_checklist.view_res_partner_form_without_checklist"
        )
        self.list_view_with_checklist = self.env.ref(
            "smile_checklist.view_res_partner_list_with_checklist"
        )
        self.list_view_without_checklist = self.env.ref(
            "smile_checklist.view_res_partner_list_without_checklist"
        )
        # Load the actions from the demo file
        self.action_with_checklist = self.env.ref(
            "smile_checklist.action_res_partner_with_checklist"
        )
        self.action_without_checklist = self.env.ref(
            "smile_checklist.action_res_partner_without_checklist"
        )
        # Store the original view architecture
        self.original_arch_form_view_with_checklist = self.form_view_with_checklist.arch
        self.original_arch_form_view_without_checklist = (
            self.form_view_without_checklist.arch
        )

    def tearDown(self):
        # Reset the view architecture to its original state after each test
        self.form_view_with_checklist.write(
            {"arch": self.original_arch_form_view_with_checklist}
        )
        self.form_view_without_checklist.write(
            {"arch": self.original_arch_form_view_without_checklist}
        )
        self.env.registry.clear_cache()
        super().tearDown()

    def test_01_checklist_progress(self):
        # Create a new contact with only the name filled
        partner = self.ResPartner.create({"name": "Test Partner"})
        # Check that the checklist percentage is 33%
        self.assertEqual(
            partner.x_checklist_progress_rate,
            33.0,
            "Checklist progress should be 33% after filling the name",
        )
        # Fill the city in the same contact
        partner.write({"city": "Test City"})
        # Check that the checklist percentage is 67%
        self.assertEqual(
            partner.x_checklist_progress_rate,
            67.0,
            "Checklist progress should be 67% after filling the city",
        )
        # Empty the city
        partner.write({"city": False})
        # Check that the checklist percentage is 33%
        self.assertEqual(
            partner.x_checklist_progress_rate,
            33.0,
            "Checklist progress should be 33% after emptying the city",
        )
        # Fill the city and the country
        partner.write({"city": "Test City", "country_id": self.env.ref("base.us").id})
        # Check that the checklist percentage is now 100%
        self.assertEqual(
            partner.x_checklist_progress_rate,
            100.0,
            "Checklist progress should be 100% after filling the city" " and country",
        )
        # Check that the server action has been executed
        self.assertEqual(
            partner.comment,
            "<p>RSA</p>",
            "Server action should have added 'RSA' to the internal comment",
        )
        # Make the checklist condition mandatory for the partner to be active
        # Also test applied on filter at the same time
        self.task_city.write(
            {"mandatory": True, "filter_domain": [("id", "=", partner.id)]}
        )
        partner.write({"city": False})
        self.assertFalse(
            partner.active,
            "The partner is still active even if it does not fit "
            "the checklist condition.",
        )
        partner.write({"city": True})
        self.assertTrue(
            partner.active,
            "The partner is still active even if it does not fit "
            "the checklist condition.",
        )

    def test_02_checklist_uniqueness(self):
        with self.assertRaises(ValidationError):
            self.Checklist.create(
                {
                    "name": "Duplicate Partner Checklist",
                    "model_id": self.env.ref("base.model_res_partner").id,
                }
            )

    def test_03_checklist_button_visibility_on_views(self):
        # Associate the form view with the checklist
        self.checklist.write({"view_ids": [(6, 0, [self.form_view_with_checklist.id])]})
        # Test the button visibility in the associated form view
        res = self.env["res.partner"].get_view(
            view_id=self.form_view_with_checklist.id, view_type="form"
        )
        arch = etree.XML(res["arch"])
        button = arch.find(".//button[@name='open_checklist']")
        self.assertIsNotNone(
            button,
            "The checklist button should be present in the associated" " form view",
        )
        # Test the button visibility in a different form view
        res = self.env["res.partner"].get_view(
            view_id=self.form_view_without_checklist.id, view_type="form"
        )
        arch = etree.XML(res["arch"])
        button = arch.find(".//button[@name='open_checklist']")
        self.assertIsNone(
            button,
            "The checklist button should not be present in a different form" " view",
        )

    def test_04_checklist_button_visibility_on_menus_for_form_view(self):
        # Associate the checklist with the action and view
        self.checklist.write(
            {"act_window_ids": [(6, 0, [self.action_with_checklist.id])]}
        )
        # Retrieve the view using get_view with a matching view_id and
        # action_id
        view = self.env["res.partner"].get_view(
            view_id=self.form_view_with_checklist.id,
            view_type="form",
            action_id=self.action_with_checklist.id,
        )
        # Parse the view arch to check if the checklist button is added
        arch = etree.fromstring(view["arch"])
        button = arch.find(".//button[@name='open_checklist']")
        self.assertIsNotNone(
            button,
            "The checklist button should be present when the act_window_id "
            "and view_id match",
        )
        # Retrieve the view using get_view with a non-matching
        # act_window_id and view_id
        view = self.env["res.partner"].get_view(
            view_id=self.form_view_without_checklist.id,
            view_type="form",
            action_id=self.action_without_checklist.id,
        )
        # Parse the view arch to check if the checklist button is not added
        arch = etree.fromstring(view["arch"])
        button = arch.find(".//button[@name='open_checklist']")
        self.assertIsNone(
            button,
            "The checklist button should not be present when the"
            " act_window_id and view_id do not match",
        )

    def test_05_checklist_button_visibility_on_menus_for_list_view(self):
        # Associate the checklist with the action and view
        self.checklist.write(
            {"act_window_ids": [(6, 0, [self.action_with_checklist.id])]}
        )
        # Retrieve the view using get_view with a matching view_id and
        # action_id
        view = self.env["res.partner"].get_view(
            view_id=self.list_view_with_checklist.id,
            view_type="list",
            action_id=self.action_with_checklist.id,
        )
        # Parse the view arch to check if the checklist button is added
        arch = etree.fromstring(view["arch"])
        button = arch.find(".//field[@name='x_checklist_progress_rate']")
        self.assertIsNotNone(
            button,
            "The checklist button should be present when the act_window_id "
            "and view_id match",
        )
        # Retrieve the view using get_view with a non-matching
        # act_window_id and view_id
        view = self.env["res.partner"].get_view(
            view_id=self.list_view_without_checklist.id,
            view_type="list",
            action_id=self.action_without_checklist.id,
        )
        # Parse the view arch to check if the checklist button is not added
        arch = etree.fromstring(view["arch"])
        button = arch.find(".//field[@name='x_checklist_progress_rate']")
        self.assertIsNone(
            button,
            "The checklist button should not be present when the"
            " act_window_id and view_id do not match",
        )
