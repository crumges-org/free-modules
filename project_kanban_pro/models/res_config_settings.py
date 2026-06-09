from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    project_kanban_pro_aging_days = fields.Integer(
        string="Kanban Aging Alert Days",
        config_parameter="project_kanban_pro.aging_days",
        default=3,
    )
    project_kanban_pro_stale_days = fields.Integer(
        string="Kanban Stale Days",
        config_parameter="project_kanban_pro.stale_days",
        default=5,
    )
    project_kanban_pro_risk_deadline_days = fields.Integer(
        string="Kanban Risk Deadline Days",
        config_parameter="project_kanban_pro.risk_deadline_days",
        default=2,
    )
