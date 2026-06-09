from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KanbanRule(models.Model):
    _name = "kanban.rule"
    _description = "Kanban Rule"
    _order = "priority asc, id asc"

    name = fields.Char(required=True)
    model_id = fields.Many2one(
        "ir.model",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.ref("project.model_project_task", raise_if_not_found=False),
    )
    domain = fields.Text(required=True, default="[]")
    color = fields.Selection(
        selection=[
            ("blocked", "Blocked"),
            ("overdue", "Overdue"),
            ("at_risk", "At Risk"),
            ("on_track", "On Track"),
        ],
        required=True,
        default="on_track",
    )
    label = fields.Char(required=True)
    priority = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.constrains("domain")
    def _check_domain(self):
        for rule in self:
            try:
                domain = literal_eval(rule.domain or "[]")
            except (ValueError, SyntaxError) as exc:
                raise ValidationError(_("Invalid domain on kanban rule '%s'.") % rule.name) from exc
            if not isinstance(domain, (list, tuple)):
                raise ValidationError(_("Kanban rule domains must evaluate to a list or tuple."))
