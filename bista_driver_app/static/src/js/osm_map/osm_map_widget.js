/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onPatched, onWillUnmount, useRef } from "@odoo/owl";

const LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
const LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const DEFAULT_CENTER = [40.75, -74.125];
const DEFAULT_ZOOM = 14;

function loadCssOnce(href) {
    if (document.querySelector(`link[href="${href}"]`)) return Promise.resolve();
    return new Promise((resolve) => {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = href;
        link.onload = resolve;
        document.head.appendChild(link);
    });
}

function loadScriptOnce(src) {
    if (document.querySelector(`script[src="${src}"]`)) return Promise.resolve();
    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.async = true;
        script.onload = resolve;
        script.onerror = reject;
        document.body.appendChild(script);
    });
}

export class OsmMapWidget extends Component {
    static template = "web.OsmMapWidget";

    setup() {
        this.mapRef = useRef("osm_map_container");
        this.map = null;
        this.marker = null;

        onMounted(async () => {
            await loadCssOnce(LEAFLET_CSS);
            await loadScriptOnce(LEAFLET_JS);
            this._initMap();
        });

        onPatched(() => {
            this._updateMap();
        });

        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
                this.map = null;
            }
        });
    }

    _getCoords() {
        const data = this.props.record.data;
        const lat = parseFloat(data.latitude);
        const lng = parseFloat(data.longitude);
        if (!isNaN(lat) && !isNaN(lng)) {
            return [lat, lng];
        }
        return null;
    }

    _getZoom() {
        return this.props.record.data.zoom_level || DEFAULT_ZOOM;
    }

    _initMap() {
        const el = this.mapRef.el;
        if (!el || !window.L) return;

        const coords = this._getCoords();
        const center = coords || DEFAULT_CENTER;
        const zoom = this._getZoom();

        this.map = L.map(el).setView(center, zoom);

        L.tileLayer(TILE_URL, {
            attribution: TILE_ATTRIBUTION,
            maxZoom: 19,
        }).addTo(this.map);

        if (coords) {
            this.marker = L.marker(coords).addTo(this.map);
        }

        // Leaflet sometimes miscalculates container size when rendered inside hidden tabs.
        // Force a size recalculation after a short delay.
        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 300);
    }

    _updateMap() {
        if (!this.map) {
            this._initMap();
            return;
        }

        const coords = this._getCoords();
        const zoom = this._getZoom();

        if (coords) {
            this.map.setView(coords, zoom);
            if (this.marker) {
                this.marker.setLatLng(coords);
            } else {
                this.marker = L.marker(coords).addTo(this.map);
            }
        } else if (this.marker) {
            this.map.removeLayer(this.marker);
            this.marker = null;
            this.map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
        }

        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 300);
    }
}

export const osmMapWidget = {
    component: OsmMapWidget,
};

registry.category("view_widgets").add("osm_map", osmMapWidget);
