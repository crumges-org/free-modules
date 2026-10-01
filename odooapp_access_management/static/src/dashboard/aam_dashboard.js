import { Component, onWillStart, useState } from "@odoo/owl";
import { AamChart } from "./aam_chart";
import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Access Management dashboard.
 *
 * The restriction matrix is the hero rather than a row of KPI tiles: for
 * administrators and auditors, the *shape* of restrictions across models is
 * the thing worth seeing first. Counts sit above it as a thin strip.
 *
 * All figures come from `aam.dashboard` on the server. The client never reads
 * rules, groups or ACL rows directly - handing that data to the browser is
 * exactly what an access-management module should not do.
 */
export class AamDashboard extends Component {
    static template = "odooapp_access_management.Dashboard";
    // The action service adds props of its own - `globalState` when you come
    // back through a breadcrumb, `state` when the URL carries one. Listing them
    // by hand meant returning to the screen threw *"unknown key 'globalState'"*
    // in dev mode; the exported schema stays right across releases.
    static props = { ...standardActionServiceProps };
    static components = { AamChart };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, data: null, error: null });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const [data, heatmap] = await Promise.all([
                this.orm.call("aam.dashboard", "get_dashboard_data", []),
                this.orm.call("aam.dashboard", "get_heatmap_data", []),
            ]);
            this.state.data = data;
            this.state.heatmap = heatmap;
        } catch (error) {
            this.state.error = error.message?.data?.message || _t("Could not load the dashboard.");
        } finally {
            this.state.loading = false;
        }
    }

    /* -- tiles ---------------------------------------------------------- */

    /** How each count reads: an identity gradient, an icon, a severity and a
     *  one-line caption.
     *
     *  The gradient and the severity do different jobs, which is the whole
     *  point of splitting them. The gradient is *identity* - "Expiring soon" is
     *  the orange one, always, whatever it counts - and it is what makes ten
     *  tiles scannable. The severity is *state*, and it only fires when the
     *  number means something is wrong.
     *
     *  Neither is ever the sole carrier: the label and the caption say the same
     *  thing in words, so the strip is legible in greyscale.
     */
    tileMeta(tile) {
        const META = {
            total:          ["info",    "brand",  "fa-shield",         _t("in this database")],
            active:         ["ok",      "teal",   "fa-check-circle",   _t("enforcing now")],
            inactive:       ["neutral", "grey",   "fa-pause-circle",   _t("switched off")],
            expiring:       ["warn",    "orange", "fa-hourglass-half", _t("within 7 days")],
            expired:        ["bad",     "red",    "fa-times-circle",   _t("past their end date")],
            user_rules:     ["info",    "blue",   "fa-user",           _t("targeted directly")],
            group_rules:    ["info",    "purple", "fa-users",          _t("through a group")],
            group_profile:  ["info",    "cyan",   "fa-id-badge",       _t("through a profile")],
            time_based:     ["warn",    "orange", "fa-clock-o",        _t("only in a time window")],
            login_disabled: ["bad",     "red",    "fa-ban",            _t("users cannot log in")],
        };
        const [severity, accent, icon, caption] =
            META[tile.key] || ["neutral", "grey", "fa-circle-o", ""];
        return {
            // A zero is not trouble. Without this a clean database opened with
            // two red tiles and two amber ones, all of them reading 0, which is
            // exactly backwards.
            severity: !tile.value && (severity === "bad" || severity === "warn")
                ? "quiet"
                : severity,
            accent,
            icon,
            // `pct` is computed server-side for the four share-of-total tiles.
            caption: tile.pct === null || tile.pct === undefined
                ? caption
                : _t("%s%% of all rules", tile.pct),
        };
    }

    /* -- activity list --------------------------------------------------- */

    /** Icon and gradient for one audit entry.
     *
     *  Keyed on `event_type`, the raw selection value, never on `event`, which
     *  is the *translated* label - this module ships five languages and an icon
     *  map keyed on display text would silently fall back to the default on
     *  four of them.
     */
    eventMeta(log) {
        const META = {
            denial:        ["red",    "fa-ban"],
            login:         ["teal",   "fa-sign-in"],
            logout:        ["grey",   "fa-sign-out"],
            login_blocked: ["orange", "fa-lock"],
            impersonate:   ["purple", "fa-user-secret"],
        };
        const [accent, icon] = META[log.event_type] || ["grey", "fa-circle-o"];
        return { accent, icon };
    }

    /* -- top users ------------------------------------------------------- */

    /** Up to two initials, so a 36px circle is never asked to hold a name. */
    initials(name) {
        const parts = (name || "?").trim().split(/\s+/).slice(0, 2);
        return parts.map((part) => part.charAt(0).toUpperCase()).join("");
    }

    /** A stable hue per user id. The same person keeps the same colour between
     *  reloads, which is the only thing that makes an avatar colour useful. */
    avatarHue(id) {
        return (id * 137) % 360;   // 137deg ~ the golden angle: adjacent ids land far apart
    }

    /** Share of the busiest user, so the bars read as a ranking without anyone
     *  having to compare two numbers. Floored at 6% so the smallest bar is
     *  still visible as a bar. */
    userBarPct(user) {
        const top = Math.max(...(this.state.data?.top_users || []).map((u) => u.value), 1);
        return Math.max(6, Math.round((user.value * 100) / top));
    }

    /* -- health score ---------------------------------------------------- */

    /** The 0-100 score the server already computes. Rendered as a ring rather
     *  than a number alone: a bare "92" says nothing about the range it sits in. */
    get score() {
        const value = this.state.data?.insights?.score;
        if (value === null || value === undefined) {
            return null;
        }
        const band = value >= 85 ? "ok" : value >= 60 ? "warn" : "bad";
        return {
            value,
            band,
            // Stroke offset for an r=26 ring (circumference 163.36).
            dash: (163.36 * value) / 100,
            label: band === "ok" ? _t("Healthy")
                : band === "warn" ? _t("Needs attention")
                : _t("At risk"),
        };
    }

    /* -- charts ---------------------------------------------------------- */

    /** `_created_trend` uses `_read_group`, which omits months that have no
     *  rules. A line with a missing February does not read as "zero", it reads
     *  as "February did not happen" - so fill the six-month grid before
     *  plotting. Client-side on purpose: no server change, no migration risk. */
    get trendPoints() {
        const raw = this.state.data?.created_trend || [];
        if (this._trendFrom !== raw) {
            this._trendFrom = raw;
            const byKey = new Map(raw.map((point) => [point.label, point.value]));
            const now = new Date();
            const out = [];
            for (let back = 5; back >= 0; back--) {
                const at = new Date(now.getFullYear(), now.getMonth() - back, 1);
                const key = `${at.getFullYear()}-${String(at.getMonth() + 1).padStart(2, "0")}`;
                out.push({
                    label: at.toLocaleDateString(undefined, { month: "short" }),
                    value: byKey.get(key) ?? 0,
                });
            }
            this._trend = out;
        }
        return this._trend;
    }

    /* -- matrix ---------------------------------------------------------- */

    /** Which family a heatmap column belongs to.
     *
     *  The cells stay on one sequential hue - a heatmap encodes magnitude, and
     *  a multi-hue ramp would destroy the comparison it exists to support. The
     *  colour goes on the *column headers* instead, where it groups seventeen
     *  columns into four ideas you can actually hold in your head: what the
     *  rule blocks, what it stops leaving the system, what it hides in the UI,
     *  and which records it applies to.
     */
    columnGroup(key) {
        const GROUPS = {
            read: "crud", write: "crud", create: "crud", unlink: "crud",
            import: "flow", export: "flow", print: "flow", duplicate: "flow",
            readonly: "ui", field_hide: "ui", field_mask: "ui", view_hide: "ui",
            archive: "ui", button: "ui", search: "ui", chatter: "ui",
            domain: "records",
        };
        return GROUPS[key] || "ui";
    }

    /** Density band for a cell, 0-5. Buckets, not a gradient, so the eye can
     *  compare two cells without measuring them. */
    level(count) {
        if (!count) return 0;
        if (count === 1) return 1;
        if (count === 2) return 2;
        if (count <= 4) return 3;
        if (count <= 7) return 4;
        return 5;
    }

    get verdict() {
        const insights = this.state.data?.insights;
        if (!insights) return { text: "", bad: false };
        if (!insights.enabled) {
            return { text: _t("Switched off — no rule is doing anything."), bad: true };
        }
        if (!insights.admin_protected) {
            return { text: _t("Administrator protection is off."), bad: true };
        }
        return {
            text: _t("%s models covered, %s users affected.",
                     insights.models_covered, insights.users_affected),
            bad: false,
        };
    }

    openRules(filter) {
        const context = {};
        if (filter) {
            context[`search_default_${filter}`] = 1;
        }
        this.action.doAction("odooapp_access_management.action_aam_rule", {
            additionalContext: context,
        });
    }

    openModelRules(model) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Rules affecting %s", model),
            res_model: "aam.rule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: ["|", "|", "|",
                ["model_line_ids.model_name", "=", model],
                ["field_line_ids.model_name", "=", model],
                ["button_line_ids.model_name", "=", model],
                ["chatter_line_ids.model_name", "=", model]],
        });
    }

    openAccessMap() {
        this.action.doAction("odooapp_access_management.action_aam_access_map");
    }

    openAuditLog() {
        this.action.doAction("odooapp_access_management.action_aam_audit_log");
    }
}

registry.category("actions").add("odooapp_access_management.dashboard", AamDashboard);
