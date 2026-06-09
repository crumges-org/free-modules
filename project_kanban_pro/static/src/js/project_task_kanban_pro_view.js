/** @odoo-module */

import { registry } from "@web/core/registry";
import { projectTaskKanbanView } from "@project/views/project_task_kanban/project_task_kanban_view";
import { ProjectTaskKanbanRenderer } from "@project/views/project_task_kanban/project_task_kanban_renderer";
import { ProjectKanbanProSearchModel } from "./project_task_kanban_pro_search_model";
import { ProjectKanbanProController } from "./project_task_kanban_pro_controller";
import { ProjectKanbanProRecord } from "./project_task_kanban_pro_record";

class ProjectKanbanProRenderer extends ProjectTaskKanbanRenderer {}

ProjectKanbanProRenderer.components = {
    ...ProjectTaskKanbanRenderer.components,
    KanbanRecord: ProjectKanbanProRecord,
};

export const projectKanbanProTaskKanbanView = {
    ...projectTaskKanbanView,
    SearchModel: ProjectKanbanProSearchModel,
    Controller: ProjectKanbanProController,
    Renderer: ProjectKanbanProRenderer,
    searchMenuTypes: ["filter", "groupBy", "favorite"],
};

registry.category("views").add("project_kanban_pro_task_kanban", projectKanbanProTaskKanbanView);
