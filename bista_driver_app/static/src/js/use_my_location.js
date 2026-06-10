/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import {session} from "@web/session";
import { user } from "@web/core/user";

export class UseMyLocation extends Component {
    static template = "bista_driver_app.UseMyLocation";

    setup() {
        // this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.is_callout_user = false;
        this.is_admin = false;
        this.is_shipment_dispatcher = false;
        const model = this.props.record.evalContext.active_model;
//        if (model === 'call.out.request') {
//            this.is_callout_user = this.env.model.user.hasGroup('bista_call_out_request.group_call_out_user_access');
//            this.is_admin = this.env.model.user.hasGroup('bista_call_out_request.group_call_out_admin_access');
//        }

        // if (model === 'shipment.location' || model === 'shipment.stop') {
        //     this.is_shipment_dispatcher = this.env.model.user.hasGroup('bista_driver_app.group_shipment_dispatcher_access');
        // }
        if (this.props.record.model.config.resModel === "shipment.location" || this.props.record.model.config.resModel === "shipment.stop") {
            this.is_shipment_dispatcher = user.hasGroup('bista_driver_app.group_shipment_dispatcher_access');
        }

        
    }

    async getLocationAndUpdate() {
        if (!navigator.geolocation) {
            this.notification.add("Geolocation is not supported by your browser.", { type: "danger" });
            return;
        }

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                try {
                    this.props.record.update({ latitude: parseFloat(lat.toFixed(6)), longitude: parseFloat(lng.toFixed(6)) });
                    this.notification.add("Location updated successfully!", { type: "success" });
                } catch (error) {
                    console.error(error);
                    this.notification.add("Failed to update location.", { type: "danger" });
                }
            },
            (error) => {
                console.error(error);
                this.notification.add("Unable to retrieve your location.", { type: "danger" });
            }
        );
    }
}

export const useMyLocation = {
    component: UseMyLocation,
};

registry.category("view_widgets").add("use_my_location", useMyLocation);

