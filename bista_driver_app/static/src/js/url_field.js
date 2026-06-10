/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, onMounted, onRendered} from "@odoo/owl";


class TrackingPopup extends Component {
    static template = "bista_driver_app.FleetMap";

    setup() {
        super.setup();
        this.action = useService('action');
        this.orm = useService('orm');
    }

    async openPopup(){
        if (this.props.record.data.latitude != null && this.props.record.data.longitude != null) {
            const action = await this.orm.call(
                this.props.record.evalContext.active_model,
                "get_map_action",
                [this.props.record.evalContext.active_id],
            );
            await this.action.doAction(action);
        }
        else{
            alert('Please enter latitude and longitude')
        }

    }
}

export const trackingPopup = {
    component: TrackingPopup,
    extractProps: ({ attrs }) => {
        return {
            urlfield: attrs.url_field || "",
        };
    },
};

registry.category("view_widgets").add("google_map", trackingPopup);
