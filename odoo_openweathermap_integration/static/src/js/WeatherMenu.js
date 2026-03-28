/** @odoo-module **/
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";


export class WeatherMenu extends Component {
    static template = "odoo_openweathermap_integration.systrayWeatherMenu";
    static components = { Dropdown, DropdownItem, CheckBox };

    setup() {
        this.state = useState({
            // normalized weather payload (OWM raw)
            weather: null,
            // presentation helpers
            displayTemp: null,      // temp shown to user (according to scale)
            celsiusTemp: null,      // temp normalized to °C (for color classes)
            feelsLikeTemp: null, // temp feels like (according to scale)
            unitLabel: "",          // °C / °F / K
            heatClass: "",          // text-danger / text-warning / text-info
            error: null,
            errorMessage: "",
        });
        
        this.weatherSystray = useWeatherSystray();
        this.user = user;                    // expose to template
        this.orm = useService("orm");
        this.session = session;
        this._timer = null;

        onWillStart(async () => {
            this.isWeatherGroup = await user.hasGroup("odoo_openweathermap_integration.group_show_weather_forecast")
            if (this.isWeatherGroup) {
                await this._loadUserPrefs();
                await this.fetchData();
                this._timer = setInterval(() => this.fetchData(), 300000); // 5 min
            }
        });

        onWillUnmount(() => {
            if (this._timer) clearInterval(this._timer);
        });
    }

    async _loadUserPrefs() {
        // read custom fields once; make them available on reactive `user`
        try {
            const [vals] = await this.orm.read("res.users", [this.user.userId], [
                "show_weather_notification",
                "weather_temp_scale_type",
            ]);
            if (vals) {
                this.user.show_weather_notification = !!vals.show_weather_notification;
                this.user.weather_temp_scale_type = vals.weather_temp_scale_type || "metric";
            }
        } catch (e) {
            // swallow—UI will simply not render
        }
    }

    async fetchData() {
        try {
            const raw = await rpc("/weather/notification/check", {});
            // normalize
            const payload = raw?.data || raw || null;
            const hasError = !!(raw?.error || (payload?.cod && payload.cod !== 200));
            if (hasError || !payload?.main) {
                this.state.weather = null;
                this.state.error = raw?.error || "no_data";
                this.state.errorMessage = raw?.message || "No weather data available.";
                this._applyPresentation(null);
            } else {
                this.state.weather = payload;
                this.state.error = null;
                this.state.errorMessage = null;
                this._applyPresentation(payload);
            }
            this._updateSession();
        } catch (e) {
            this.state.weather = null;
            this.state.error = "rpc_failed";
            this._applyPresentation(null);
            this._updateSession();
        }
    }

    _applyPresentation(w) {
        // compute temps/labels/classes once
        const scale = this.user.weather_temp_scale_type || "metric";
        let displayTemp = null;
        let celsiusTemp = null;
        let feelsLikeTemp = null;
        let unitLabel = "";
        let heatClass = "";

        if (w?.main?.temp != null && typeof w.main.temp === "number") {
            const t = w.main.temp;
            const f = w.main.feels_like;
            displayTemp = Math.round(t);
            feelsLikeTemp = Math.round(f);
            if (scale === "imperial") {          // OWM °F if units=imperial
                celsiusTemp = Math.round((t - 32) * 5 / 9);
                unitLabel = "°F";
            } else if (scale === "standard") {   // OWM Kelvin if units=standard
                celsiusTemp = Math.round(t - 273.15);
                unitLabel = "K";
            } else {                             // metric: °C
                celsiusTemp = Math.round(t);
                unitLabel = "°C";
            }

            // color class from °C
            if (celsiusTemp >= 30) heatClass = "text-danger";
            else if (celsiusTemp >= 10) heatClass = "text-warning";
            else heatClass = "text-info";
        }

        this.state.displayTemp = displayTemp;
        this.state.celsiusTemp = celsiusTemp;
        this.state.feelsLikeTemp = feelsLikeTemp;
        this.state.unitLabel = unitLabel;
        this.state.heatClass = heatClass;
    }

    _updateSession() {
        const w = this.state.weather;
        if (!w) {
            this.session.name = "";
            this.session.main = "";
            this.session.country = "";
            this.session.description = this.state.error ? String(this.state.error) : "";
            this.session.temp = "";
            return;
        }
        this.session.name = w?.name || "";
        this.session.country = w?.sys?.country || "";
        this.session.main = w?.weather?.[0]?.main || "";
        this.session.description = w?.weather?.[0]?.description || "";
        this.session.temp = this.state.displayTemp ?? "";
    }
}

registry.category("systray").add("WeatherNotification", { Component: WeatherMenu }, {sequence: 0});

export function useWeatherSystray() {
    const ui = useState(useService("ui"));
    return {
        get contentClass() {
            return `d-flex flex-column flex-grow-1 ${
                ui.isSmall ? "overflow-auto w-100 mh-100" : ""
            }`;
        },
        get menuClass() {
            return `${
                ui.isSmall
                    ? "start-0 w-100 mh-100 d-flex flex-column mt-0 border-0 shadow-lg"
                    : ""
            }`;
        },
    };
}
