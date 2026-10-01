# -*- coding: utf-8 -*-
"""The scan: exposures that are easy to create and impossible to see.

Every finding here is a fact read off ``ir.model.access`` and ``ir.rule``, not
a judgement about how a business should be run. A finding is a prompt to go and
look, which is why each one records the exact record that produced it.
"""

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

SEVERITIES = [("high", "High"), ("medium", "Medium"), ("low", "Low")]

# Models whose rows are the business itself. An unrestricted grant on these is
# worth reporting even though the same grant on a technical model is routine.
SENSITIVE_MODELS = (
    "res.partner", "res.users", "account.move", "account.move.line",
    "account.payment", "account.journal", "hr.employee", "hr.contract",
    "hr.payslip", "sale.order", "purchase.order", "product.template",
    "product.product", "stock.quant", "crm.lead", "res.company",
)


class AccessFinding(models.Model):
    _name = "tx.access.finding"
    _description = "Access Rights Finding"
    _order = "severity, model_name, id"
    _rec_name = "title"

    title = fields.Char(required=True, readonly=True)
    severity = fields.Selection(SEVERITIES, required=True, readonly=True,
                                index=True)
    kind = fields.Char(required=True, readonly=True, index=True)
    model_name = fields.Char("Odoo Model", readonly=True, index=True)
    detail = fields.Text(readonly=True)
    res_model = fields.Char("Source Record Model", readonly=True)
    res_id = fields.Integer("Source Record", readonly=True)
    scanned_on = fields.Datetime(readonly=True, default=fields.Datetime.now)

    def action_open_source(self):
        """Open the ACL line, rule or group that produced this finding."""
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {"type": "ir.actions.act_window", "res_model": self.res_model,
                "res_id": self.res_id, "view_mode": "form"}

    # ------------------------------------------------------------------
    # the scan
    # ------------------------------------------------------------------
    @api.model
    def _finding(self, kind, severity, title, detail, model_name="",
                 record=None):
        return {
            "kind": kind,
            "severity": severity,
            "title": title,
            "detail": detail,
            "model_name": model_name,
            "res_model": record._name if record is not None else False,
            "res_id": record.id if record is not None else False,
        }

    @api.model
    def _scan_ungrouped_acls(self):
        """ACL lines with no group grant the operation to every logged-in user."""
        out = []
        lines = self.env["ir.model.access"].sudo().search([
            ("group_id", "=", False), ("active", "=", True),
        ])
        for line in lines:
            model_name = line.model_id.model
            writes = [label for perm, label in (
                ("perm_write", "write"), ("perm_create", "create"),
                ("perm_unlink", "delete")) if line[perm]]
            if not writes:
                continue
            sensitive = model_name in SENSITIVE_MODELS
            out.append(self._finding(
                "acl_no_group", "high" if sensitive else "medium",
                _("%(model)s: %(ops)s allowed for every user")
                % {"model": model_name, "ops": ", ".join(writes)},
                _("The access line '%(line)s' has no group, so every "
                  "logged-in user may %(ops)s records of %(model)s. An access "
                  "line without a group is a grant to everyone, not a "
                  "placeholder.")
                % {"line": line.name, "ops": ", ".join(writes),
                   "model": model_name},
                model_name, line))
        return out

    @api.model
    def _scan_unrestricted_delete(self):
        """Delete rights on a business model with no record rule to narrow them."""
        out = []
        lines = self.env["ir.model.access"].sudo().search([
            ("perm_unlink", "=", True), ("active", "=", True),
        ])
        for line in lines:
            model_name = line.model_id.model
            if model_name not in SENSITIVE_MODELS:
                continue
            rules = self.env["ir.rule"].sudo().search_count([
                ("model_id", "=", line.model_id.id), ("active", "=", True),
                ("perm_unlink", "=", True),
            ])
            if rules:
                continue
            out.append(self._finding(
                "delete_no_rule", "medium",
                _("%s: delete is not narrowed by any record rule") % model_name,
                _("'%(line)s' grants delete on %(model)s to %(group)s, and no "
                  "active record rule limits which records that covers. "
                  "Deleting a business record is rarely reversible.")
                % {"line": line.name, "model": model_name,
                   "group": line.group_id.display_name or _("everyone")},
                model_name, line))
        return out

    @api.model
    def _scan_missing_company_rules(self):
        """Multi-company models with no company rule leak across companies."""
        out = []
        if self.env["res.company"].sudo().search_count([]) < 2:
            return out
        rule_model = self.env["ir.rule"].sudo()
        for model_name in SENSITIVE_MODELS:
            if model_name not in self.env:
                continue
            model = self.env[model_name]
            if "company_id" not in model._fields:
                continue
            record = self.env["ir.model"].sudo()._get(model_name)
            if not record:
                continue
            has_company_rule = rule_model.search_count([
                ("model_id", "=", record.id), ("active", "=", True),
                ("domain_force", "like", "company"),
            ])
            if has_company_rule:
                continue
            out.append(self._finding(
                "no_company_rule", "high",
                _("%s: no record rule mentions the company") % model_name,
                _("This database has more than one company and %s carries a "
                  "company field, but no active record rule filters on it. "
                  "Users may be seeing another company's records.")
                % model_name,
                model_name, record))
        return out

    @api.model
    def _scan_groups_implying_admin(self):
        """Ordinary-looking groups that transitively grant Settings access."""
        out = []
        admin = self.env.ref("base.group_system", raise_if_not_found=False)
        if not admin:
            return out
        audit = self.env["tx.access.audit"]
        for group in self.env["res.groups"].sudo().search([]):
            if group == admin:
                continue
            closure = audit.effective_groups_of_group(group)
            if admin not in closure:
                continue
            out.append(self._finding(
                "implies_admin", "high",
                _("%s implies Settings access") % group.display_name,
                _("A user given '%s' silently receives full Settings rights "
                  "through the implied-groups chain, which is not visible on "
                  "the user form.") % group.display_name,
                "res.groups", group))
        return out

    @api.model
    def _scan_users_with_admin(self):
        """Who actually holds Settings access, counting implied groups."""
        out = []
        admin = self.env.ref("base.group_system", raise_if_not_found=False)
        if not admin:
            return out
        audit = self.env["tx.access.audit"]
        holders = self.env["res.users"]
        for user in self.env["res.users"].sudo().search(
                [("active", "=", True), ("share", "=", False)]):
            if admin in audit.effective_groups(user):
                holders |= user
        if len(holders) <= 1:
            return out
        indirect = holders.filtered(
            lambda u: admin not in audit.direct_groups(u))
        out.append(self._finding(
            "admin_holders", "medium" if indirect else "low",
            _("%d user(s) hold Settings access") % len(holders),
            _("Settings access: %(names)s.%(extra)s")
            % {"names": ", ".join(holders.mapped("display_name")),
               "extra": (_(" %s hold it only through an implied group, so it "
                           "is not shown on their user form.")
                         % ", ".join(indirect.mapped("display_name")))
                        if indirect else ""},
            "res.users", holders[:1]))
        return out

    @api.model
    def _scan_inactive_rules(self):
        """Record rules switched off - a restriction that no longer restricts."""
        out = []
        for rule in self.env["ir.rule"].sudo().search([("active", "=", False)]):
            out.append(self._finding(
                "rule_inactive", "medium",
                _("Record rule '%s' is inactive") % rule.name,
                _("This rule was written to limit access to %s and is "
                  "switched off, so it limits nothing. An inactive rule is "
                  "easy to miss because it does not appear in the default "
                  "rule list.") % (rule.model_id.model or ""),
                rule.model_id.model or "", rule))
        return out

    @api.model
    def scan(self):
        """Run every check and replace the previous findings."""
        self.sudo().search([]).unlink()
        findings = []
        for check in (self._scan_ungrouped_acls,
                      self._scan_unrestricted_delete,
                      self._scan_missing_company_rules,
                      self._scan_groups_implying_admin,
                      self._scan_users_with_admin,
                      self._scan_inactive_rules):
            try:
                findings.extend(check())
            except Exception as exc:        # noqa: BLE001 - one check, not all
                _logger.exception("Access audit check %s failed",
                                  check.__name__)
                findings.append(self._finding(
                    "check_failed", "low",
                    _("A check could not run: %s") % check.__name__, str(exc)))
        return self.sudo().create(findings)

    @api.model
    def action_scan(self):
        """Rescan and show the result."""
        self.scan()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "tx_access_audit.action_tx_access_finding")
        return action
