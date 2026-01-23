/** @odoo-module **/

import { DashboardKanbanRenderer } from "@account/views/account_dashboard_kanban/account_dashboard_kanban_renderer";
import { ZatcaKPIDashboard } from "../../components/zatca_kpi_dashboard/zatca_kpi_dashboard";

export class ZatcaDashboardKanbanRenderer extends DashboardKanbanRenderer {
    static template = "an_zatca_dashboard_kpi.ZatcaDashboardKanbanRenderer";
    static components = {
        ...DashboardKanbanRenderer.components,
        ZatcaKPIDashboard,
    };
}
