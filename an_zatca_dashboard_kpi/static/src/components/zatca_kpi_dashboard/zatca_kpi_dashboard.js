/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ZatcaKPIDashboard extends Component {
    static template = "an_zatca_dashboard_kpi.ZatcaKPIDashboard";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            isLoading: true,
            kpiData: {
                sent: 0,
                pending: 0,
                errors: 0,
                warnings: 0,
            },
        });

        onWillStart(async () => {
            await this.loadKPIData();
        });
    }

    async loadKPIData() {
        try {
            const data = await this.orm.call(
                "account.journal",
                "get_zatca_dashboard_kpi",
                []
            );
            this.state.kpiData = data;
        } catch (error) {
            console.error("Error loading ZATCA KPI data:", error);
        }
        this.state.isLoading = false;
    }

    async onKPIClick(type) {
        const action = await this.orm.call(
            "account.journal",
            "open_zatca_kpi_action",
            [type]
        );
        if (action) {
            this.action.doAction(action);
        }
    }
}
