/** @odoo-module */

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { ProjectKanbanProQuickFilters } from "./project_task_kanban_pro_quick_filters";

export class ProjectKanbanProController extends KanbanController {}

ProjectKanbanProController.template = "project_kanban_pro.ProjectKanbanProKanbanView";
ProjectKanbanProController.components = {
    ...KanbanController.components,
    ProjectKanbanProQuickFilters,
};
