import { registry } from "@web/core/registry";
import { session } from "@web/session";

/**
 * Client-side view of the compiled access policy.
 *
 * The policy arrives with `session_info` rather than through an RPC, because
 * the web client needs it before the first view renders - fetching it later
 * would show a flash of un-restricted UI before things disappeared.
 *
 * This is presentation only. Every restriction here is also enforced on the
 * server, so a user who bypasses the browser gains nothing.
 */

const EMPTY = {
    globals: {},
    menus: [],
    models: {},
    fields: {},
    buttons: {},
    search: {},
    chatter: {},
    reports: [],
    actions: [],
    views: [],
};

/*
 * There is no view-cache bust on Odoo 18, deliberately.
 *
 * The Odoo 19 build of this file cleared the browser's *persistent* view cache
 * whenever the policy fingerprint moved: v19's `viewService` keeps `get_views`
 * archs in IndexedDB and invalidates them only when `ir.ui.view` or `ir.filters`
 * is written - and assigning a profile writes neither, so the browser kept
 * serving an arch fetched before the restriction existed, across a full reload.
 *
 * Odoo 18 cannot reproduce that. There is no `rpc.setCache`, no `rpc_cache.js`
 * and no IndexedDB anywhere in web/static/src; `view_service.js:47` is a plain
 * in-memory `let cache = {}` scoped to the page load and cleared on the
 * `env.bus` "CLEAR-CACHES" event (`:56`). A reload starts from an empty cache,
 * and the policy itself only changes through a server-side write, which the
 * open page cannot see without reloading anyway. `rpcBus` has no "CLEAR-CACHES"
 * listener here at all, so porting the call would have been a silent no-op
 * dressed up as a safeguard.
 */

export const aamPolicyService = {
    start() {
        const policy = session.aam_policy || EMPTY;

        const globals = policy.globals || {};

        /** A user-wide toggle, e.g. `isGlobal("hide_export")`. */
        function isGlobal(flag) {
            return Boolean(globals[flag]);
        }

        /** Restrictions for one model, never null. */
        function forModel(resModel) {
            return (policy.models && policy.models[resModel]) || {};
        }

        function searchFor(resModel) {
            return (policy.search && policy.search[resModel]) || {};
        }

        function chatterFor(resModel) {
            return (policy.chatter && policy.chatter[resModel]) || {};
        }

        /**
         * True when `flag` is set either globally or for this model.
         * Most restrictions can be expressed at both levels, and the answer the
         * UI needs is always "either one".
         */
        function isHidden(resModel, flag) {
            return isGlobal(flag) || Boolean(forModel(resModel)[flag]);
        }

        function isSearchHidden(resModel, flag, globalFlag) {
            return isGlobal(globalFlag || flag) || Boolean(searchFor(resModel)[flag]);
        }

        return {
            policy,
            isGlobal,
            forModel,
            searchFor,
            chatterFor,
            isHidden,
            isSearchHidden,
            /** True when the user has no restrictions at all - lets patches bail early. */
            get isUnrestricted() {
                return (
                    !Object.values(globals).some(Boolean) &&
                    !Object.keys(policy.models || {}).length &&
                    !Object.keys(policy.fields || {}).length &&
                    !Object.keys(policy.search || {}).length &&
                    !Object.keys(policy.chatter || {}).length
                );
            },
        };
    },
};

registry.category("services").add("aam_policy", aamPolicyService);
