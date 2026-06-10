/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onPatched, onWillUnmount, useRef } from "@odoo/owl";

const LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
const LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const DEFAULT_CENTER = [40.75, -74.125];
const DEFAULT_ZOOM = 5;

const OSRM_BASE = "https://router.project-osrm.org/route/v1/driving/";
const OSRM_CHUNK_SIZE = 100;

const COLOR_ONLINE = "#34A853";
const COLOR_OFFLINE = "#EA4335";
const COLOR_ROUTE = "#4285F4";

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

function createPinIcon(label, color, size) {
    const s = size || 28;
    const half = s / 2;
    const html =
        `<div class="osm_marker_pin" style="width:${s}px;height:${s}px;">` +
            `<svg viewBox="0 0 ${s} ${s}" width="${s}" height="${s}">` +
                `<circle cx="${half}" cy="${half}" r="${half - 1}" fill="${color}" stroke="#fff" stroke-width="2"/>` +
                `<text x="${half}" y="${half}" text-anchor="middle" dominant-baseline="central" ` +
                    `fill="#fff" font-size="${Math.round(s * 0.43)}px" font-weight="bold" font-family="Arial,sans-serif">${label}</text>` +
            `</svg>` +
        `</div>`;
    return L.divIcon({
        html,
        className: "",
        iconSize: [s, s],
        iconAnchor: [half, half],
        popupAnchor: [0, -half],
    });
}

function createDotIcon(color) {
    const s = 14;
    const half = s / 2;
    const html =
        `<div class="osm_marker_dot">` +
            `<svg viewBox="0 0 ${s} ${s}" width="${s}" height="${s}">` +
                `<circle cx="${half}" cy="${half}" r="${half - 1}" fill="${color}" stroke="#fff" stroke-width="1.5"/>` +
            `</svg>` +
        `</div>`;
    return L.divIcon({
        html,
        className: "",
        iconSize: [s, s],
        iconAnchor: [half, half],
        popupAnchor: [0, -half],
    });
}

export class OsmTrackingMapWidget extends Component {
    static template = "web.OsmTrackingMapWidget";

    setup() {
        this.mapRef = useRef("osm_tracking_map_container");
        this.map = null;
        this.markersLayer = null;
        this._destroyed = false;

        onMounted(async () => {
            await loadCssOnce(LEAFLET_CSS);
            await loadScriptOnce(LEAFLET_JS);
            // Component may have unmounted while scripts were loading
            if (this._destroyed) return;
            this._initMap();
        });

        onPatched(() => {
            this._updateMap();
        });

        onWillUnmount(() => {
            this._destroyed = true;
            if (this.map) {
                this.map.remove();
                this.map = null;
            }
            this.markersLayer = null;
        });
    }

    get hasHistoryPoints() {
        const historyData = this.props.record.data.geolocation_history_ids;
        if (!historyData) return false;
        const records = historyData.records || [];
        return records.some(
            (r) => r.data.asset_latitude && r.data.asset_longitude
        );
    }

    _getHistoryPoints() {
        const historyData = this.props.record.data.geolocation_history_ids;
        if (!historyData) return [];

        const records = historyData.records || [];
        const points = [];

        for (const rec of records) {
            const lat = rec.data.asset_latitude;
            const lng = rec.data.asset_longitude;
            if (!lat || !lng) continue;

            points.push({
                lat,
                lng,
                connectivity_status: rec.data.connectivity_status || false,
                date_recorded: rec.data.date_recorded || false,
            });
        }

        points.sort((a, b) => {
            if (!a.date_recorded) return -1;
            if (!b.date_recorded) return 1;
            const dateA = a.date_recorded instanceof Date ? a.date_recorded : new Date(a.date_recorded);
            const dateB = b.date_recorded instanceof Date ? b.date_recorded : new Date(b.date_recorded);
            return dateA - dateB;
        });

        return points;
    }

    async _fetchRoute(points) {
        if (points.length < 2) return null;

        try {
            let allCoords = [];

            for (let i = 0; i < points.length; i += OSRM_CHUNK_SIZE - 1) {
                const chunk = points.slice(i, i + OSRM_CHUNK_SIZE);
                if (chunk.length < 2) break;

                const coordStr = chunk.map((p) => `${p.lng},${p.lat}`).join(";");
                const url = `${OSRM_BASE}${coordStr}?overview=full&geometries=geojson`;

                const resp = await fetch(url);
                if (!resp.ok) return null;

                const data = await resp.json();
                if (data.code !== "Ok" || !data.routes || !data.routes[0]) return null;

                const routeCoords = data.routes[0].geometry.coordinates;
                if (allCoords.length > 0) {
                    routeCoords.shift();
                }
                allCoords = allCoords.concat(routeCoords);
            }

            return {
                type: "Feature",
                geometry: {
                    type: "LineString",
                    coordinates: allCoords,
                },
            };
        } catch (e) {
            console.warn("OSRM routing failed, falling back to straight lines:", e);
            return null;
        }
    }

    _initMap() {
        const el = this.mapRef.el;
        if (!el || !window.L) return;

        this.map = L.map(el).setView(DEFAULT_CENTER, DEFAULT_ZOOM);

        L.tileLayer(TILE_URL, {
            attribution: TILE_ATTRIBUTION,
            maxZoom: 19,
        }).addTo(this.map);

        this.markersLayer = L.layerGroup().addTo(this.map);

        this._renderMarkers();

        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 300);
    }

//    Based on date_recorded of geolocation history model, start and end point define
//    Start point = "A" pin → i === 0 (the first item after sorting)
//    End point = "B" pin → i === lastIdx (the last item after sorting)

    async _renderMarkers() {
        // Guard: bail out early if map or layer is already gone
        if (!this.map || !this.markersLayer) return;

        this.markersLayer.clearLayers();

        const points = this._getHistoryPoints();
        if (points.length === 0) return;

        const lastIdx = points.length - 1;
        const coordsArray = [];

        for (let i = 0; i < points.length; i++) {
            const point = points[i];
            const latLng = [point.lat, point.lng];
            coordsArray.push(latLng);

            const isOnline = point.connectivity_status === "online";
            const statusColor = isOnline ? COLOR_ONLINE : COLOR_OFFLINE;
            const statusLabel = isOnline ? "Online" : "Offline";

            let icon;
            if (i === 0) {
                icon = createPinIcon("A", statusColor, 32);
            } else if (i === lastIdx) {
                icon = createPinIcon("B", statusColor, 32);
            } else {
                icon = createDotIcon(statusColor);
            }

            const marker = L.marker(latLng, { icon });

            let dateStr = "";
            if (point.date_recorded) {
                const d = point.date_recorded instanceof Date
                    ? point.date_recorded
                    : new Date(point.date_recorded);
                dateStr = d.toLocaleString();
            }

            marker.bindPopup(
                `<div style="min-width:160px">` +
                    `<b>Status:</b> <span style="color:${statusColor};font-weight:bold">${statusLabel}</span><br/>` +
                    `<b>Lat:</b> ${point.lat}<br/>` +
                    `<b>Lng:</b> ${point.lng}<br/>` +
                    (dateStr ? `<b>Date:</b> ${dateStr}` : "") +
                `</div>`
            );

            this.markersLayer.addLayer(marker);
        }

        // Guard: map may have been destroyed during the loop above
        if (!this.map) return;

        // Fit bounds using marker positions (synchronous — safe here)
        if (coordsArray.length > 1) {
            this.map.fitBounds(L.latLngBounds(coordsArray).pad(0.1));
        } else if (coordsArray.length === 1) {
            this.map.setView(coordsArray[0], 14);
        }

        if (points.length < 2) return;

        // ── ASYNC boundary: component can be destroyed at any point after this ──
        const routeGeoJson = await this._fetchRoute(points);

        // Guard: map/layer destroyed while the route was being fetched
        if (!this.map || !this.markersLayer) return;

        if (routeGeoJson) {
            const routeLayer = L.geoJSON(routeGeoJson, {
                style: {
                    color: COLOR_ROUTE,
                    weight: 5,
                    opacity: 0.8,
                },
            });
            this.markersLayer.addLayer(routeLayer);

            // Guard: one final check before fitBounds — this is the line that was crashing
            if (!this.map) return;
            this.map.fitBounds(routeLayer.getBounds().pad(0.1));
        } else {
            const polyline = L.polyline(coordsArray, {
                color: COLOR_ROUTE,
                weight: 4,
                opacity: 0.7,
            });
            this.markersLayer.addLayer(polyline);
        }
    }

    _updateMap() {
        if (!this.map) {
            this._initMap();
            return;
        }
        this._renderMarkers();

        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 300);
    }
}

export const osmTrackingMapWidget = {
    component: OsmTrackingMapWidget,
};

registry.category("view_widgets").add("osm_tracking_map", osmTrackingMapWidget);