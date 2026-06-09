/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { SearchModel } from "@web/search/search_model";

export class ProjectKanbanProSearchModel extends SearchModel {
    setup() {
        this.projectKanbanProFilters = {
            assignee: { userId: null, ids: [] },
            quick: { key: null, ids: [] },
        };
        super.setup(...arguments);
    }

    _dropDynamicFilters(ids) {
        if (!ids.length) {
            return;
        }
        this.query = this.query.filter((item) => !ids.includes(item.searchItemId));
        for (const id of ids) {
            delete this.searchItems[id];
        }
    }

    toggleAssigneeFilter(userId, userName) {
        if (this.projectKanbanProFilters.assignee.userId === userId) {
            this._dropDynamicFilters(this.projectKanbanProFilters.assignee.ids);
            this.projectKanbanProFilters.assignee = { userId: null, ids: [] };
            this._notify();
            return;
        }
        this._dropDynamicFilters(this.projectKanbanProFilters.assignee.ids);
        const nextId = this.nextId;
        this.projectKanbanProFilters.assignee = { userId, ids: [nextId] };
        this.createNewFilters([
            {
                description: `${_t("Assignee")}: ${userName}`,
                domain: [["user_ids", "in", userId]],
                invisible: "True",
                type: "filter",
            },
        ]);
    }

    toggleQuickFilter(key, filterDefinition) {
        if (this.projectKanbanProFilters.quick.key === key) {
            this._dropDynamicFilters(this.projectKanbanProFilters.quick.ids);
            this.projectKanbanProFilters.quick = { key: null, ids: [] };
            this._notify();
            return;
        }
        this._dropDynamicFilters(this.projectKanbanProFilters.quick.ids);
        const nextId = this.nextId;
        this.projectKanbanProFilters.quick = { key, ids: [nextId] };
        this.createNewFilters([
            {
                description: filterDefinition.label,
                domain: filterDefinition.domain,
                invisible: "True",
                type: "filter",
            },
        ]);
    }

    isQuickFilterActive(key) {
        return this.projectKanbanProFilters.quick.key === key;
    }

    isAssigneeFilterActive(userId) {
        return this.projectKanbanProFilters.assignee.userId === userId;
    }
}
