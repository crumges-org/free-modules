import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ChecklistInstanceView extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            tasks: [],
        });
        this.res_model = this.props.action.context.res_model;
        this.res_id = this.props.action.context.res_id;
        onWillStart(async () => {
            await this.loadTasks();
        });
    }
    async loadTasks() {
        this.state.tasks = await this.orm.searchRead("checklist.task.instance", [
                ["task_id.checklist_id.model_id.model", "=", this.res_model],
                ["res_id", "=", this.res_id],
            ], ["name", "complete", "mandatory"]);

    }
}

ChecklistInstanceView.template = "ChecklistInstanceViewTemplate";

registry.category("actions").add("checklist_instance_view", ChecklistInstanceView);
