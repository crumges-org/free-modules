/** @odoo-module **/

import { CharField } from "@web/views/fields/char/char_field";
import { _t } from "@web/core/l10n/translation";
import { useRef, onMounted, onRendered } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class AddressAutocompleteGmap extends CharField {
    static template = "web.AddressAutocompleteGmap";
    static props = {
        ...CharField.props,
        streetField: String,
        street2Field: String,
        cityField: String,
        zipField: String,
        stateField: String,
        countryField: String,
        countyField: String,
        latField: String,
        lngField: String,
    };

    setup() {
        super.setup();
        this.input = useRef("input");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.api_key = false;

        onRendered(async () => {
            if (!this.api_key) {
                this.api_key = await this.orm.call(
                    "shipment.shipment",
                    "get_map_api_key",
                    [[], "bista_driver_app.shipment_google_map_api_key"]
                );
                await this.loadScriptOnce(`https://maps.googleapis.com/maps/api/js?key=${this.api_key}&loading=async&libraries=places,drawing`);
            }
        });

        onMounted(() => {
            let counter = 0;
            const _interval = setInterval(() => {
                counter++;
                if (typeof google === "undefined" || !google.maps) return;
                clearInterval(_interval);

                const autocomplete = new google.maps.places.Autocomplete(this.input.el, {
                    types: ["geocode"],
                    componentRestrictions: { country: "us" },
                });
                autocomplete.setFields(["address_components", "geometry"]);

                autocomplete.addListener("place_changed", async () => {
                    const place = autocomplete.getPlace();
                    if (!place || !place.geometry) return;

                    const location = place.geometry.location;
                    const components = place.address_components;
                    const parsed = await this._parseAddress(components);

                    // Set the full formatted address as the address field value
                    parsed[this.props.name] = [
                        parsed[this.props.streetField],
                        parsed[this.props.cityField],
                        parsed[this.props.stateField] ? parsed[this.props.stateField][1] : "",
                        parsed[this.props.zipField],
                        parsed[this.props.countryField] ? parsed[this.props.countryField][1] : ""
                    ].filter(Boolean).join(", ");

                    parsed[this.props.latField] = parseFloat(location.lat().toFixed(6));
                    parsed[this.props.lngField] = parseFloat(location.lng().toFixed(6));

                    this.props.record.update(parsed);
                });
            }, 1000);
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

    async _parseAddress(components) {
        const data = {
            [this.props.streetField]: '',
            [this.props.street2Field]: '',
            [this.props.cityField]: '',
            [this.props.zipField]: '',
            [this.props.stateField]: false,
            [this.props.countryField]: false,
        };

        let streetNumber = "";
        let route = "";
        let stateName = "";
        let countryName = "";
        let countyName = "";

        for (const c of components) {
            if (c.types.includes("street_number")) streetNumber = c.long_name;
            else if (c.types.includes("route")) route = c.long_name;
            else if (c.types.includes("subpremise")) data[this.props.street2Field] = c.long_name;
            else if (c.types.includes("locality")) data[this.props.cityField] = c.long_name;
            else if (c.types.includes("postal_code")) data[this.props.zipField] = c.long_name;
            else if (c.types.includes("administrative_area_level_1")) stateName = c.long_name;
            else if (c.types.includes("country")) countryName = c.long_name;
            else if (c.types.includes("sublocality_level_1")) countyName = c.short_name;
        }

        data[this.props.streetField] = [streetNumber, route].filter(Boolean).join(" ") || "";

        if (countryName) {
            const id = await this._resolveMany2one("res.country", countryName);
            data[this.props.countryField] = id ? [id, countryName] : false;
        }
        let stateId = false;
        if (stateName) {
            stateId = await this._resolveMany2one("res.country.state", stateName);
            data[this.props.stateField] = stateId ? [stateId, stateName] : false;
        }
        if (countyName && stateId && !this.props.record.data[this.props.countyField]) {
            const domain = [["name", "ilike", countyName], ["state_id", "=", stateId]];
            console.log("domain", domain);
            const id = await this._resolveMany2one("res.city", countyName, domain);
            data[this.props.countyField] = id ? [id, countyName] : false;
        }

        return data;
    }

    async _resolveMany2one(model, name, domain = [["name", "ilike", name]]) {
        const records = await this.orm.searchRead(model, domain, ["id"], { limit: 1 });
        return records.length ? records[0].id : false;
    }
}

export const addressAutocompleteGmap = {
    component: AddressAutocompleteGmap,
    supportedTypes: ["char"],
    supportedOptions: [
        { name: "street", label: _t("Street"), type: "char" },
        { name: "street2", label: _t("Street 2"), type: "char" },
        { name: "city", label: _t("City"), type: "char" },
        { name: "zip", label: _t("ZIP"), type: "char" },
        { name: "state", label: _t("State"), type: "char" },
        { name: "country", label: _t("Country"), type: "char" },
        { name: "county", label: _t("County"), type: "char" },
        { name: "latitude", label: _t("Latitude"), type: "char" },
        { name: "longitude", label: _t("Longitude"), type: "char" },
    ],
    relatedFields: ({ options }) => {
        return Object.entries(options).map(([name, field]) => ({
            name: field,
            type: "char",
            readonly: false,
        }));
    },
    extractProps({ options }) {
        return {
            streetField: options.street,
            street2Field: options.street2,
            cityField: options.city,
            zipField: options.zip,
            stateField: options.state,
            countryField: options.country,
            countyField: options.county,
            latField: options.latitude,
            lngField: options.longitude,
        };
    },
};

registry.category("fields").add("address_autocomplete_gmap_widget", addressAutocompleteGmap);
