# -*- coding: utf-8 -*-
"""The explainer, checked against what Odoo itself enforces."""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestExplain(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.audit = cls.env["tx.access.audit"]
        cls.leaf = cls.env["res.groups"].create({"name": "TX Leaf"})
        cls.middle = cls.env["res.groups"].create(
            {"name": "TX Middle", "implied_ids": [(6, 0, cls.leaf.ids)]})
        cls.top = cls.env["res.groups"].create(
            {"name": "TX Top", "implied_ids": [(6, 0, cls.middle.ids)]})
        cls.user = cls.env["res.users"].create({
            "name": "Audit Subject", "login": "tx_audit_subject",
            cls._group_field(): [(6, 0, (
                cls.env.ref("base.group_user") | cls.top).ids)],
        })

    @classmethod
    def _group_field(cls):
        """Odoo 19 renamed res.users.groups_id to group_ids."""
        return ("group_ids" if "group_ids" in cls.env["res.users"]._fields
                else "groups_id")

    # -- group closure ----------------------------------------------------
    def test_implied_groups_are_followed_all_the_way_down(self):
        groups = self.audit.effective_groups(self.user)
        # The user form shows only TX Top; the other two arrive by implication.
        self.assertIn(self.top, groups)
        self.assertIn(self.middle, groups)
        self.assertIn(self.leaf, groups)

    def test_inherited_groups_is_exactly_what_the_form_does_not_show(self):
        direct = self.audit.direct_groups(self.user)
        effective = self.audit.effective_groups(self.user)
        self.assertIn(self.top, direct)
        # Odoo 18 materialises implied groups into the user's own list on
        # assignment while other versions leave them implicit, so whether leaf
        # is "direct" is a storage detail that differs by version. What must
        # hold everywhere is that effective covers the whole chain and that
        # inherited is precisely the part the user form does not show.
        self.assertLessEqual(set(direct.ids), set(effective.ids))
        self.assertEqual(set(self.audit.inherited_groups(self.user).ids),
                         set(effective.ids) - set(direct.ids))

    def test_a_group_closure_includes_itself(self):
        closure = self.audit.effective_groups_of_group(self.top)
        self.assertIn(self.top, closure)
        self.assertIn(self.leaf, closure)

    def test_the_closure_survives_a_cycle(self):
        # implied_ids is user-editable, so a loop is possible and must not hang.
        self.leaf.implied_ids = [(6, 0, self.top.ids)]
        closure = self.audit.effective_groups_of_group(self.top)
        self.assertIn(self.leaf, closure)

    # -- model access -----------------------------------------------------
    def test_a_model_the_user_cannot_reach_is_reported_as_denied(self):
        result = self.audit.explain(self.user, "ir.model.access", "unlink")
        self.assertFalse(result["allowed"])
        text = self.audit.explain_text(self.user, "ir.model.access", "unlink")
        self.assertIn("cannot", text)

    def test_a_model_the_user_can_read_names_the_granting_line(self):
        result = self.audit.explain(self.user, "res.partner", "read")
        self.assertTrue(result["allowed"])
        self.assertTrue(result["granted_by"] or result["granted_to_everyone"])

    def test_the_explanation_says_which_group_would_grant_it(self):
        model = self.env["ir.model"]._get("res.currency.rate")
        self.env["ir.model.access"].create({
            "name": "tx_test_rate_delete",
            "model_id": model.id,
            "group_id": self.env.ref("base.group_system").id,
            "perm_read": True, "perm_unlink": True,
        })
        result = self.audit.explain(self.user, "res.currency.rate", "unlink")
        self.assertFalse(result["allowed"])
        self.assertIn(self.env.ref("base.group_system"),
                      result["would_grant_via"].mapped("group_id"))

    def test_reachable_count_comes_from_odoo_not_from_our_own_rule_engine(self):
        partner = self.env["res.partner"].create({"name": "Visible To All"})
        result = self.audit.explain(self.user, "res.partner", "read")
        # Asking Odoo as that user is the only answer that cannot drift from
        # what the ORM actually enforces.
        self.assertIsNotNone(result["records_reachable"])
        self.assertGreaterEqual(result["records_total"],
                                result["records_reachable"])
        self.assertTrue(
            self.env["res.partner"].with_user(self.user).browse(partner.id).exists())

    # -- record rules -----------------------------------------------------
    def test_a_global_rule_is_reported_separately_from_a_group_rule(self):
        model = self.env["ir.model"]._get("res.partner")
        global_rule = self.env["ir.rule"].create({
            "name": "tx_test_global", "model_id": model.id,
            "domain_force": "[('id', '!=', 0)]", "groups": [(6, 0, [])],
        })
        group_rule = self.env["ir.rule"].create({
            "name": "tx_test_group", "model_id": model.id,
            "domain_force": "[('id', '!=', 0)]", "groups": [(6, 0, self.top.ids)],
        })
        result = self.audit.explain_record_rules(self.user, "res.partner")
        self.assertIn(global_rule, result["global_rules"])
        self.assertIn(group_rule, result["group_rules"])

    def test_a_rule_for_a_group_the_user_lacks_is_not_applied(self):
        other = self.env["res.groups"].create({"name": "TX Unrelated"})
        model = self.env["ir.model"]._get("res.partner")
        rule = self.env["ir.rule"].create({
            "name": "tx_test_other", "model_id": model.id,
            "domain_force": "[('id', '=', 0)]", "groups": [(6, 0, other.ids)],
        })
        result = self.audit.explain_record_rules(self.user, "res.partner")
        self.assertIn(rule, result["rules_for_other_groups"])
        self.assertNotIn(rule, result["group_rules"])


@tagged("post_install", "-at_install")
class TestExplainWizard(TransactionCase):

    def test_the_wizard_answers_as_the_form_is_filled_in(self):
        wizard = self.env["tx.access.explain"].create({
            "user_id": self.env.user.id,
            "model_id": self.env["ir.model"]._get("res.partner").id,
            "operation": "read",
        })
        wizard._onchange_explain()
        self.assertTrue(wizard.answer)
        self.assertTrue(wizard.allowed)

    def test_an_incomplete_form_produces_no_answer(self):
        wizard = self.env["tx.access.explain"].new({
            "user_id": self.env.user.id, "operation": "read"})
        wizard._onchange_explain()
        self.assertFalse(wizard.answer)
