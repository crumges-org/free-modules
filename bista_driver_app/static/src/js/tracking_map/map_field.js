///** @odoo-module **/
//   // Code For MAP View in Shipment Form
//import {registry} from "@web/core/registry";
//import {_lt} from "@web/core/l10n/translation";
//import {standardFieldProps} from "@web/views/fields/standard_field_props";
//import {useInputField} from "@web/views/fields/input_field_hook";
//import {Component, onMounted, onRendered, onWillStart, useEffect} from "@odoo/owl";
//import {useService} from "@web/core/utils/hooks";
//import {session} from "@web/session";
//
//export class ShipmentMap extends Component {
//    static template = "web.ShipmentMap";
//
//    setup() {
//        this.orm = useService("orm")
//
////        this.busService = this.env.services.bus_service;
////        this.busService.addChannel("map_refresh#" + session.uid.toString());
////        this.busService.subscribe("render", async (message) => await this.displayMap());
////        this.busService.start();
//
//        onWillStart(async () =>{
////            this.displayMap()
//            this.api_key = false;
//             try {
//                if (!this.api_key) {
//                    this.api_key = await this.orm.call(
//                        "shipment.shipment",
//                        "get_map_api_key",
//                        [[], "bista_driver_app.shipment_google_map_api_key"]
//                    );
//                    const scriptLoaded = await loadScript(`https://maps.googleapis.com/maps/api/js?key=${this.api_key}&libraries=places`);
//                    if (scriptLoaded.status) {
//                        this.displayMap();
//                    }
//
//                }else{
//                    this.displayMap();
//                }
//
//            } catch (err) {
//                console.error(err);
//            }
//        });
//
//        useEffect(() => {
//            this.displayMap();
//            }, () => [this.props.record.data.status_id || this.props.record.data.latest_latitude || this.props.record.data.latest_longitude]);
//
//
//        const loadScript = async (FILE_URL, async = true, type = "text/javascript") => {
//            return new Promise((resolve, reject) => {
//                if (document.querySelector(`script[src="${FILE_URL}"]`)) {
//                    resolve({ status: true }); // If script is already loaded, resolve immediately
//                    return;
//                }
//
//                try {
//                    const scriptEle = document.createElement("script");
//                    scriptEle.type = type;
//                    scriptEle.async = async;
//                    scriptEle.src = FILE_URL;
//                    scriptEle.addEventListener("load", (ev) => {
//                        resolve({status: true});
//                    });
//                    scriptEle.addEventListener("error", (ev) => {
//                        reject({
//                            status: false,
//                            message: `Failed to load the script ${FILE_URL}`,
//                        });
//                    });
//                    document.body.appendChild(scriptEle);
//                } catch (error) {
//                    reject(error);
//                }
//            });
//        };
////        this.api_key = false;
////
////        onRendered(async () => {
////            try {
////                if (!this.api_key) {
////                    this.api_key = await this.orm.call(
////                        "shipment.shipment",
////                        "get_map_api_key",
////                        [[], "bista_driver_app.shipment_google_map_api_key"]
////                    );
////                    const scriptLoaded = await loadScript(`https://maps.googleapis.com/maps/api/js?key=${this.api_key}&libraries=places`);
////                    if (scriptLoaded.status) {
////                        this.displayMap();
////                    }
////
////                }else{
////                    this.displayMap();
////                }
////
////            } catch (err) {
////                console.error(err);
////            }
////        });
//
//    }
//
//    async displayMap() {
//        const obj = await this.getLetLong();
//        const mapDiv = document.getElementById("map");
//        this.travelInfo = false;
//        if (!mapDiv) {
//            console.error('Map element not found.');
//            return;
//        }
//
//        if (Object.keys(obj).length === 0) {
//            mapDiv.innerHTML = `<h4>No data available to display on the map.</h4>`;
//            console.error('No data available to display on the map.');
//            return;
//        }
//
//        const stage = obj.stage;
//        const stage_name = obj.stage_name;
//        const mapOptions = {
//            center: new google.maps.LatLng(obj.origin.lat, obj.origin.lng),
//            zoom: 12,
//            disableDefaultUI: true,
//            zoomControl: true,
//            scaleControl: true,
//            fullscreenControl: true,
//            mapTypeId: google.maps.MapTypeId.HYBRID,
//            panControl: true,
//            mapTypeControl: true,
//            streetViewControl: true,
//            scrollwheel: true,
//            draggableCursor: 'default',
//            draggingCursor: 'default',
//            mapTypeControlOptions: {
//                style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
//                mapTypeIds: ["satellite", "roadmap", "terrain", "hybrid"],
//                position: google.maps.ControlPosition.TOP_RIGHT,
//            },
//        };
//
//        const map = new google.maps.Map(mapDiv, mapOptions);
//
//        const customIcons = {
//            origin: {
//                url: '/bista_driver_app/static/src/img/A1.png',
//                scaledSize: new google.maps.Size(40, 50)
//            },
//            destination: {
//                url: '/bista_driver_app/static/src/img/B1.png',
//                scaledSize: new google.maps.Size(40, 50)
//            },
//            waypoint: {
//                url: '/bista_driver_app/static/src/img/Truck123.png',
//                scaledSize: new google.maps.Size(40, 50)
//            },
//            eld_waypoint: {
//                url: '/bista_driver_app/static/src/img/Truck3.png',
//                scaledSize: new google.maps.Size(40, 50)
//            },
//            red: {
//                url: '/bista_driver_app/static/src/img/red_with_border.png',
//                scaledSize: new google.maps.Size(20, 20)
//            },
//            green: {
//                url: '/bista_driver_app/static/src/img/green_with_border.png',
//                scaledSize: new google.maps.Size(20, 20)
//            },
//            pink: {
//                url: '/bista_driver_app/static/src/img/pink_with_border.png',
//                scaledSize: new google.maps.Size(20, 20)
//            },
//        };
//
//        const bounds = new google.maps.LatLngBounds();
//        const driverInfoWindow = new google.maps.InfoWindow();  // 👈 Shared InfoWindow
//        const sharedInfoWindow = new google.maps.InfoWindow();  // 👈 Shared InfoWindow
//        const originInfoWindow = new google.maps.InfoWindow();  // 👈 Shared InfoWindow
//        const destinationInfoWindow = new google.maps.InfoWindow();  // 👈 Shared InfoWindow
//
//        // Origin Marker
//        const originMarker = new google.maps.Marker({
//            position: new google.maps.LatLng(obj.origin.lat, obj.origin.lng),
//            map: map,
//            icon: customIcons.origin,
//            zIndex: 1,
//            cursor: 'default'
//        });
//        if (obj.origin){
//            const origin = obj.origin;
//            const originContentString = `
//            <div style="z-index: 1000; font-size: 13px; padding: 6px 10px; min-width: 240px; font-family: Arial, sans-serif; line-height: 1.6;">
//                ${origin.location_name ? `<div><span style="font-weight:bold;">Name:</span>&nbsp;${origin.location_name}</div>` : ''}
//                ${origin.address ? `<div><span style="font-weight:bold;">Address:</span>&nbsp;${origin.address}</div>` : ''}
//                ${origin.planned_pickup ? `<div><span style="font-weight:bold;">Planned:</span>&nbsp;${origin.planned_pickup}${origin.timezone ? '&nbsp;' + origin.timezone : ''}</div>` : ''}
//                ${origin.actual_pickup ? `<div><span style="font-weight:bold;">Actual:</span>&nbsp;${origin.actual_pickup}${origin.timezone ? '&nbsp;' + origin.timezone : ''}</div>` : ''}
//            </div>
//        `;
//
//
//            originMarker.addListener("mouseover", () => {
//                originInfoWindow.setContent(originContentString);
//                originInfoWindow.open(map,originMarker);
//                if (sharedInfoWindow) {
//                    sharedInfoWindow.close();
//                    this.infoWindowMarkerOpen = false;
//                }
//
//            });
//
//            originMarker.addListener("mouseout", () => {
//                originInfoWindow.close();
//            });
//            if (obj.origin.shape_data) {
//                const shape = JSON.parse(obj.origin.shape_data);
//                let currentCircle = null;
//                let currentPolygon = null;
//                let currentRectangle = null;
//
//                // Draw shape based on type
//
//                if (shape.type === "circle" && shape.center) {
//                    const center = new google.maps.LatLng(shape.center.lat, shape.center.lng);
//                    currentCircle = new google.maps.Circle({
//                        strokeColor: "#3367D6",
//                        strokeOpacity: 1.0,
//                        strokeWeight: 2,
//                        fillColor: "#4285F4",
//                        fillOpacity: 0.10,
//                        editable: false,
//                        map: map,
//                        center: center,
//                        radius: shape.radius,
//                    });
//
//                    // map.setCenter(center);
//                    // setMainMarker(center);
//                    // if (this.props.record._config?.resModel !== 'call.out.request') {
//                    //     const originalData = {
//                    //         type: "circle",
//                    //         center: {
//                    //             lat: center.lat(),
//                    //             lng: center.lng(),
//                    //         },
//                    //         radius: shape.radius,
//                    //     };
//
//                    //     currentCircle.addListener('dblclick', () => this.removeShape(currentCircle));
//                    //     currentCircle.addListener('radius_changed', () => {
//                    //         if (this._revertLock) return;
//                    //         this.confirmSaveShapeData(currentCircle, originalData);
//                    //     });
//
//                    //     currentCircle.addListener('center_changed', () => {
//                    //         if (this._revertLock) return;
//                    //         this.confirmSaveShapeData(currentCircle, originalData);
//                    //     });
//                    // }
//
//                }
//
//                else if (shape.type === "polygon" && shape.path) {
//                    const bounds = new google.maps.LatLngBounds();
//                    shape.path.forEach(p => bounds.extend(p));
//                    map.fitBounds(bounds);
//
//                    currentPolygon = new google.maps.Polygon({
//                        paths: shape.path,
//                        strokeColor: "#3367D6",
//                        strokeOpacity: 1.0,
//                        strokeWeight: 2,
//                        fillColor: "#4285F4",
//                        fillOpacity: 0.10,
//                        editable: false,
//                        map: map,
//                    });
//
//                    // if (shape.center){
//                    //     const center = new google.maps.LatLng(shape.center.lat, shape.center.lng);
//                    //     setMainMarker(center);
//                    // }
//                    // if (this.props.record._config?.resModel !== 'call.out.request') {
//                    //     currentPolygon.addListener('dblclick', () => this.removeShape(currentPolygon));
//                    //     const path = currentPolygon.getPath();
//                    //     path.addListener('set_at', () => {
//                    //         this.saveShapeData(currentPolygon);
//                    //     });
//                    //     path.addListener('insert_at', () => {
//                    //         this.saveShapeData(currentPolygon);
//                    //     });
//                    //     path.addListener('remove_at', () => {
//                    //         this.saveShapeData(currentPolygon);
//                    //     });
//                    // }
//                }
//
//                else if (shape.type === "rectangle" && shape.bounds) {
//                    const sw = new google.maps.LatLng(shape.bounds.sw.lat, shape.bounds.sw.lng);
//                    const ne = new google.maps.LatLng(shape.bounds.ne.lat, shape.bounds.ne.lng);
//                    const bounds = new google.maps.LatLngBounds(sw, ne);
//
//                    currentRectangle = new google.maps.Rectangle({
//                        bounds: bounds,
//                        strokeColor: "#3367D6",
//                        strokeOpacity: 1.0,
//                        strokeWeight: 2,
//                        fillColor: "#4285F4",
//                        fillOpacity: 0.10,
//                        editable: false,
//                        map: map,
//                    });
//
//                    // map.fitBounds(bounds);
//
//                    // if (shape.center) {
//                    //     const center = new google.maps.LatLng(shape.center.lat, shape.center.lng);
//                    //     setMainMarker(center);
//                    // }
//
//                    // if (this.props.record._config?.resModel !== 'call.out.request') {
//                    //     const originalBounds = {
//                    //         sw: { lat: sw.lat(), lng: sw.lng() },
//                    //         ne: { lat: ne.lat(), lng: ne.lng() },
//                    //     };
//
//                    //     currentRectangle.addListener('dblclick', () => this.removeShape(currentRectangle));
//                    //     currentRectangle.addListener('bounds_changed', () => {
//                    //         if (!this._revertLock) {
//                    //             this.confirmSaveShapeData(currentRectangle, originalBounds);
//                    //         }
//
//                    //     });
//                    // }
//                }
//            }
//        }
//        bounds.extend(originMarker.getPosition());
//
//        // Destination Marker
//        const destinationMarker = new google.maps.Marker({
//            position: new google.maps.LatLng(obj.destination.lat, obj.destination.lng),
//            map: map,
//            icon: customIcons.destination,
//            zIndex: 1,
//            cursor: 'default'
//        });
//        if (obj.destination){
//            const destination = obj.destination;
//            const destinationContentString = `
//                <div style="z-index: 1000; font-size: 13px; padding: 6px 10px; min-width: 240px; font-family: Arial, sans-serif; line-height: 1.6;">
//                    ${destination.location_name ? `<div><span style="font-weight:bold;">Name:</span>&nbsp;${destination.location_name}</div>` : ''}
//                    ${destination.address ? `<div><span style="font-weight:bold;">Address:</span>&nbsp;${destination.address}</div>` : ''}
//                    ${destination.planned_delivery ? `<div><span style="font-weight:bold;">Planned:</span>&nbsp;${destination.planned_delivery}${destination.timezone ? ' ' + destination.timezone : ''}</div>` : ''}
//                    ${destination.actual_delivery ? `<div><span style="font-weight:bold;">Actual:</span>&nbsp;${destination.actual_delivery}${destination.timezone ? ' ' + destination.timezone : ''}</div>` : ''}
//                </div>
//            `;
//
//            destinationMarker.addListener("mouseover", () => {
//                destinationInfoWindow.setContent(destinationContentString);
//                destinationInfoWindow.open(map,destinationMarker);
//                if (sharedInfoWindow) {
//                    sharedInfoWindow.close();
//                    this.infoWindowMarkerOpen = false;
//                }
//
//            });
//
//            destinationMarker.addListener("mouseout", () => {
//                destinationInfoWindow.close();
//            });
//            if (obj.destination.shape_data) {
//                const shape = JSON.parse(obj.destination.shape_data);
//                let currentCircle = null;
//                let currentPolygon = null;
//                let currentRectangle = null;
//
//                // Draw shape based on type
//
//                if (shape.type === "circle" && shape.center) {
//                    const center = new google.maps.LatLng(shape.center.lat, shape.center.lng);
//                    currentCircle = new google.maps.Circle({
//                        strokeColor: "#3367D6",
//                        strokeOpacity: 1.0,
//                        strokeWeight: 2,
//                        fillColor: "#4285F4",
//                        fillOpacity: 0.10,
//                        editable: false,
//                        map: map,
//                        center: center,
//                        radius: shape.radius,
//                    });
//
//                    // map.setCenter(center);
//                    // setMainMarker(center);
//                    // if (this.props.record._config?.resModel !== 'call.out.request') {
//                    //     const originalData = {
//                    //         type: "circle",
//                    //         center: {
//                    //             lat: center.lat(),
//                    //             lng: center.lng(),
//                    //         },
//                    //         radius: shape.radius,
//                    //     };
//
//                    //     currentCircle.addListener('dblclick', () => this.removeShape(currentCircle));
//                    //     currentCircle.addListener('radius_changed', () => {
//                    //         if (this._revertLock) return;
//                    //         this.confirmSaveShapeData(currentCircle, originalData);
//                    //     });
//
//                    //     currentCircle.addListener('center_changed', () => {
//                    //         if (this._revertLock) return;
//                    //         this.confirmSaveShapeData(currentCircle, originalData);
//                    //     });
//                    // }
//
//                }
//
//                else if (shape.type === "polygon" && shape.path) {
//                    const bounds = new google.maps.LatLngBounds();
//                    shape.path.forEach(p => bounds.extend(p));
//                    map.fitBounds(bounds);
//
//                    currentPolygon = new google.maps.Polygon({
//                        paths: shape.path,
//                        strokeColor: "#3367D6",
//                        strokeOpacity: 1.0,
//                        strokeWeight: 2,
//                        fillColor: "#4285F4",
//                        fillOpacity: 0.10,
//                        editable: false,
//                        map: map,
//                    });
//
//                    // if (shape.center){
//                    //     const center = new google.maps.LatLng(shape.center.lat, shape.center.lng);
//                    //     setMainMarker(center);
//                    // }
//                    // if (this.props.record._config?.resModel !== 'call.out.request') {
//                    //     currentPolygon.addListener('dblclick', () => this.removeShape(currentPolygon));
//                    //     const path = currentPolygon.getPath();
//                    //     path.addListener('set_at', () => {
//                    //         this.saveShapeData(currentPolygon);
//                    //     });
//                    //     path.addListener('insert_at', () => {
//                    //         this.saveShapeData(currentPolygon);
//                    //     });
//                    //     path.addListener('remove_at', () => {
//                    //         this.saveShapeData(currentPolygon);
//                    //     });
//                    // }
//                }
//
//                else if (shape.type === "rectangle" && shape.bounds) {
//                    const sw = new google.maps.LatLng(shape.bounds.sw.lat, shape.bounds.sw.lng);
//                    const ne = new google.maps.LatLng(shape.bounds.ne.lat, shape.bounds.ne.lng);
//                    const bounds = new google.maps.LatLngBounds(sw, ne);
//
//                    currentRectangle = new google.maps.Rectangle({
//                        bounds: bounds,
//                        strokeColor: "#3367D6",
//                        strokeOpacity: 1.0,
//                        strokeWeight: 2,
//                        fillColor: "#4285F4",
//                        fillOpacity: 0.10,
//                        editable: false,
//                        map: map,
//                    });
//
//                    // map.fitBounds(bounds);
//
//                    // if (shape.center) {
//                    //     const center = new google.maps.LatLng(shape.center.lat, shape.center.lng);
//                    //     setMainMarker(center);
//                    // }
//
//                    // if (this.props.record._config?.resModel !== 'call.out.request') {
//                    //     const originalBounds = {
//                    //         sw: { lat: sw.lat(), lng: sw.lng() },
//                    //         ne: { lat: ne.lat(), lng: ne.lng() },
//                    //     };
//
//                    //     currentRectangle.addListener('dblclick', () => this.removeShape(currentRectangle));
//                    //     currentRectangle.addListener('bounds_changed', () => {
//                    //         if (!this._revertLock) {
//                    //             this.confirmSaveShapeData(currentRectangle, originalBounds);
//                    //         }
//
//                    //     });
//                    // }
//                }
//            }
//        }
//        bounds.extend(destinationMarker.getPosition());
//        // Directions API
//        const directionsService = new google.maps.DirectionsService();
//        const directionsRenderer = new google.maps.DirectionsRenderer({
//            suppressMarkers: true
//        });
//        directionsRenderer.setMap(map);
//
//        let directionsRequest = {
//            origin: new google.maps.LatLng(obj.origin.lat, obj.origin.lng),
//            destination: new google.maps.LatLng(obj.destination.lat, obj.destination.lng),
//            travelMode: google.maps.TravelMode.DRIVING,
//        };
//        if (obj.waypoints && obj.waypoints.lat && obj.waypoints.lng && obj.is_display_waypoints) {
//            directionsRequest.waypoints = [{
//                location: new google.maps.LatLng(obj.waypoints.lat, obj.waypoints.lng),
//                stopover: true
//            }];
//        }
//        if (obj.waypoints && obj.waypoints.lat && obj.waypoints.lng && obj.is_display_routes_from_truck_to_destination) {
//            directionsRequest.waypoints = [{
//                location: new google.maps.LatLng(obj.origin.lat, obj.origin.lng),
//                stopover: true
//            }];
//            directionsRequest.origin = new google.maps.LatLng(obj.waypoints.lat, obj.waypoints.lng);
//        }
//        this.infoWindowMarkerOpen = false;
//
//        directionsService.route(directionsRequest, (result, status) => {
//            if (status === google.maps.DirectionsStatus.OK) {
//                directionsRenderer.setDirections(result);
//                if (obj.waypoints && obj.waypoints.lat && obj.waypoints.lng && obj.is_display_waypoints) {
//                    const route = result.routes[0];
//                    const leg = route.legs.at(-1);
//                    this.travelInfo = `
//                        <div style="z-index: 1000; font-size: 13px; padding: 6px 10px; min-width: 240px; font-family: Arial, sans-serif; line-height: 1.6;">
//                            ${stage ? `<div><span style="font-weight:bold;">Remaining Mileage:</span>&nbsp;${leg.distance.text || 'N/A'}</div>` : ''}
//                            <div><span style="font-weight:bold;">Date/Time:</span>&nbsp;${obj.waypoints.date_recorded || 'N/A'} ${obj.waypoints.timezone || ''}</div>
//                            <div><span style="font-weight:bold;">Latitude & Longitude:</span>&nbsp;${obj.waypoints.lat}, ${obj.waypoints.lng}</div>
//                            <div><span style="font-weight:bold;">Connectivity Status:</span>&nbsp;${obj.waypoints.connectivity_status}</div>
//                            <div><span style="font-weight:bold;">Driver Name:</span>&nbsp;${obj.waypoints.driver_name || 'N/A'}</div>
//                            <div><span style="font-weight:bold;">Carrier:</span>&nbsp;${obj.waypoints.carrier_name || 'N/A'} &lt;${obj.waypoints.truck_number || 'N/A'}&gt;</div>
//                            <div><span style="font-weight:bold;">Source:</span>&nbsp;${obj.waypoints.source}</div>
//                        </div>
//                    `;
//                    this.waypointMarker = new google.maps.Marker({
//                        position: new google.maps.LatLng(obj.waypoints.lat, obj.waypoints.lng),
//                        map: map,
//                        // icon: customIcons.waypoint,
//                        icon: obj.waypoints.eld_waypoint ? customIcons.eld_waypoint : customIcons.waypoint,
//                        zIndex: 1,
//                        cursor: 'default'
//                    });
//                    bounds.extend(this.waypointMarker.getPosition());
//                    if (this.travelInfo) {
//                        sharedInfoWindow.setContent(this.travelInfo);
//                        sharedInfoWindow.open(map, this.waypointMarker);
//                        this.infoWindowMarkerOpen = true;
//
//                        this.waypointMarker.addListener("mouseover", () => {
//                            sharedInfoWindow.setContent(this.travelInfo);
//                            sharedInfoWindow.open(map, this.waypointMarker);
//                            this.infoWindowMarkerOpen = true;
//                        });
//
//                        this.waypointMarker.addListener("mouseout", () => {
//                            sharedInfoWindow.close();
//                            this.infoWindowMarkerOpen = false;
//                        });
//                    }
//                }
//            } else {
//                console.error('Directions request failed due to:', status);
//                map.fitBounds(bounds);
//                google.maps.event.addListenerOnce(map, 'bounds_changed', function () {
//                    if (map.getZoom() > 10) {
//                        map.setZoom(10);
//                    }
//                });
//            }
//
//
//        });
//        google.maps.event.addListener(map, "click", () => {
//            if (this.infoWindowMarkerOpen && sharedInfoWindow.getMap()) {
//                sharedInfoWindow.close();
//                this.infoWindowMarkerOpen = false;
//            }
//        });
//
//        // Geolocation history markers
//        if (obj.geolocation_history && obj.geolocation_history.length > 0) {
//            for (let i = 0; i < obj.geolocation_history.length; i++) {
//                let geo = obj.geolocation_history[i];
//                let icon;
//                if (geo.connectivity_status === 'Online' && geo.device_type === 'mobile') {
//                    icon = customIcons.green;
//                } else if (geo.device_type === 'eld') {
//                    icon = customIcons.pink;
//                } else if (geo.connectivity_status === 'Offline') {
//                    icon = customIcons.red;
//                }
//
//                const marker = new google.maps.Marker({
//                    position: new google.maps.LatLng(geo.lat, geo.lng),
//                    map: map,
//                    icon: icon,
//                    zIndex: 999,
//                    cursor: 'default'
//                });
//
//                const contentString = `
//                    <div style="z-index: 1000; font-size: 13px; padding: 6px 10px; min-width: 240px; font-family: Arial, sans-serif; line-height: 1.6;">
//                        <div><span style="font-weight:bold;">Date/Time:</span> ${geo.date_recorded || 'N/A'} ${geo.timezone || ''}</div>
//                        <div><span style="font-weight:bold;">Latitude & Longitude:</span> ${geo.lat}, ${geo.lng}</div>
//                        <div><span style="font-weight:bold;">Connectivity Status:</span> ${geo.connectivity_status}</div>
//                        <div><span style="font-weight:bold;">Driver Name:</span> ${geo.driver_name || 'N/A'}</div>
//                        <div><span style="font-weight:bold;">Carrier:</span> ${geo.carrier_name || 'N/A'} &lt;${geo.truck_number || 'N/A'}&gt;</div>
//                        <div><span style="font-weight:bold;">Source:</span> ${geo.source || 'N/A'}</div>
//                    </div>
//                `;
//
//                marker.addListener("mouseover", () => {
//                    driverInfoWindow.setContent(contentString);
//                    driverInfoWindow.open(map, marker);
//                    if (sharedInfoWindow) {
//                        sharedInfoWindow.close();
//                        this.infoWindowMarkerOpen = false;
//                    }
//
//                });
//
//                marker.addListener("mouseout", () => {
//                    driverInfoWindow.close();
//                });
//
//                bounds.extend(marker.getPosition());
//            }
//        }
//
//        return map;
//    }
//
//
//    async getLetLong(){
//        var record_id = this.props.record.evalContext['id']
//        const action = await this.orm.call(
//            "shipment.shipment",
//            "get_lat_lon",
//            [[record_id]],
//        );
//
//        return action
//    }
//}
//
//export const shipmentMap = {
//    component: ShipmentMap,
//};
//
//registry.category("view_widgets").add("shipment_maps", shipmentMap);
