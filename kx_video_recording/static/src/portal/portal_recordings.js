/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

const STORAGE_KEY = "kx_portal_recording_view";

publicWidget.registry.KxPortalRecordingsView = publicWidget.Widget.extend({
    selector: ".o_kx_portal_recordings",

    events: {
        "click .o_kx_view_btn": "_onViewBtnClick",
    },

    /**
     * @param {string} view
     */
    _setView(view) {
        const mode = view === "list" ? "list" : "kanban";
        this.el.classList.toggle("o_kx_view_kanban", mode === "kanban");
        this.el.classList.toggle("o_kx_view_list", mode === "list");
        for (const btn of this.el.querySelectorAll(".o_kx_view_btn")) {
            btn.classList.toggle("active", btn.dataset.view === mode);
            btn.setAttribute("aria-pressed", btn.dataset.view === mode ? "true" : "false");
        }
    },

    _onViewBtnClick(ev) {
        ev.preventDefault();
        const view = ev.currentTarget.dataset.view;
        if (!view) {
            return;
        }
        this._setView(view);
        try {
            localStorage.setItem(STORAGE_KEY, view);
        } catch {
            /* private browsing */
        }
    },

    start() {
        let stored = "kanban";
        try {
            stored = localStorage.getItem(STORAGE_KEY) || stored;
        } catch {
            /* noop */
        }
        this._setView(stored);
        return this._super(...arguments);
    },
});

export default publicWidget.registry.KxPortalRecordingsView;
