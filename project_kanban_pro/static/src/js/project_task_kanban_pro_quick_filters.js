/** @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useBus } from "@web/core/utils/hooks";

const QUICK_FILTERS = [
    { key: "my_tasks", label: _t("My Tasks"), domain: [["user_ids", "in", "__uid__"]] },
    { key: "blocked", label: _t("Blocked"), domain: [["is_blocked", "=", true]] },
    { key: "overdue", label: _t("Overdue"), domain: [["is_overdue", "=", true]] },
    { key: "at_risk", label: _t("At Risk"), domain: [["is_at_risk", "=", true]] },
    { key: "stale", label: _t("No Recent Activity"), domain: [["is_stale", "=", true]] },
];

export class ProjectKanbanProQuickFilters extends Component {
    static template = "project_kanban_pro.ProjectKanbanProQuickFilters";

    setup() {
        useBus(this.env.searchModel, "update", () => this.render());
    }

    get filters() {
        const uid = user.userId;
        return QUICK_FILTERS.map((filter) => ({
            ...filter,
            domain: filter.domain.map((term) =>
                term[2] === "__uid__" ? [term[0], term[1], uid] : term
            ),
            active: this.env.searchModel.isQuickFilterActive(filter.key),
        }));
    }

    toggleFilter(filter) {
        this.env.searchModel.toggleQuickFilter(filter.key, filter);
    }
}
