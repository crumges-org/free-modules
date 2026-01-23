/** @odoo-module **/

import { AccountMoveListRenderer } from "@account/views/account_move_list/account_move_list_renderer";
import { ZatcaKPIDashboard } from "../../components/zatca_kpi_dashboard/zatca_kpi_dashboard";

export class ZatcaAccountTreeRenderer extends AccountMoveListRenderer {
    static template = "an_zatca_dashboard_kpi.ZatcaAccountTreeRenderer";
    static components = {
        ...AccountMoveListRenderer.components,
        ZatcaKPIDashboard,
    };
}
