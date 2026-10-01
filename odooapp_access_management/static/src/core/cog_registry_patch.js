import { registry } from "@web/core/registry";

/**
 * Hide whole cogMenu entries contributed by other modules (B6, B7, H4, H9).
 *
 * The Import, Insert-in-Spreadsheet and Add-to-Dashboard entries are separate
 * registry items rather than part of `getStaticActionMenuItems`, so the
 * controller patch does not reach them.
 *
 * Rather than name each one, wrap every matching item's `isDisplayed` with a
 * policy check. Nothing breaks if a key is absent - which matters because
 * Insert-in-Spreadsheet only exists on Enterprise.
 *
 * Matched by pattern, not by exact key. An earlier version listed exact names
 * and three of the five were wrong: Enterprise registers one
 * `spreadsheet-cog-menu` rather than the per-view keys that were guessed, and
 * `board` registers `add-to-board`, not `add-to-board-menu`. Nothing failed
 * loudly - the toggles were simply inert, on the edition where they matter
 * most. A pattern survives that kind of rename.
 */

/** [key matcher, policy flag that hides it]. First match wins. */
const GATED_ITEMS = [
    // base_import, on both editions.
    [/^import-menu$/, "hide_import"],
    // Enterprise `spreadsheet_edition`; keep it broad so per-view variants,
    // present or future, are covered by the same toggle.
    [/spreadsheet/, "hide_spreadsheet"],
    // `board` - "Add to my Dashboard" copies a view out of the record it came
    // from, which is the same concern the spreadsheet toggle exists for.
    [/^add-to-board/, "hide_spreadsheet"],
];

const cogMenuRegistry = registry.category("cogMenu");

/** The flag hiding this registry key, or undefined when it is not gated. */
function flagFor(key) {
    const hit = GATED_ITEMS.find(([matcher]) => matcher.test(key));
    return hit && hit[1];
}

function gate(flag, item) {
    if (item.aamGated) {
        return item;
    }
    const original = item.isDisplayed;
    item.isDisplayed = async (env) => {
        const aam = env.services.aam_policy;
        if (aam && !aam.isUnrestricted && aam.isHidden(env.config?.resModel, flag)) {
            return false;
        }
        return original ? original(env) : true;
    };
    item.aamGated = true;
    return item;
}

for (const key of cogMenuRegistry.getEntries().map(([k]) => k)) {
    const flag = flagFor(key);
    if (flag) {
        gate(flag, cogMenuRegistry.get(key));
    }
}

// Items registered after us (module load order is not guaranteed) get wrapped
// as they arrive.
cogMenuRegistry.addEventListener("UPDATE", (ev) => {
    const { key, value, operation } = ev.detail;
    if (operation !== "add" || !value) {
        return;
    }
    const flag = flagFor(key);
    if (flag) {
        gate(flag, value);
    }
});
