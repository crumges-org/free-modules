// File: address_multiple_markers_gmap.js
import { Component, useRef, onWillStart, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class AddressMultipleMarkersGmap extends Component {
    static template = "web.AddressMultipleMarkersGmap";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this._gmapApiKey = false;
        this.mapref = useRef("googleMap");
        this.recordList = useRef("recordList");
        this.usageDisplay = useState({ value: "" });


        // to offset overlapping markers
        const markerPositions = {};
        let _lastHue = Math.random() * 360;
        // helper to add a marker + InfoWindow
        const addMarker = (position, title, address, label = null, icon = null) => {
            const key = `${position.lat.toFixed(6)},${position.lng.toFixed(6)}`;
            if (markerPositions[key] === undefined) {
                markerPositions[key] = 0;
            } else {
                markerPositions[key]++;
                const offset = markerPositions[key] * 0.0001;
                position = { lat: position.lat + offset, lng: position.lng + offset };
            }
            let html = `<div><strong>${title || ""}</strong>`;
            if (address) {
                html += `<br/>${address}`;
            }
            html += `</div>`;

            const opts = { position, map: this.map, title, icon };
            if (label) {
                opts.label = {
                    text: label,
                    color: "white",
                    fontSize: "12px",
                    fontWeight: "bold",
                };
            }
            const m = new google.maps.Marker(opts);
            const iw = new google.maps.InfoWindow({ content: html });
            m.addListener("click", () => iw.open(this.map, m));
            m.infoWindow = iw;
            return m;
        };

        // random pastel‑y color generator
        function getRandomColor() {
            _lastHue = (_lastHue + 137.508) % 360;
            // round to one decimal if you like, or drop to use full precision
            const hue = Math.round(_lastHue * 10) / 10;
            return `hsl(${hue}, 65%, 50%)`;
        }

        onWillStart(async () => {
            const key = await this._getGMapAPIKey();
            if (!key) {
                this.notification.add(
                    _t("Google Map API Key not configured. Please setup in Settings."),
                    { title: _t("API Key Missing"), type: "danger", sticky: true }
                );
            }
            // Load Google Maps JS API
            await loadJS(
                `https://maps.googleapis.com/maps/api/js?key=${key}&libraries=places,maps async`
            );
        });

        onMounted(async () => {
            // 1) initialize map
            this.map = new google.maps.Map(this.mapref.el, {
                center: { lat: 0, lng: 0 },
                zoom: 2,
            });

            // 2) icon definitions
            const icons = {
                start: {
                    url: "/mss_route_optimization/static/description/startEnd.svg",
                    scaledSize: new google.maps.Size(40, 40),
                },
                job: {
                    url: "/mss_route_optimization/static/description/pinpoint.svg",
                    scaledSize: new google.maps.Size(30, 30),
                },
                end: {
                    url: "/mss_route_optimization/static/description/startEnd.svg",
                    scaledSize: new google.maps.Size(40, 40),
                },
            };
            // clear sidebar
            this.recordList.el.innerHTML = "";

            try {
                // 3) fetch both the Traktop steps and the live vehicle GPS
                const [records, vehicleData] = await Promise.all([
                    this.orm.call("traktop", "search_read", [
                        [],
                        [
                            "id",
                            "partner_latitude",
                            "partner_longitude",
                            "display_name",
                            "delivery_address",
                            "driver_name",
                            "vehicle_id",       // [id, name]
                            "route_sequence",
                            "step_type",
                        ],
                    ]),
                    this.orm.call("traktop", "fetch_vehicle_data", []),
                ]);

                // 4) group steps by vehicle_id
                const byVehicle = {};
                for (const r of records) {
                    if (!r.vehicle_id || !r.vehicle_id[0]) {
                        continue; // skip unassigned
                    }
                    const vid = r.vehicle_id[0];
                    if (!byVehicle[vid]) {
                        // label = "Driver Name / Plate"
                        const plate = r.vehicle_id[1] || "";
                        const label = [r.driver_name, plate].filter(Boolean).join(" / ");
                        byVehicle[vid] = { label, recs: [] };
                    }
                    byVehicle[vid].recs.push(r);
                }

                const result = await this.orm.call("mss_route_optimization.user.registration", "search_read", [[]], { fields: ["usage_display"], limit: 1 });
                this.usageDisplay = result.length ? result[0].usage_display : "Usage info not found";
                
                // Insert banner just once under control panel
                const controlPanel = document.querySelector(".o_control_panel");
                if (controlPanel && !document.querySelector(".custom-usage-banner")) {
                    const banner = document.createElement("div");
                    banner.className = "custom-usage-banner";
                    banner.innerText = `Usage Info: you have used ${this.usageDisplay} optimization credits this month.`;
            
                    // Insert after control panel
                    controlPanel.insertAdjacentElement("afterend", banner);
                }
                if (this.modelName === "traktop") {
                    const controlPanel = document.querySelector(".o_control_panel");
                    if (controlPanel && !document.querySelector(".custom-usage-banner")) {
                      const banner = document.createElement("div");
                      banner.className = "custom-usage-banner alert alert-info mt-2";
                      banner.innerText = `You have used ${this.usageDisplay} optimization credits this month.`;
                      controlPanel.insertAdjacentElement("afterend", banner);
                    }
                  }
                  
                const isAdmin = await this.orm.call("traktop", "is_admin", []);
                if (isAdmin) {
                    // Create "Optimization" button
                    const optimizationBtn = document.createElement("button");
                    optimizationBtn.textContent = "Optimization";
                    optimizationBtn.className = "btn btn-primary btn-sm o_map_btn";
                    Object.assign(optimizationBtn.style, {
                        marginBottom: "5px",
                        fontSize: "15px",
                    });
                   
                    // Event listener for Optimization button
                    optimizationBtn.addEventListener("click", async () => {
                        try {
                            const response = await this.orm.call("traktop", "get_optimized_rec_created", []);
                            console.log("Optimization response:", response);
                            if (response && response.params) {
                                const { title, message, type, sticky, next } = response.params;
                                this.notification.add(message, {
                                    title: title,
                                    type: type,
                                    sticky: sticky,
                                });
                        
                                if (next && next.type === 'ir.actions.client' && next.tag === 'reload') {
                                    location.reload(); // Reload the page
                                }
                            } else if (response && response.type === "ir.actions.act_window") {
                                await this.env.services.action.doAction(response);
                            }
                        } catch (error) {
                            console.error("Error during optimization:", error);
                            // if (error instanceof FetchRecordError) {
                            //     this.notification.add(
                            //         _t("Some records were not found or might have been deleted. Please verify."),
                            //         { title: _t("Error"), type: "danger" }
                            //     );
                            // } else {
                            //     this.notification.add(
                            //         _t("Optimization failed. Please try again."),
                            //         { title: _t("Error"), type: "danger" }
                            //     );
                            // }
                        }
                        
                    });

                    // Append the optimization button above the routes
                    const btnWrapper = document.createElement("div");
                    btnWrapper.appendChild(optimizationBtn);
                    this.recordList.el.appendChild(btnWrapper);
                }
            


                // 5) iterate each vehicle group
                for (const [vid, { label: vehLabel, recs }] of Object.entries(byVehicle)) {
                    // sort according to your sequence
                    recs.sort((a, b) => a.route_sequence - b.route_sequence);

                    // find any start/end steps
                    const startRec = recs.find(r => r.step_type === "start");
                    const endRec   = recs.find(r => r.step_type === "end");
                    // always get the job steps
                    const jobs     = recs.filter(r => r.step_type === "job");
                    if (!jobs.length) {
                        console.warn(`Vehicle "${vehLabel}" has no jobs, skipping.`);
                        continue;
                    }

                    const bounds = new google.maps.LatLngBounds();
                    const color  = getRandomColor();

                    // --- build sidebar header ---
                    const hdr = document.createElement("li");
                    hdr.textContent = vehLabel;
                    Object.assign(hdr.style, {
                        fontWeight: "bold",
                        color,
                        cursor: "pointer",
                        margin: "10px 0 5px",
                        listStyle: "none",
                    });
                    const arrow = document.createElement("span");
                    arrow.textContent = " ▼";
                    hdr.appendChild(arrow);                    

                    const detailUl = document.createElement("ul");
                    Object.assign(detailUl.style, {
                        listStyle: "none",
                        paddingLeft: "15px",
                        display: "none",
                    });

                    hdr.addEventListener("click", () => {
                        const show = detailUl.style.display === "none";
                        detailUl.style.display = show ? "block" : "none";
                        arrow.textContent = show ? " ▲" : " ▼";
                        this.map.fitBounds(bounds);
                    });
                    
                    
                    if(!isAdmin) {
                        const gmapsBtn = document.createElement("button");
                        gmapsBtn.textContent = "View in Google Maps";
                        gmapsBtn.className = "btn btn-primary btn-sm o_map_btn";  // Using Odoo default color (blue primary)
                        
                        Object.assign(gmapsBtn.style, {
                            marginBottom: "5px",
                            fontSize: "15px",
                        });
                        
                        const btnWrapper = document.createElement("div");
                        btnWrapper.appendChild(gmapsBtn);
                        this.recordList.el.appendChild(btnWrapper); // This places the button *above* the routes
                        gmapsBtn.addEventListener("click", () => {
                            const points = [];

                            if (startPt) points.push(`${startPt.lat},${startPt.lng}`);
                            for (const job of jobs) {
                                points.push(`${+job.partner_latitude},${+job.partner_longitude}`);
                            }
                            if (endPt) points.push(`${endPt.lat},${endPt.lng}`);

                            if (points.length >= 2) {
                                const origin = points[0];
                                const destination = points[points.length - 1];
                                const waypoints = points.slice(1, points.length - 1).join("|");

                                let url = `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}`;
                                if (waypoints) {
                                    url += `&waypoints=${encodeURIComponent(waypoints)}`;
                                }

                                window.open(url, "_blank");
                            } else {
                                this.notification.add("Not enough route points to open Google Maps", {
                                    type: "warning",
                                });
                            }
                        });
                    }
                    this.recordList.el.appendChild(hdr);
                    this.recordList.el.appendChild(detailUl);

                    // 6) determine actual start/end coordinates
                    let startPt, endPt;
                    if (startRec && endRec) {
                        startPt = {
                            lat: +startRec.partner_latitude,
                            lng: +startRec.partner_longitude,
                        };
                        endPt = {
                            lat: +endRec.partner_latitude,
                            lng: +endRec.partner_longitude,
                        };
                    } else {
                        // fallback to vehicleData entry
                        const vinfo = vehicleData.find(v => v.id === +vid);
                        if (vinfo) {
                            // vinfo.start is [lng, lat]
                            startPt = { lat: vinfo.start[1], lng: vinfo.start[0] };
                            endPt   = { lat: vinfo.end[1],   lng: vinfo.end[0]   };
                        }
                    }

                    // 7) draw start/end markers (real or fallback)
                    if (startPt) {
                        bounds.extend(startPt);
                        addMarker(startPt, `Start ${vehLabel}`, "", null, icons.start);
                    }
                    if (endPt) {
                        bounds.extend(endPt);
                        addMarker(endPt, `End ${vehLabel}`, "", null, icons.end);
                    }

                    // 8) plot job markers + sidebar items
                    let counter = 1;
                    for (const job of jobs) {
                        const lat = +job.partner_latitude;
                        const lng = +job.partner_longitude;
                        bounds.extend({ lat, lng });

                        const m = addMarker(
                            { lat, lng },
                            job.display_name,
                            job.delivery_address,
                            String(counter),
                            icons.job
                        );

                        const li = document.createElement("li");
                        Object.assign(li.style, {
                            cursor: "pointer",
                            marginBottom: "10px",
                            listStyle: "none",
                        });
                        const link = document.createElement("a");
                        link.href = "/web#id=${job.id}&model=sale.order&view_type=form";
                        link.target = "_blank"; // Open the link in a new tab
                        link.innerHTML = job.display_name; // Set the customer display name as link text
                        link.style.fontWeight = "bold"; // Style for the name
                        const adiv = document.createElement("div");
                        adiv.textContent = job.delivery_address;
                        adiv.style.fontSize = "small";
                        adiv.style.color = "#666";
                        li.append(link, adiv);
                        
                        li.addEventListener("click", () => {
                            this.map.panTo({ lat, lng });
                            this.map.setZoom(12);
                            m.infoWindow?.open(this.map, m);
                        });
                        detailUl.appendChild(li);
                        counter++;
                    }

                    // 9) draw the route polyline if we have both ends
                    if (startPt && endPt) {
                        const ds = new google.maps.DirectionsService();
                        const dr = new google.maps.DirectionsRenderer({
                            map: this.map,
                            suppressMarkers: true,
                            polylineOptions: {
                                strokeColor: color,
                                strokeOpacity: 0.8,
                                strokeWeight: 4,
                            },
                        });
                        const waypoints = jobs.map(j => ({
                            location: {
                                lat: +j.partner_latitude,
                                lng: +j.partner_longitude,
                            },
                            stopover: true,
                        }));
                        ds.route(
                            {
                                origin:      startPt,
                                destination: endPt,
                                waypoints,
                                travelMode:  google.maps.TravelMode.DRIVING,
                            },
                            (res, status) => {
                                if (status === google.maps.DirectionsStatus.OK) {
                                    dr.setDirections(res);
                                } else {
                                    console.error("Directions request failed:", status);
                                }
                            }
                        );
                    }
                }
            } catch (err) {
                console.error("Error loading route data:", err);
                this.notification.add(_t("Failed to load route data."), {
                    type: "danger",
                });
            }

            // Mobile toggle button to show/hide the sidebar
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            const mapLeftView = this.recordList.el.parentElement;
            const toggleBtn = document.createElement("div");
            toggleBtn.classList.add("map-toggle-btn-pure");

            this.mapref.el.parentElement.insertBefore(toggleBtn, this.mapref.el);

            let isOpen = false;
            toggleBtn.addEventListener("click", (event) => {
                // Stop the event from bubbling up so the document click doesn't fire immediately.
                event.stopPropagation();
                isOpen = !isOpen;
                mapLeftView.classList.toggle("map-panel-visible", isOpen);
                toggleBtn.classList.toggle("flipped", isOpen);
                toggleBtn.style.left = isOpen ? "calc(70% - 16px)" : "15px";
            });
            function handleResize() {
                const mobile = window.innerWidth <= 768;
                if (mobile) {
                  toggleBtn.style.display = "";           // show
                } else {
                  toggleBtn.style.display = "none";       // hide
                  if (isOpen) {
                    isOpen = false;
                    mapLeftView.classList.remove("map-panel-visible");
                    toggleBtn.classList.remove("flipped");
                  }
                }
              }
              window.addEventListener("resize", handleResize);
              handleResize();
            // Click anywhere else to hide the panel if it's open
            document.addEventListener("click", (e) => {
                if (isOpen && !mapLeftView.contains(e.target) && e.target !== toggleBtn) {
                    isOpen = false;
                    mapLeftView.classList.remove("map-panel-visible");
                    toggleBtn.classList.remove("flipped");
                    toggleBtn.style.left = "15px";
                }
            });

            // OPTIONAL: Hide toggle when top-left menu is opened
            const topLeftMenu = document.querySelector('.o_main_navbar');
            if (topLeftMenu) {
                topLeftMenu.addEventListener("click", () => {
                    toggleBtn.style.display = "none";
                });
            }
        }

            // --- live user locations (unchanged) ---
            let userLiveMarkers = {};
            const updateLive = async () => {
                try {
                    const parts = await this.orm.call("res.partner", "search_read", [
                        [],
                        ["live_latitude", "live_longitude", "name", "id"],
                    ]);
                    // const liveIcon = {
                    //     path: google.maps.SymbolPath.CIRCLE,
                    //     fillColor: "skyblue",
                    //     fillOpacity: 1,
                    //     scale: 8,
                    //     strokeColor: "white",
                    //     strokeWeight: 2,
                    // };
                    const liveIcon = {
                        url: "/mss_route_optimization/static/src/img/box-truck.png", // ✅ Set correct path to your image
                        scaledSize: new google.maps.Size(40, 40), // ✅ Adjust size as needed
                        anchor: new google.maps.Point(20, 20),    // ✅ Center the icon
                    };
                    parts
                        .filter(p => {
                            const la = parseFloat(p.live_latitude);
                            const lo = parseFloat(p.live_longitude);
                            return !isNaN(la) && !isNaN(lo) && la !== 0 && lo !== 0;
                        })
                        .forEach(p => {
                            const pos = { lat: +p.live_latitude, lng: +p.live_longitude };
                            if (userLiveMarkers[p.id]) {
                                userLiveMarkers[p.id].setPosition(pos);
                            } else {
                                userLiveMarkers[p.id] = addMarker(
                                    pos,
                                    p.name,
                                    "",
                                    null,
                                    liveIcon
                                );
                            }
                        });
                } catch (e) {
                    console.error("Live location update error:", e);
                }
            };
            updateLive();
            setInterval(updateLive, 5000);
        });
    }

    async _getGMapAPIKey() {
        if (!this._gmapApiKey) {
            this._gmapApiKey = await this.orm.call(
                "traktop",
                "get_google_map_api_key",
                []
            );
        }
        return this._gmapApiKey;
    }
}

export const addressMultipleMarkersGmap = {
    component: AddressMultipleMarkersGmap,
};
registry.category("fields").add(
    "address_multiple_markers_gmap",
    addressMultipleMarkersGmap
);