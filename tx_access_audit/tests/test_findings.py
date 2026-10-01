# -*- coding: utf-8 -*-
"""The scan. Each test provokes one exposure and asserts it is reported."""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

# scan() logs the traceback of a check it then reports as a finding. That is
# right in production and pure noise here, where provoking the failure is the
# point of the test - and the install gate reads a logged ERROR as a failure.
SCAN_LOGGER = "odoo.addons.tx_access_audit.models.access_finding"


@tagged("post_install", "-at_install")
class TestFindings(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.finding = cls.env["tx.access.finding"]

    def _kinds(self):
        return set(self.finding.search([]).mapped("kind"))

    def _of_kind(self, kind):
        return self.finding.search([("kind", "=", kind)])

    def test_an_access_line_with_no_group_is_reported(self):
        model = self.env["ir.model"]._get("res.currency.rate")
        self.env["ir.model.access"].create({
            "name": "tx_test_open_to_everyone", "model_id": model.id,
            "group_id": False,
            "perm_read": True, "perm_write": True,
        })
        self.finding.scan()
        found = self._of_kind("acl_no_group").filtered(
            lambda f: f.model_name == "res.currency.rate")
        self.assertTrue(found)
        self.assertIn("write", found[0].title)

    def test_a_read_only_line_with_no_group_is_not_reported(self):
        model = self.env["ir.model"]._get("res.currency.rate")
        self.env["ir.model.access"].create({
            "name": "tx_test_public_read", "model_id": model.id,
            "group_id": False, "perm_read": True,
        })
        self.finding.scan()
        # Read for everyone is ordinary; only a write grant is worth a flag.
        found = self._of_kind("acl_no_group").filtered(
            lambda f: "tx_test_public_read" in (f.detail or ""))
        self.assertFalse(found)

    def test_a_grant_on_a_business_model_is_high_not_medium(self):
        model = self.env["ir.model"]._get("res.partner")
        self.env["ir.model.access"].create({
            "name": "tx_test_partner_open", "model_id": model.id,
            "group_id": False, "perm_read": True, "perm_unlink": True,
        })
        self.finding.scan()
        found = self._of_kind("acl_no_group").filtered(
            lambda f: f.model_name == "res.partner")
        self.assertTrue(found)
        self.assertEqual(found[0].severity, "high")

    def test_a_group_that_implies_settings_access_is_reported(self):
        admin = self.env.ref("base.group_system")
        trap = self.env["res.groups"].create({
            "name": "TX Looks Harmless", "implied_ids": [(6, 0, admin.ids)]})
        self.finding.scan()
        found = self._of_kind("implies_admin").filtered(
            lambda f: f.res_id == trap.id)
        self.assertTrue(found)
        self.assertEqual(found[0].severity, "high")

    def test_an_inactive_record_rule_is_reported(self):
        model = self.env["ir.model"]._get("res.partner")
        rule = self.env["ir.rule"].create({
            "name": "tx_test_switched_off", "model_id": model.id,
            "domain_force": "[('id', '=', 0)]", "active": False,
        })
        self.finding.scan()
        found = self._of_kind("rule_inactive").filtered(
            lambda f: f.res_id == rule.id)
        self.assertTrue(found)

    def test_every_finding_links_back_to_the_record_that_caused_it(self):
        model = self.env["ir.model"]._get("res.currency.rate")
        self.env["ir.model.access"].create({
            "name": "tx_test_traceable", "model_id": model.id,
            "group_id": False, "perm_read": True, "perm_create": True,
        })
        self.finding.scan()
        # A finding nobody can act on is noise; the source record is the fix.
        for found in self.finding.search([("kind", "!=", "check_failed")]):
            self.assertTrue(found.res_model, found.title)
            self.assertTrue(found.res_id, found.title)

    def test_a_rescan_replaces_the_previous_findings(self):
        self.finding.scan()
        first = self.finding.search([])
        self.finding.scan()
        second = self.finding.search([])
        self.assertFalse(set(first.ids) & set(second.ids))

    def test_the_scan_reports_who_holds_settings_access(self):
        self.env["res.users"].create({
            "name": "TX Extra Admin", "login": "tx_extra_admin",
            self._group_field(): [(6, 0, (
                self.env.ref("base.group_user")
                | self.env.ref("base.group_system")).ids)],
        })
        self.finding.scan()
        self.assertTrue(self._of_kind("admin_holders"))

    def _group_field(self):
        return ("group_ids" if "group_ids" in self.env["res.users"]._fields
                else "groups_id")

    def test_the_scan_never_writes_to_a_security_record(self):
        model = self.env["ir.model"]._get("res.partner")
        rule = self.env["ir.rule"].create({
            "name": "tx_test_untouched", "model_id": model.id,
            "domain_force": "[('id', '!=', 0)]", "active": False,
        })
        before = (rule.active, rule.domain_force, rule.name)
        self.finding.scan()
        rule.invalidate_recordset()
        # The whole promise of this module is that it reads and reports.
        self.assertEqual((rule.active, rule.domain_force, rule.name), before)

    @mute_logger(SCAN_LOGGER)
    def test_one_failing_check_does_not_lose_the_others(self):
        def boom(*args, **kwargs):
            raise ValueError("provoked")
        self.patch(type(self.finding), "_scan_inactive_rules", boom)
        self.finding.scan()
        kinds = self._kinds()
        self.assertIn("check_failed", kinds)
        self.assertNotIn("rule_inactive", kinds)
