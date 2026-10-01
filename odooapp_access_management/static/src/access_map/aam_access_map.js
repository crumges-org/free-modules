import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Access Map: what a security group can actually do.
 *
 * Groups on the left; for the selected one, its members, the model/CRUD matrix,
 * and a "cannot do" summary derived from live rights rather than written by
 * hand. A hand-written security summary goes stale the first time an ACL
 * changes, and a stale one is worse than none.
 *
 * This reports *native* Odoo rights. For what this module's own rules add on
 * top, and which rule caused each effect, use the Access Explainer.
 */
export class AamAccessMap extends Component {
    static template = "odooapp_access_management.AccessMap";
    // The action service adds props of its own - `globalState` when you come
    // back through a breadcrumb, `state` when the URL carries one. Listing them
    // by hand meant returning to the screen threw *"unknown key 'globalState'"*
    // in dev mode; the exported schema stays right across releases.
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            groups: [],
            groupFilter: "",
            modelFilter: "",
            scope: "relevant",
            selectedId: null,
            detail: null,
            detailLoading: false,
        });
        onWillStart(async () => {
            this.state.groups = await this.orm.call(
                "aam.dashboard", "get_access_map_groups", []);
            this.state.loading = false;
            if (this.state.groups.length) {
                await this.select(this.state.groups[0].id);
            }
        });
    }

    get visibleGroups() {
        const needle = this.state.groupFilter.trim().toLowerCase();
        if (!needle) {
            return this.state.groups;
        }
        return this.state.groups.filter(
            (g) =>
                g.name.toLowerCase().includes(needle) ||
                g.area.toLowerCase().includes(needle) ||
                g.xmlid.toLowerCase().includes(needle)
        );
    }

    get visibleModels() {
        const rows = this.state.detail?.models || [];
        const needle = this.state.modelFilter.trim().toLowerCase();
        if (!needle) {
            return rows;
        }
        // Match label and technical id alike: administrators know a model by
        // one or the other, rarely both.
        return rows.filter(
            (r) =>
                (r.name || "").toLowerCase().includes(needle) ||
                r.model.toLowerCase().includes(needle)
        );
    }

    async select(groupId) {
        this.state.selectedId = groupId;
        this.state.detailLoading = true;
        try {
            this.state.detail = await this.orm.call(
                "aam.dashboard", "get_access_map_detail", [groupId, this.state.scope]);
        } finally {
            this.state.detailLoading = false;
        }
    }

    async setScope(scope) {
        this.state.scope = scope;
        if (this.state.selectedId) {
            await this.select(this.state.selectedId);
        }
    }

    statusLabel(status) {
        return {
            full: _t("Full"),
            partial: _t("Partial"),
            readonly: _t("Read only"),
            none: _t("None"),
        }[status] || status;
    }

    exportExcel() {
        this.action.doAction("odooapp_access_management.action_aam_groups_export");
    }

    explain() {
        this.action.doAction("odooapp_access_management.action_aam_explain");
    }
}

registry.category("actions").add("odooapp_access_management.access_map", AamAccessMap);
