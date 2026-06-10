/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListDashboard } from "../js/list_dashboard";
import { evaluateExpr } from "@web/core/py_js/py";

export class IspgDashboardRenderer extends ListRenderer {
    setup() {
        super.setup(...arguments);
        this.dashboardConfig = this.parseDashboardMeta();
    }

    parseDashboardMeta() {
        // The server (ir.ui.view._postprocess_tag_list) translates the
        // <listdashboard> tag into a JSON attribute on the <list> root node.
        const listNode = this.props.archInfo?.xmlDoc;
        if (!listNode || typeof listNode.getAttribute !== "function") {
            return null;
        }

        const rawData = listNode.getAttribute("ispg_dashboard_data");
        if (!rawData) {
            return null;
        }

        try {
            const parsed = JSON.parse(rawData);
            const normalizeCard = (card) => ({
                title: card.title || "KPI",
                user_field: card.user_field || "user_id",
                color: card.color || "",
                icon: card.icon || "",
                symbol: card.symbol || "",
                measure: card.measure || "",
                aggregate: card.aggregate || "sum",
                // Domains are stored as Python-style strings; evaluate them
                // into a real domain array (handles tuples, today(), etc.).
                domain: card.domain ? evaluateExpr(card.domain) : [],
            });
            // Current shape: array of {title, cards}. Tolerate legacy shapes:
            // an array of card-arrays, or a flat array of cards.
            let rawRows;
            if (parsed[0] && Array.isArray(parsed[0].cards)) {
                rawRows = parsed;
            } else if (Array.isArray(parsed[0])) {
                rawRows = parsed.map((cards) => ({ title: "", cards }));
            } else {
                rawRows = [{ title: "", cards: parsed }];
            }
            const rows = rawRows.map((row) => ({
                title: row.title || "",
                cards: (row.cards || []).map(normalizeCard),
            }));
            return { rows };
        } catch (e) {
            console.error("Failed to parse ISPG Dashboard metadata:", e);
        }
        return null;
    }
}

IspgDashboardRenderer.components = { ...ListRenderer.components, ListDashboard };

registry.category("views").add("ispg_dashboard", {
    ...listView,
    Renderer: IspgDashboardRenderer,
});