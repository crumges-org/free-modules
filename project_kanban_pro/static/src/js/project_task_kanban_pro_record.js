/** @odoo-module */

import { ProjectTaskKanbanRecord } from "@project/views/project_task_kanban/project_task_kanban_record";
import { useService } from "@web/core/utils/hooks";

export class ProjectKanbanProRecord extends ProjectTaskKanbanRecord {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    onGlobalClick(ev) {
        const quickAction = ev.target.closest("[data-quick-action]");
        if (quickAction) {
            ev.preventDefault();
            ev.stopPropagation();
            const action = quickAction.dataset.quickAction;
            if (action === "move_next_stage") {
                return this.moveToNextStage();
            }
            if (action === "assign_me") {
                return this.assignToMe();
            }
            if (action === "cycle_priority") {
                return this.cyclePriorityLevel();
            }
            return;
        }
        return super.onGlobalClick(ev);
    }

    async _runQuickAction(method, args = []) {
        await this.orm.call("project.task", method, [[this.props.record.resId], ...args]);
        await this.props.list.load();
    }

    async moveToNextStage() {
        await this._runQuickAction("action_kanban_pro_move_to_next_stage");
    }

    async assignToMe() {
        await this._runQuickAction("action_kanban_pro_assign_me");
    }

    async cyclePriorityLevel() {
        await this._runQuickAction("action_kanban_pro_cycle_priority");
    }
}
