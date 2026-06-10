/** @odoo-module **/

import {registry} from "@web/core/registry";
import {_t} from "@web/core/l10n/translation";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {useInputField} from "@web/views/fields/input_field_hook";
import {Component, onMounted, onRendered, onWillStart} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FleetMapField extends Component {
    setup() {
        this.orm = useService('orm');
        onRendered(async () =>{
            this.api_key = false;
            try {
                if (!this.api_key) {
                    this.api_key = await this.orm.call(
                        "shipment.shipment",
                        "get_map_api_key",
                        [[], "bista_driver_app.shipment_google_map_api_key"]
                    );
                    await this.loadScriptOnce(`https://maps.googleapis.com/maps/api/js?key=${this.api_key}&loading=async&libraries=places,drawing`);
                    this.displayMap();

                }else{
                    this.displayMap();
                }

            } catch (err) {
                console.error(err);
            }
        });

        useInputField({
            getValue: () => this.props.value || "",
        });
    }

    async loadScriptOnce(src) {
        if (document.querySelector(`script[src^="${src}"]`)) return;
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.type = "text/javascript";
            script.async = true;
            script.defer = true;
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.body.appendChild(script);
        });
    }

    displayMap() {
        let counter = 0;
        const _interval = setInterval(() => {
            counter++;
            var jsonString = this.props.record.data[this.props.name];
            var obj1 = jsonString.replace(/'/g, '"');
            var obj = JSON.parse(obj1);
            console.log(obj);
//            let lat, lng;
//            if (!obj || obj.lat === "" && obj.lng === "") {
//                lat  = 40.75;
//                lng = -74.125;
//            }else{
//                lat = obj.lat;
//                lng = obj.lng;
//            }
            let lat = (obj?.lat && obj?.lng) ? obj.lat : 40.75;
            let lng = (obj?.lat && obj?.lng) ? obj.lng : -74.125;

            const mapOptions = {
                center: new google.maps.LatLng(lat, lng),
                zoom: 14,
                disableDefaultUI: true,
                zoomControl: true,
                scaleControl: true,
                mapTypeId: google.maps.MapTypeId.SATELLITE,
                panControl: true,
                mapTypeControl: true,
                streetViewControl: true,
                fullscreenControl: true,
                scrollwheel: true,
                draggableCursor: 'default',       // 👈 cursor on hover
                draggingCursor: 'default',        // 👈 cursor while dragging
                mapTypeControlOptions: {
                    style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
                    mapTypeIds: ["satellite", "roadmap", "terrain", "hybrid"],
                    position: google.maps.ControlPosition.TOP_RIGHT,
                },
            };

            const mapDiv = document.getElementById("fleet_map");
            if (!mapDiv) {
                console.error('Map element not found.');
                return;
            }
            const map = new google.maps.Map(mapDiv, mapOptions);
            var labelMapType = new google.maps.StyledMapType(
                [
                    {
                        featureType: "poi",
                        elementType: "labels",
                        stylers: [{visibility: "on"}],
                    },
                ],
                {name: "Label"}
            );

            map.mapTypes.set("label", labelMapType);
            var iconBase = 'https://maps.google.com/mapfiles/kml/paddle/';

            new google.maps.Marker({
                position: new google.maps.LatLng(lat, lng),
                map: map,
                icon: iconBase + 'O.png',
                cursor: 'default',
            });

            if (google && google.maps) {
                clearInterval(_interval);
            }
            return map;
        }, 1000);
    }
}

FleetMapField.template = "web.fleetMapField";
FleetMapField.props = {
    ...standardFieldProps,
    placeholder: {type: String, optional: true},
};

export const fleetMapField = {
    component: FleetMapField,
    supportedTypes: ["char"],
    displayName: _t("Map")
};
registry.category("fields").add("fleet_maps", fleetMapField);
