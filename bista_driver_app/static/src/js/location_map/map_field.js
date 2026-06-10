/** @odoo-module **/

import {registry} from "@web/core/registry";
//import {_t} from "@web/core/l10n/translation";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {useInputField} from "@web/views/fields/input_field_hook";
import {Component, onMounted, onRendered} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";


export class LocationMapField extends Component {
    setup() {
        this.orm = useService('orm');
        this.dialogService = useService("dialog");
        this.api_key = false;
        this._revertLock = false;
        onRendered(async () => {
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

    // Refactored and enhanced `displayMap` method with all 4 requirements
    async displayMap() {
        let counter = 0;
        let currentCircle = null;
        let currentPolygon = null;
        let currentRectangle = null;
        let mainMarker = null;
        const iconBase = 'https://maps.google.com/mapfiles/kml/paddle/';

        const getPolygonCenter = (polygon) => {
            const path = polygon.getPath().getArray();
            let lat = 0, lng = 0;
            path.forEach(p => {
                lat += p.lat();
                lng += p.lng();
            });
            return new google.maps.LatLng(lat / path.length, lng / path.length);
        };

        const _interval = setInterval(() => {
            counter++;
            const shape_data = this.props.record.data['shape_data'];
            const zoom_level = this.props.record.data['zoom_level'] || 14;
            const mapDiv = document.getElementById("location_map");
            if (!mapDiv) return;

            const map = new google.maps.Map(mapDiv, {
                center: new google.maps.LatLng(40.75, -74.125),
                zoom: zoom_level,
                disableDefaultUI: true,
                zoomControl: true,
                scaleControl: true,
                mapTypeId: google.maps.MapTypeId.HYBRID,
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
            });

            const updateMarkerAndShape = (newCenter) => {
                if (mainMarker) mainMarker.setPosition(newCenter);
                if (currentCircle) currentCircle.setCenter(newCenter);
                if (currentPolygon) {
                    const oldCenter = getPolygonCenter(currentPolygon);
                    const offsetLat = newCenter.lat() - oldCenter.lat();
                    const offsetLng = newCenter.lng() - oldCenter.lng();
                    const newPath = currentPolygon.getPath().getArray().map(p => new google.maps.LatLng(p.lat() + offsetLat, p.lng() + offsetLng));
                    currentPolygon.setPath(newPath);
                }
                if (currentRectangle) {
                    const bounds = currentRectangle.getBounds();
                    const oldCenter = bounds.getCenter();
                    const offsetLat = newCenter.lat() - oldCenter.lat();
                    const offsetLng = newCenter.lng() - oldCenter.lng();
                    const ne = bounds.getNorthEast();
                    const sw = bounds.getSouthWest();
                    currentRectangle.setBounds(new google.maps.LatLngBounds(
                        new google.maps.LatLng(sw.lat() + offsetLat, sw.lng() + offsetLng),
                        new google.maps.LatLng(ne.lat() + offsetLat, ne.lng() + offsetLng)
                    ));
                }
                this.saveShapeData(currentCircle || currentPolygon || currentRectangle);
            };

            const setMainMarker = (position) => {
                if (mainMarker) mainMarker.setMap(null);
                mainMarker = new google.maps.Marker({
                    position,
                    map,
                    draggable: false,
                    icon: { url: iconBase + 'O.png', scaledSize: new google.maps.Size(50, 50) },
                });
            };

            if (shape_data) {
                const shape = JSON.parse(shape_data);

                if (shape.type === "circle" && shape.center) {
                    const center = new google.maps.LatLng(shape.center.lat, shape.center.lng);
                    currentCircle = new google.maps.Circle({
                        strokeColor: "#3367D6",
                        strokeOpacity: 1.0,
                        strokeWeight: 2,
                        fillColor: "#4285F4",
                        fillOpacity: 0.10,
                        editable: this.props.record._config?.resModel !== 'call.out.request',
                        map: map,
                        center: center,
                        radius: shape.radius,
                    });

                    map.setCenter(center);
                    setMainMarker(center);
                    if (this.props.record._config?.resModel !== 'call.out.request') {
                        const originalData = {
                            type: "circle",
                            center: {
                                lat: center.lat(),
                                lng: center.lng(),
                            },
                            radius: shape.radius,
                        };

                        currentCircle.addListener('dblclick', () => this.removeShape(currentCircle));
                        currentCircle.addListener('radius_changed', () => {
                            if (this._revertLock) return;
                            this.confirmSaveShapeData(currentCircle, originalData);
                        });

                        currentCircle.addListener('center_changed', () => {
                            if (this._revertLock) return;
                            this.confirmSaveShapeData(currentCircle, originalData);
                        });
                    }

                }

                else if (shape.type === "polygon" && shape.path) {
                    const bounds = new google.maps.LatLngBounds();
                    shape.path.forEach(p => bounds.extend(p));
                    map.fitBounds(bounds);

                    currentPolygon = new google.maps.Polygon({
                        paths: shape.path,
                        strokeColor: "#3367D6",
                        strokeOpacity: 1.0,
                        strokeWeight: 2,
                        fillColor: "#4285F4",
                        fillOpacity: 0.10,
                        editable: this.props.record._config?.resModel !== 'call.out.request',
                        map: map,
                    });

                    if (shape.center){
                        const center = new google.maps.LatLng(shape.center.lat, shape.center.lng);
                        setMainMarker(center);
                    }
                    if (this.props.record._config?.resModel !== 'call.out.request') {
                        currentPolygon.addListener('dblclick', () => this.removeShape(currentPolygon));
                        const path = currentPolygon.getPath();
                        path.addListener('set_at', () => {
                            this.saveShapeData(currentPolygon);
                        });
                        path.addListener('insert_at', () => {
                            this.saveShapeData(currentPolygon);
                        });
                        path.addListener('remove_at', () => {
                            this.saveShapeData(currentPolygon);
                        });
                    }
                }

                else if (shape.type === "rectangle" && shape.bounds) {
                    const sw = new google.maps.LatLng(shape.bounds.sw.lat, shape.bounds.sw.lng);
                    const ne = new google.maps.LatLng(shape.bounds.ne.lat, shape.bounds.ne.lng);
                    const bounds = new google.maps.LatLngBounds(sw, ne);

                    currentRectangle = new google.maps.Rectangle({
                        bounds: bounds,
                        strokeColor: "#3367D6",
                        strokeOpacity: 1.0,
                        strokeWeight: 2,
                        fillColor: "#4285F4",
                        fillOpacity: 0.10,
                        editable: this.props.record._config?.resModel !== 'call.out.request',
                        map: map,
                    });

                    map.fitBounds(bounds);

                    if (shape.center) {
                        const center = new google.maps.LatLng(shape.center.lat, shape.center.lng);
                        setMainMarker(center);
                    }

                    if (this.props.record._config?.resModel !== 'call.out.request') {
                        const originalBounds = {
                            sw: { lat: sw.lat(), lng: sw.lng() },
                            ne: { lat: ne.lat(), lng: ne.lng() },
                        };

                        currentRectangle.addListener('dblclick', () => this.removeShape(currentRectangle));
                        currentRectangle.addListener('bounds_changed', () => {
                            if (!this._revertLock) {
                                this.confirmSaveShapeData(currentRectangle, originalBounds);
                            }

                        });
                    }
                }
            }

            if (this.props.record._config?.resModel !== 'call.out.request') {
                // Create the drawing manager
                const drawingManager = new google.maps.drawing.DrawingManager({
                    drawingControl: true,
                    drawingControlOptions: {
                        position: google.maps.ControlPosition.TOP_CENTER,
                        drawingModes: ['circle','polygon','rectangle'],
                    },
                    circleOptions: {
                        strokeColor: "#3367D6",
                        strokeOpacity: 1.0,
                        strokeWeight: 2,
                        fillColor: "#4285F4",
                        fillOpacity: 0.10,
                        editable: true,
                    },
                    polygonOptions: {
                        strokeColor: "#3367D6",
                        strokeOpacity: 1.0,
                        strokeWeight: 2,
                        fillColor: "#4285F4",
                        fillOpacity: 0.10,
                        editable: true,
                    },
                    rectangleOptions: { // ✅ Rectangle-specific options
                        strokeColor: "#3367D6",
                        strokeOpacity: 1.0,
                        strokeWeight: 2,
                        fillColor: "#4285F4",
                        fillOpacity: 0.10,
                        editable: true,
                    }
                });
                drawingManager.setMap(map);

                 // Drawing listener
                google.maps.event.addListener(drawingManager, 'overlaycomplete', (event) => {
                    if (currentCircle) currentCircle.setMap(null);
                    if (currentPolygon) currentPolygon.setMap(null);
                    if (currentRectangle) currentRectangle.setMap(null);
                    currentPolygon = null;
                    currentCircle = null;
                    currentRectangle = null;

                    if (event.type === 'circle') {
                        currentCircle = event.overlay;
                        currentCircle.setEditable(true);
                        setMainMarker(currentCircle.getCenter());
                        google.maps.event.addListener(currentCircle, 'dblclick', () => {
                            const message = `Do you want to delete the circle?`;
                            const currentZoom = map.getZoom();
                            this.dialogService.add(ConfirmationDialog, {
                                 title: _t("Confirmation"),
                                 body: _t(message),
                                 confirmClass: "btn-primary",
                                 confirmLabel: _t("Ok"),
                                 confirm: async () => {
                                        currentCircle.setMap(null);
                                        currentCircle = null;
                                        await this.props.record.update({
                                            shape_data: 0,
                                            zoom_level: currentZoom,
                                        });
                                        await this.props.record.save();
                                 },
                                 cancelLabel : _t("Cancel"),
                                 cancel: () => { },
                             });
                        });
                        google.maps.event.addListener(currentCircle, 'radius_changed', () => this.saveShapeData(currentCircle));
                        google.maps.event.addListener(currentCircle, 'center_changed', () => this.saveShapeData(currentCircle));

                        this.saveShapeData(currentCircle);
        //                    this.saveCoordinatesToRecord(currentCircle.getCenter().lat(), currentCircle.getCenter().lng(), map.getZoom());

                    } else if (event.type === 'polygon') {
                        currentPolygon = event.overlay;
                        currentPolygon.setEditable(true);
                        setMainMarker(getPolygonCenter(currentPolygon));
                        google.maps.event.addListener(currentPolygon, 'dblclick', () => {
                            currentPolygon.setMap(null);
                            currentPolygon = null;
                            this.saveShapeData(null);
                        });

                        const path = currentPolygon.getPath();
                        google.maps.event.addListener(path, 'set_at', () => this.saveShapeData(currentPolygon));
                        google.maps.event.addListener(path, 'insert_at', () => this.saveShapeData(currentPolygon));
                        google.maps.event.addListener(path, 'remove_at', () => this.saveShapeData(currentPolygon));

                        this.saveShapeData(currentPolygon);
        //                    this.saveCoordinatesToRecord(currentPolygon.getPath().getArray()[0].lat(), currentPolygon.getPath().getArray()[0].lng(), map.getZoom());
                    }
                    else if (event.type === 'rectangle') {
                        currentRectangle = event.overlay;
                        currentRectangle.setEditable(true);
                        setMainMarker(currentRectangle.bounds.getCenter());
                        // 🔥 Allow deletion on double-click
                        google.maps.event.addListener(currentRectangle, 'dblclick', () => {
                            currentRectangle.setMap(null);
                            currentRectangle = null;
                            this.saveShapeData(null);
                        });

                        // 🔁 Listen for bounds changes to re-save
                        google.maps.event.addListener(currentRectangle, 'bounds_changed', () => {
                            this.saveShapeData(currentRectangle);
                        });

                        // ✅ Save the shape
                        this.saveShapeData(currentRectangle);
        //                    this.saveCoordinatesToRecord(currentRectangle.getBounds().getNorthEast().lat(), currentRectangle.getBounds().getSouthWest().lng(), map.getZoom());
                    }
                    drawingManager.setDrawingMode(null);
                });

            }
            map.addListener("click", (e) => {
                const clickedLat = parseFloat(e.latLng.lat().toFixed(6));
                const clickedLng = parseFloat(e.latLng.lng().toFixed(6));
                const currentZoom = map.getZoom();
                const newCenter = new google.maps.LatLng(clickedLat, clickedLng);

                const message = `Do you want to update the location to the following coordinates?\n\nLatitude: ${clickedLat}\nLongitude: ${clickedLng}`;
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Confirmation"),
                    body: _t(message),
                    confirmClass: "btn-primary",
                    confirmLabel: _t("Ok"),
                    confirm: async () => {
                        this._revertLock = true;
                        updateMarkerAndShape(newCenter);
                        map.setCenter(newCenter);
                        map.setZoom(currentZoom);
                        // 🔒 Reset lock after delay
                        setTimeout(() => {
                            this._revertLock = false;
                        }, 300); // short delay to skip triggering change listeners during revert
                    },
                    cancelLabel: _t("Cancel"),
                    cancel: () => {},
                });
            });


            clearInterval(_interval);
        }, 1000);
    }

    async confirmSaveShapeData(shape, originalData = null) {
        const message = `Do you want to save the shape?`;
        this.dialogService.add(ConfirmationDialog, {
            title: _t("Confirmation"),
            body: _t(message),
            confirmClass: "btn-primary",
            confirmLabel: _t("Ok"),
            confirm: async () => await this.saveShapeData(shape),
            cancelLabel: _t("Cancel"),
            cancel: () => {
                if (!originalData || !shape) return;
                this._revertLock = true;

                if (shape instanceof google.maps.Rectangle) {
                    const sw = new google.maps.LatLng(originalData.sw.lat, originalData.sw.lng);
                    const ne = new google.maps.LatLng(originalData.ne.lat, originalData.ne.lng);
                    shape.setBounds(new google.maps.LatLngBounds(sw, ne));
                } else if (shape instanceof google.maps.Circle) {
                    shape.setCenter(new google.maps.LatLng(originalData.center.lat, originalData.center.lng));
                    shape.setRadius(originalData.radius);
                } else if (shape instanceof google.maps.Polygon) {
                    const path = originalData.path.map(p => new google.maps.LatLng(p.lat, p.lng));
                    shape.setPath(path);
                }

                // 🔒 Reset lock after delay
                setTimeout(() => {
                    this._revertLock = false;
                }, 300); // short delay to skip triggering change listeners during revert
            }
        });
    }


    async saveShapeData(shape) {
        let data = "";
        let latitude = 0;
        let longitude = 0;
        const getPolygonCenter = (polygon) => {
            const path = polygon.getPath().getArray();
            let lat = 0, lng = 0;
            path.forEach(p => {
                lat += p.lat();
                lng += p.lng();
            });
            return new google.maps.LatLng(lat / path.length, lng / path.length);
        };

        if (shape) {
            if (shape instanceof google.maps.Circle) {
                data = {
                    type: 'circle',
                    center: shape.getCenter().toJSON(),
                    radius: shape.getRadius()
                };
                latitude = shape.getCenter().lat();
                longitude = shape.getCenter().lng();
            } else if (shape instanceof google.maps.Polygon) {
                const position = getPolygonCenter(shape);
                data = { type: 'polygon', path: shape.getPath().getArray().map(p => p.toJSON()), center: position.toJSON() };
                latitude = position.lat();
                longitude = position.lng();
            }
            else if (shape instanceof google.maps.Rectangle) {
                const bounds = shape.getBounds();
                const position = bounds.getCenter()
                data = {
                    type: 'rectangle',
                    bounds: {
                        ne: bounds.getNorthEast().toJSON(),
                        sw: bounds.getSouthWest().toJSON(),
                    },
                    center: position.toJSON()
                };
                latitude = position.lat();
                longitude = position.lng();
            }
        }
        console.log(data);
        data = JSON.stringify(data);
        await this.saveCoordinatesToRecord(data, latitude, longitude);
    }



    async removeShape(shape) {
        const message = `Do you want to delete this shape?`;
        const currentZoom = this.props.record.data['zoom_level'] || 14;
        this.dialogService.add(ConfirmationDialog, {
            title: _t("Confirmation"),
            body: _t(message),
            confirmClass: "btn-primary",
            confirmLabel: _t("Ok"),
            confirm: async () => {
                shape.setMap(null);
                await this.props.record.update({
                    shape_data: "",
                    zoom_level: currentZoom,
                });
            },
            cancelLabel: _t("Cancel"),
            cancel: () => {},
        });
    }


    async saveCoordinatesToRecord(shape_data, lat, lng) {
        const fixedLat = parseFloat(lat.toFixed(6));
        const fixedLng = parseFloat(lng.toFixed(6));
        const changes = {
            shape_data: shape_data,
            latitude: fixedLat,
            longitude: fixedLng,
        };
        this.props.record.update(changes);
//        this.props.record.save();
    }

    async getRadius(){
        const radius = await this.orm.call(
            "shipment.settings",
            "get_raidus",
            [[], "Geofence Radius"]
        );
        return radius
    }

}

LocationMapField.template = "web.locationMapField";
LocationMapField.props = {
    ...standardFieldProps,
    placeholder: {type: String, optional: true},
};

export const locationMapField = {
    component: LocationMapField,
    supportedTypes: ["char"],
    displayName: _t("Map")
};
registry.category("fields").add("location_maps", locationMapField);
