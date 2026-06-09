/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ProjectTaskStateSelection } from "@project/components/project_task_state_selection/project_task_state_selection";

patch(ProjectTaskStateSelection.prototype, {
    setup() {
        super.setup(...arguments);
        this.icons["05_blocked"] = "fa fa-lg fa-ban";
        this.colorIcons["05_blocked"] = "text-danger";
        this.colorButton["05_blocked"] = "btn-outline-danger";
    },

    get options() {
        const labels = new Map(super.options);
        const states = ["1_canceled", "1_done"];
        const currentState = this.props.record.data[this.props.name];
        if (currentState !== "04_waiting_normal") {
            states.unshift("01_in_progress", "02_changes_requested", "03_approved", "05_blocked");
        } else {
            states.unshift("05_blocked");
        }
        return states
            .filter((state, index, arr) => arr.indexOf(state) === index)
            .map((state) => [state, labels.get(state) || (state === "05_blocked" ? _t("Blocked") : state)]);
    },
});
