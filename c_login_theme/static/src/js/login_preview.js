/** @odoo-module **/
// Part of the Codfy module suite for Odoo. See LICENSE file for full terms.
// Copyright (C) 2026 Codfy (https://www.codfy.mx)
// License: LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import { Component, onMounted, onWillUnmount, onWillRender, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useDebounced } from "@web/core/utils/timing";

const DEVICES = {
    desktop: { label: "Computadora", icon: "fa-desktop", width: 1280, height: 800 },
    tablet: { label: "Tableta", icon: "fa-tablet", width: 834, height: 1000 },
    mobile: { label: "Teléfono", icon: "fa-mobile", width: 390, height: 780 },
};

const TEXT_FIELDS = {
    layout: "login_theme_layout",
    card_mode: "login_theme_card_mode",
    primary_color: "login_theme_primary_color",
    bg_start: "login_theme_bg_start",
    bg_end: "login_theme_bg_end",
    headline: "login_theme_headline",
    tagline: "login_theme_tagline",
    footer_note: "login_theme_footer_note",
};

const NUMBER_FIELDS = {
    radius: "login_theme_radius",
    logo_height: "login_theme_logo_height",
    overlay: "login_theme_overlay",
};

const BOOLEAN_FIELDS = {
    use_own_logo: "login_theme_use_own_logo",
    show_reset_password: "login_theme_show_reset_password",
    show_signup: "login_theme_show_signup",
    show_db_selector: "login_theme_show_db_selector",
    show_db_manager: "login_theme_show_db_manager",
};

export class LoginThemePreview extends Component {
    static template = "c_login_theme.LoginThemePreview";
    static props = { "*": true };

    setup() {
        this.devices = DEVICES;
        this.frame = useRef("frame");
        this.state = useState({
            device: "desktop",
            scale: 1,
            url: this.buildUrl(),
        });
        this.refresh = useDebounced(() => {
            const url = this.buildUrl();
            if (url !== this.state.url) {
                this.state.url = url;
            }
        }, 450);
        onWillRender(() => this.refresh());
        onMounted(() => {
            this.observer = new ResizeObserver(() => this.updateScale());
            if (this.frame.el) {
                this.observer.observe(this.frame.el);
            }
            this.updateScale();
        });
        onWillUnmount(() => this.observer && this.observer.disconnect());
    }

    get device() {
        return DEVICES[this.state.device];
    }

    get frameStyle() {
        const { width, height } = this.device;
        return `width:${width}px;height:${height}px;transform:scale(${this.state.scale});`;
    }

    get boxStyle() {
        return `height:${Math.round(this.device.height * this.state.scale)}px;`;
    }

    updateScale() {
        if (!this.frame.el) {
            return;
        }
        const available = this.frame.el.clientWidth;
        const scale = Math.min(1, available / this.device.width);
        if (scale > 0 && Math.abs(scale - this.state.scale) > 0.005) {
            this.state.scale = scale;
        }
    }

    setDevice(device) {
        this.state.device = device;
        this.updateScale();
    }

    buildUrl() {
        const data = this.props.record.data;
        const params = new URLSearchParams();
        for (const [key, field] of Object.entries(TEXT_FIELDS)) {
            params.set(key, data[field] || "");
        }
        for (const [key, field] of Object.entries(NUMBER_FIELDS)) {
            params.set(key, String(data[field] ?? 0));
        }
        for (const [key, field] of Object.entries(BOOLEAN_FIELDS)) {
            params.set(key, data[field] ? "1" : "0");
        }
        return `/c_login_theme/preview?${params.toString()}`;
    }
}

export const loginThemePreview = {
    component: LoginThemePreview,
};

registry.category("view_widgets").add("login_theme_preview", loginThemePreview);
