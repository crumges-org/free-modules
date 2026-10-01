# -*- coding: utf-8 -*-
"""Read the access rules Odoo is actually enforcing, and explain them.

Odoo decides whether a user may touch a record in two separate layers, and
neither is legible from the user form. ``ir.model.access`` grants CRUD on a
model to a group; ``ir.rule`` then narrows *which records* of that model the
user sees, and rules attached to different groups are OR-ed together while
rules attached to no group apply to everyone and are AND-ed on top. Group
membership is itself transitive through ``implied_ids``.

Nothing here writes. This module reads those tables and reports what they mean,
so an administrator can answer "why can this person see this?" without reading
the source of every module installed.
"""

import logging

from odoo import _, api, models

_logger = logging.getLogger(__name__)

OPERATIONS = (
    ("read", "Read"),
    ("write", "Write"),
    ("create", "Create"),
    ("unlink", "Delete"),
)
PERM_FIELD = {"read": "perm_read", "write": "perm_write",
              "create": "perm_create", "unlink": "perm_unlink"}


class AccessAudit(models.AbstractModel):
    _name = "tx.access.audit"
    _description = "Access Rights Audit"

    # ------------------------------------------------------------------
    # group membership
    # ------------------------------------------------------------------
    @api.model
    def direct_groups(self, user):
        """Groups assigned to the user on the form.

        Odoo 19 renamed ``res.users.groups_id`` to ``group_ids``; asking the
        model which field it has keeps one implementation working on 16-19.
        """
        return user["group_ids" if "group_ids" in user._fields else "groups_id"]

    @api.model
    def effective_groups(self, user):
        """Every group a user really has, following implied_ids transitively.

        A user added to "Sales / Administrator" also holds "Sales / User" and
        whatever that implies. The direct list on the user form is therefore
        never the list the rules are evaluated against.

        Odoo 19 computes this itself as ``all_group_ids`` - the reflexive
        transitive closure, so it already contains the direct groups. Earlier
        versions have to walk ``implied_ids``, which is what that field does
        internally anyway.
        """
        if "all_group_ids" in user._fields:
            return user.all_group_ids
        seen = self.env["res.groups"]
        frontier = self.direct_groups(user)
        while frontier:
            seen |= frontier
            frontier = frontier.mapped("implied_ids") - seen
        return seen

    @api.model
    def effective_groups_of_group(self, group):
        """Everything holding ``group`` also grants, itself included.

        This is the chain that makes a mild-sounding group dangerous: the user
        form shows one entry, and implied_ids quietly adds the rest.
        """
        if "all_implied_ids" in group._fields:
            return group.all_implied_ids
        seen = self.env["res.groups"]
        frontier = group
        while frontier:
            seen |= frontier
            frontier = frontier.mapped("implied_ids") - seen
        return seen

    @api.model
    def inherited_groups(self, user):
        """Groups the user holds only through implication, never directly."""
        return self.effective_groups(user) - self.direct_groups(user)

    # ------------------------------------------------------------------
    # model-level access
    # ------------------------------------------------------------------
    @api.model
    def _access_lines(self, model_name):
        return self.env["ir.model.access"].sudo().search([
            ("model_id.model", "=", model_name),
        ])

    @api.model
    def explain_model_access(self, user, model_name, operation="read"):
        """Which ACL line grants ``operation`` on ``model_name`` to ``user``.

        Returns the granting lines, the lines that would have granted it to
        somebody else, and whether the model is unprotected - an ACL row with
        no group grants the operation to every logged-in user, which is the
        single most common accidental exposure.
        """
        perm = PERM_FIELD[operation]
        groups = self.effective_groups(user)
        granting = self.env["ir.model.access"]
        global_lines = self.env["ir.model.access"]
        other = self.env["ir.model.access"]
        for line in self._access_lines(model_name):
            if not line[perm]:
                continue
            if not line.group_id:
                global_lines |= line
            elif line.group_id in groups:
                granting |= line
            else:
                other |= line
        return {
            "allowed": bool(granting or global_lines),
            "granted_by": granting,
            "granted_to_everyone": global_lines,
            "would_grant_via": other,
        }

    # ------------------------------------------------------------------
    # record-level rules
    # ------------------------------------------------------------------
    @api.model
    def _rules(self, model_name, operation="read"):
        perm = PERM_FIELD[operation]
        return self.env["ir.rule"].sudo().search([
            ("model_id.model", "=", model_name),
            ("active", "=", True),
            (perm, "=", True),
        ])

    @api.model
    def explain_record_rules(self, user, model_name, operation="read"):
        """The record rules that apply to this user on this model.

        Global rules - those with no group - are restrictions everyone obeys
        and are AND-ed together. Group rules are permissions, OR-ed with each
        other, and a user holding none of their groups is not narrowed by them
        at all.
        """
        groups = self.effective_groups(user)
        global_rules = self.env["ir.rule"]
        applied = self.env["ir.rule"]
        ignored = self.env["ir.rule"]
        for rule in self._rules(model_name, operation):
            if not rule.groups:
                global_rules |= rule
            elif set(rule.groups.ids) & set(groups.ids):
                applied |= rule
            else:
                ignored |= rule
        return {
            "global_rules": global_rules,
            "group_rules": applied,
            "rules_for_other_groups": ignored,
        }

    # ------------------------------------------------------------------
    # the answer
    # ------------------------------------------------------------------
    @api.model
    def explain(self, user, model_name, operation="read"):
        """Full account of whether ``user`` may ``operation`` ``model_name``.

        ``reachable_ids`` is the honest part: rather than re-implementing
        Odoo's rule evaluation and risking a different answer, it asks Odoo
        itself, as that user, which records come back.
        """
        access = self.explain_model_access(user, model_name, operation)
        rules = self.explain_record_rules(user, model_name, operation)
        reachable = None
        total = None
        if access["allowed"] and model_name in self.env:
            model = self.env[model_name]
            total = model.sudo().search_count([])
            try:
                reachable = model.with_user(user).search_count([])
            except Exception:               # noqa: BLE001 - reported, not raised
                reachable = None
        return {
            "user": user.display_name,
            "model": model_name,
            "operation": operation,
            "allowed": access["allowed"],
            "granted_by": access["granted_by"],
            "granted_to_everyone": access["granted_to_everyone"],
            "would_grant_via": access["would_grant_via"],
            "global_rules": rules["global_rules"],
            "group_rules": rules["group_rules"],
            "rules_for_other_groups": rules["rules_for_other_groups"],
            "records_total": total,
            "records_reachable": reachable,
        }

    @api.model
    def explain_text(self, user, model_name, operation="read"):
        """The explanation as prose, for the wizard and the log."""
        data = self.explain(user, model_name, operation)
        label = dict(OPERATIONS).get(operation, operation)
        lines = []
        if not data["allowed"]:
            lines.append(_("%(user)s cannot %(op)s %(model)s: no access rule "
                           "grants it to any group they hold.")
                         % {"user": data["user"], "op": label.lower(),
                            "model": model_name})
            if data["would_grant_via"]:
                names = ", ".join(data["would_grant_via"].mapped(
                    "group_id.display_name"))
                lines.append(_("It would be granted by: %s.") % names)
            return "\n".join(lines)

        lines.append(_("%(user)s can %(op)s %(model)s.")
                     % {"user": data["user"], "op": label.lower(),
                        "model": model_name})
        if data["granted_to_everyone"]:
            lines.append(_(
                "This model is open to every logged-in user: %s has no group.")
                % ", ".join(data["granted_to_everyone"].mapped("name")))
        if data["granted_by"]:
            lines.append(_("Granted by: %s.") % ", ".join(
                "%s (via %s)" % (line.name, line.group_id.display_name)
                for line in data["granted_by"]))
        if data["global_rules"]:
            lines.append(_("Restricted for everyone by: %s.") % ", ".join(
                data["global_rules"].mapped("name")))
        if data["group_rules"]:
            lines.append(_("Widened by the group rules: %s.") % ", ".join(
                data["group_rules"].mapped("name")))
        if not data["global_rules"] and not data["group_rules"]:
            lines.append(_("No record rule applies, so every record of this "
                           "model is visible."))
        if data["records_reachable"] is not None:
            lines.append(_("%(reachable)s of %(total)s record(s) are reachable.")
                         % {"reachable": data["records_reachable"],
                            "total": data["records_total"]})
        return "\n".join(lines)
