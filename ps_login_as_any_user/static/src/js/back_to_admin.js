/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";   // <-- Use global rpc()
import { useService } from "@web/core/utils/hooks";

export class AdminSwitchWidget extends Component {
    setup() {
        super.setup();

        // Remove: this.rpc = useService("rpc");  <-- NOT ALLOWED IN ODOO 18 SYSTRAY

        this.action = useService("action");
        this.state = useState({ hasAccess: false });

        onWillStart(async () => {
            this.state.hasAccess = await checkAdminAccess();
        });
    }

    async _onClick() {
        await rpc("/switch/admin", {});   // <-- DIRECT rpc()
        location.reload();
    }
}


async function checkAdminAccess() {
    const result = await rpc("/web/dataset/call_kw", {
        model: "res.users",
        method: "check_previous_admin_access",
        args: [],
        kwargs: {},
    });
    return !!result;
}

AdminSwitchWidget.template = "AdminSwitchSystray";

registry.category("systray").add("AdminSwitchSystray", {
    Component: AdminSwitchWidget,
    isDisplayed(env) {
        return true;
    },
});
