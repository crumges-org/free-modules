/** @odoo-module **/

import { registry } from "@web/core/registry";
import { accountDashboardKanbanView } from "@account/views/account_dashboard_kanban/account_dashboard_kanban_view";
import { ZatcaDashboardKanbanRenderer } from "./zatca_dashboard_kanban_renderer";

export const zatcaDashboardKanbanView = {
    ...accountDashboardKanbanView,
    Renderer: ZatcaDashboardKanbanRenderer,
};

// Replace the existing account_dashboard_kanban view
registry.category("views").add("account_dashboard_kanban", zatcaDashboardKanbanView, { force: true });
