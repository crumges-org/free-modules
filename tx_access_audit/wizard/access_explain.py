# -*- coding: utf-8 -*-
"""Ask the question in the user's words: can this person do this, and why."""

from odoo import _, api, fields, models

from ..models.access_audit import OPERATIONS


class AccessExplain(models.TransientModel):
    _name = "tx.access.explain"
    _description = "Explain Access"

    user_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user,
        domain=[("share", "=", False)])
    model_id = fields.Many2one(
        "ir.model", required=True, domain=[("transient", "=", False)],
        help="The model to check. Access is granted per model, so this is the "
             "level Odoo actually decides at.")
    operation = fields.Selection(OPERATIONS, required=True, default="read")

    answer = fields.Text(readonly=True)
    allowed = fields.Boolean(readonly=True)
    direct_group_ids = fields.Many2many(
        "res.groups", "tx_explain_direct_rel", string="Groups On The User Form",
        readonly=True)
    inherited_group_ids = fields.Many2many(
        "res.groups", "tx_explain_inherited_rel",
        string="Groups Received Through Implication", readonly=True,
        help="Held because another group implies them. These are not shown on "
             "the user form and are the usual reason access is a surprise.")
    access_line_ids = fields.Many2many(
        "ir.model.access", string="Granting Access Lines", readonly=True)
    rule_ids = fields.Many2many("ir.rule", "tx_explain_rule_rel",
                                string="Record Rules Applied", readonly=True)
    records_total = fields.Integer(readonly=True)
    records_reachable = fields.Integer(readonly=True)

    @api.onchange("user_id", "model_id", "operation")
    def _onchange_explain(self):
        """Answer as the form is filled in - there is nothing to save here."""
        for wizard in self:
            if not wizard.user_id or not wizard.model_id:
                wizard.answer = False
                continue
            wizard._compute_answer()

    def _compute_answer(self):
        self.ensure_one()
        audit = self.env["tx.access.audit"]
        model_name = self.model_id.model
        data = audit.explain(self.user_id, model_name, self.operation)
        self.answer = audit.explain_text(self.user_id, model_name,
                                         self.operation)
        self.allowed = data["allowed"]
        self.direct_group_ids = audit.direct_groups(self.user_id)
        self.inherited_group_ids = audit.inherited_groups(self.user_id)
        self.access_line_ids = data["granted_by"] | data["granted_to_everyone"]
        self.rule_ids = data["global_rules"] | data["group_rules"]
        self.records_total = data["records_total"] or 0
        self.records_reachable = (data["records_reachable"]
                                  if data["records_reachable"] is not None
                                  else 0)

    def action_explain(self):
        """Recompute and keep the wizard open."""
        self.ensure_one()
        self._compute_answer()
        return {"type": "ir.actions.act_window", "res_model": self._name,
                "res_id": self.id, "view_mode": "form", "target": "new"}
