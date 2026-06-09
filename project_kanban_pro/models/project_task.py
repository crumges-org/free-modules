from ast import literal_eval
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


KANBAN_STATE_META = {
    "blocked": {"label": "Blocked", "color": "blocked"},
    "overdue": {"label": "Overdue", "color": "overdue"},
    "at_risk": {"label": "At Risk", "color": "at_risk"},
    "on_track": {"label": "On Track", "color": "on_track"},
}
KANBAN_COLOR_INDEX = {
    "blocked": 1,
    "overdue": 2,
    "at_risk": 3,
    "on_track": 10,
}
BLOCKED_TASK_STATES = ("04_waiting_normal", "05_blocked")
CLOSED_TASK_STATES = ("1_done", "1_canceled")
PRIORITY_SEQUENCE = ["highest", "high", "medium", "low"]


class ProjectTask(models.Model):
    _inherit = "project.task"

    state = fields.Selection(
        selection_add=[("05_blocked", "Blocked")],
        ondelete={"05_blocked": "set default"},
    )

    priority_level = fields.Selection(
        selection=[
            ("highest", "Highest"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ],
        default="medium",
        required=True,
        index=True,
        tracking=True,
    )
    blocked_reason = fields.Text(tracking=True)
    last_stage_change_date = fields.Datetime(
        copy=False,
        default=fields.Datetime.now,
        tracking=True,
    )
    aging_days = fields.Integer(compute="_compute_aging")
    last_activity_date = fields.Datetime(
        compute="_compute_last_activity_date",
        search="_search_last_activity_date",
    )
    stale_days = fields.Integer(compute="_compute_status_flags")
    kanban_state_color = fields.Selection(
        selection=[
            ("blocked", "Blocked"),
            ("overdue", "Overdue"),
            ("at_risk", "At Risk"),
            ("on_track", "On Track"),
        ],
        compute="_compute_kanban_state",
    )
    kanban_state_label = fields.Char(compute="_compute_kanban_state")
    user_task_count = fields.Integer(compute="_compute_workload")
    user_workload_data = fields.Json(compute="_compute_workload")
    workload_state = fields.Selection(
        selection=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        compute="_compute_workload",
    )
    is_blocked = fields.Boolean(compute="_compute_status_flags", search="_search_is_blocked")
    is_overdue = fields.Boolean(compute="_compute_status_flags", search="_search_is_overdue")
    is_at_risk = fields.Boolean(compute="_compute_status_flags", search="_search_is_at_risk")
    is_stale = fields.Boolean(compute="_compute_status_flags", search="_search_is_stale")
    is_aging_alert = fields.Boolean(compute="_compute_status_flags")

    @api.model
    def _kanban_pro_aging_threshold(self):
        return int(self.env["ir.config_parameter"].sudo().get_param("project_kanban_pro.aging_days", 3))

    @api.model
    def _kanban_pro_stale_threshold(self):
        return int(self.env["ir.config_parameter"].sudo().get_param("project_kanban_pro.stale_days", 5))

    @api.model
    def _kanban_pro_risk_deadline_threshold(self):
        return int(self.env["ir.config_parameter"].sudo().get_param("project_kanban_pro.risk_deadline_days", 2))

    @api.model
    def _kanban_pro_workload_state(self, count):
        if count >= 8:
            return "high"
        if count >= 4:
            return "medium"
        return "low"

    def _kanban_pro_get_status_data(self):
        now = fields.Datetime.now()
        aging_threshold = self._kanban_pro_aging_threshold()
        stale_threshold = self._kanban_pro_stale_threshold()
        deadline_threshold = self._kanban_pro_risk_deadline_threshold()
        limit_deadline = now + timedelta(days=deadline_threshold)
        result = {}
        for task in self:
            last_stage_change = task.last_stage_change_date or task.create_date or now
            aging_days = max((now - last_stage_change).days, 0)
            last_activity = task.write_date or task.create_date or now
            stale_days = max((now - last_activity).days, 0)
            blocked = bool(task.state in BLOCKED_TASK_STATES)
            overdue = bool(task.date_deadline and task.date_deadline < now and not task.is_closed)
            stale = stale_days >= stale_threshold
            aging_alert = aging_days > aging_threshold
            close_deadline = bool(
                task.date_deadline
                and not overdue
                and not task.is_closed
                and task.date_deadline <= limit_deadline
            )
            at_risk = bool(not blocked and not overdue and (close_deadline or aging_alert or stale))
            result[task.id] = {
                "aging_days": aging_days,
                "stale_days": stale_days,
                "blocked": blocked,
                "overdue": overdue,
                "stale": stale,
                "aging_alert": aging_alert,
                "at_risk": at_risk,
            }
        return result

    @api.depends("last_stage_change_date")
    def _compute_aging(self):
        status_data = self._kanban_pro_get_status_data()
        for task in self:
            task.aging_days = status_data.get(task.id, {}).get("aging_days", 0)

    @api.depends("write_date", "create_date")
    def _compute_last_activity_date(self):
        for task in self:
            task.last_activity_date = task.write_date or task.create_date

    @api.depends(
        "state",
        "date_deadline",
        "is_closed",
        "last_stage_change_date",
        "write_date",
        "create_date",
    )
    def _compute_status_flags(self):
        status_data = self._kanban_pro_get_status_data()
        for task in self:
            task_data = status_data.get(task.id, {})
            task.is_blocked = task_data.get("blocked", False)
            task.is_overdue = task_data.get("overdue", False)
            task.is_at_risk = task_data.get("at_risk", False)
            task.is_stale = task_data.get("stale", False)
            task.stale_days = task_data.get("stale_days", 0)
            task.is_aging_alert = task_data.get("aging_alert", False)

    @api.depends("user_ids", "is_closed")
    def _compute_workload(self):
        all_user_ids = self.mapped("user_ids").ids
        workload_map = {}
        if all_user_ids:
            groups = self.env["project.task"].read_group(
                [("user_ids", "in", all_user_ids), ("is_closed", "=", False)],
                ["user_ids"],
                ["user_ids"],
                lazy=False,
            )
            workload_map = {
                group["user_ids"][0]: group.get("user_ids_count", group.get("__count", 0))
                for group in groups
                if group.get("user_ids")
            }
        for task in self:
            task_map = {str(user.id): workload_map.get(user.id, 0) for user in task.user_ids}
            max_count = max(task_map.values(), default=0)
            task.user_workload_data = task_map
            task.user_task_count = max_count
            task.workload_state = self._kanban_pro_workload_state(max_count)

    @api.depends(
        "state",
        "date_deadline",
        "is_closed",
        "last_stage_change_date",
        "write_date",
        "create_date",
    )
    def _compute_kanban_state(self):
        status_data = self._kanban_pro_get_status_data()
        remaining = self
        rules = self.env["kanban.rule"].search(
            [
                ("active", "=", True),
                ("model_id.model", "=", "project.task"),
            ],
            order="priority asc, id asc",
        )
        for rule in rules:
            try:
                domain = literal_eval(rule.domain or "[]")
            except (ValueError, SyntaxError):
                continue
            matched = remaining.filtered_domain(domain)
            for task in matched:
                task.kanban_state_color = rule.color
                task.kanban_state_label = rule.label
                task.color = KANBAN_COLOR_INDEX[rule.color]
            remaining -= matched
            if not remaining:
                break
        for task in remaining:
            task_data = status_data.get(task.id, {})
            if task_data.get("blocked"):
                state_key = "blocked"
            elif task_data.get("overdue"):
                state_key = "overdue"
            elif task_data.get("at_risk"):
                state_key = "at_risk"
            else:
                state_key = "on_track"
            task.kanban_state_color = KANBAN_STATE_META[state_key]["color"]
            task.kanban_state_label = _(KANBAN_STATE_META[state_key]["label"])
            task.color = KANBAN_COLOR_INDEX[state_key]

    @api.depends("stage_id", "depend_on_ids.state")
    def _compute_state(self):
        for task in self:
            dependent_open_tasks = []
            if task.allow_task_dependencies:
                dependent_open_tasks = [
                    dependent_task
                    for dependent_task in task.depend_on_ids
                    if dependent_task.state not in CLOSED_TASK_STATES
                ]
            if dependent_open_tasks:
                if task.state not in CLOSED_TASK_STATES and task.state != "05_blocked":
                    task.state = "04_waiting_normal"
            elif task.state not in CLOSED_TASK_STATES and task.state != "05_blocked":
                task.state = "01_in_progress"

    @api.model
    def _search_last_activity_date(self, operator, value):
        return [("write_date", operator, value)]

    @api.model
    def _search_is_blocked(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise ValidationError(_("Unsupported search for blocked filter."))
        domain = [("state", "in", list(BLOCKED_TASK_STATES))]
        return domain if value == (operator == "=") else ['!'] + domain

    @api.model
    def _search_is_overdue(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise ValidationError(_("Unsupported search for overdue filter."))
        domain = [
            ("date_deadline", "!=", False),
            ("date_deadline", "<", fields.Datetime.now()),
            ("is_closed", "=", False),
        ]
        return domain if value == (operator == "=") else ['!'] + domain

    @api.model
    def _search_is_stale(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise ValidationError(_("Unsupported search for stale filter."))
        deadline = fields.Datetime.now() - timedelta(days=self._kanban_pro_stale_threshold())
        domain = [("write_date", "!=", False), ("write_date", "<=", deadline)]
        return domain if value == (operator == "=") else ['!'] + domain

    @api.model
    def _search_is_at_risk(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise ValidationError(_("Unsupported search for at risk filter."))
        now = fields.Datetime.now()
        aging_limit = now - timedelta(days=self._kanban_pro_aging_threshold())
        stale_limit = now - timedelta(days=self._kanban_pro_stale_threshold())
        deadline_limit = now + timedelta(days=self._kanban_pro_risk_deadline_threshold())
        blocked_domain = [("state", "in", list(BLOCKED_TASK_STATES))]
        overdue_domain = [
            ("date_deadline", "!=", False),
            ("date_deadline", "<", now),
            ("is_closed", "=", False),
        ]
        risky_signals = expression.OR(
            [
                [
                    ("date_deadline", "!=", False),
                    ("date_deadline", ">=", now),
                    ("date_deadline", "<=", deadline_limit),
                    ("is_closed", "=", False),
                ],
                [("last_stage_change_date", "!=", False), ("last_stage_change_date", "<=", aging_limit)],
                [("write_date", "!=", False), ("write_date", "<=", stale_limit)],
            ]
        )
        domain = expression.AND([['!'] + blocked_domain, ['!'] + overdue_domain, risky_signals])
        return domain if value == (operator == "=") else ['!'] + domain

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("last_stage_change_date", fields.Datetime.now())
        tasks = super().create(vals_list)
        tasks._kanban_pro_sync_color()
        return tasks

    def write(self, vals):
        vals = dict(vals)
        if "stage_id" in vals:
            vals["last_stage_change_date"] = fields.Datetime.now()
        if vals.get("state") != "05_blocked" and "blocked_reason" not in vals:
            vals["blocked_reason"] = False
        result = super().write(vals)
        if not self.env.context.get("skip_kanban_pro_color_sync"):
            self._kanban_pro_sync_color()
        return result

    def _kanban_pro_sync_color(self):
        for task in self:
            status_data = task._kanban_pro_get_status_data().get(task.id, {})
            if task.kanban_state_color:
                state_key = task.kanban_state_color
            elif status_data.get("blocked"):
                state_key = "blocked"
            elif status_data.get("overdue"):
                state_key = "overdue"
            elif status_data.get("at_risk"):
                state_key = "at_risk"
            else:
                state_key = "on_track"
            color = KANBAN_COLOR_INDEX[state_key]
            if task.color != color:
                super(ProjectTask, task.with_context(skip_kanban_pro_color_sync=True)).write({"color": color})

    def action_kanban_pro_toggle_blocked(self):
        for task in self:
            if task.state == "05_blocked":
                next_state = "04_waiting_normal" if task.is_blocked_by_dependences() else "01_in_progress"
                vals = {"state": next_state, "blocked_reason": False}
            else:
                vals = {"state": "05_blocked"}
                if not task.blocked_reason:
                    vals["blocked_reason"] = _("Blocked from Kanban")
            task.write(vals)
        return True

    def action_kanban_pro_cycle_priority(self):
        for task in self:
            current = task.priority_level or "medium"
            next_index = (PRIORITY_SEQUENCE.index(current) + 1) % len(PRIORITY_SEQUENCE)
            task.write({"priority_level": PRIORITY_SEQUENCE[next_index]})
        return True

    def action_kanban_pro_assign_me(self):
        user = self.env.user
        for task in self:
            if user in task.user_ids:
                task.write({"user_ids": [(3, user.id)]})
            else:
                task.write({"user_ids": [(4, user.id)]})
        return True

    def action_kanban_pro_move_to_next_stage(self):
        for task in self:
            if not task.project_id:
                continue
            stages = task.project_id.type_ids.sorted(key=lambda stage: (stage.sequence, stage.id))
            if not stages:
                continue
            try:
                current_index = stages.ids.index(task.stage_id.id)
            except ValueError:
                current_index = -1
            if current_index < len(stages) - 1:
                task.write({"stage_id": stages[current_index + 1].id})
        return True

    def action_kanban_pro_set_stage(self, stage_id):
        self.write({"stage_id": stage_id})
        return True

    def action_kanban_pro_assign_user(self, user_id):
        self.write({"user_ids": [(4, user_id)]})
        return True
