import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { exportAllItem } from "@web/views/list/export_all/export_all";

/**
 * Remove restricted entries from the cog menu (features B3-B9, H4-H8).
 *
 * Filtering happens in `actionMenuItems`, the getter that assembles the final
 * list, rather than in `getStaticActionMenuItems` where the entries are
 * contributed. That is deliberate: other modules patch
 * `getStaticActionMenuItems` too, and whoever is patched *last* runs
 * *outermost* - so an entry added by a later patch lands on top of whatever we
 * returned and is never seen. Enterprise's `spreadsheet_edition` does exactly
 * that, which is how "Insert in spreadsheet" survived a filter that named its
 * key correctly. `actionMenuItems` runs after every contributor.
 *
 * The matching server-side blocks live in `ir.model.access._get_allowed_models`
 * and the toolbar filter in `ir.actions.actions.get_bindings`; this only stops
 * the UI offering an action that would then fail.
 */

/** Policy flag that hides each cog entry, by its item key. */
const ITEM_FLAGS = {
    export: "hide_export",
    duplicate: "hide_duplicate",
    archive: "hide_archive",
    unarchive: "hide_archive",
    delete: "hide_delete",
    // Enterprise only: `spreadsheet_edition` adds "Insert in spreadsheet" to
    // the list and kanban controllers under this key. It is a static item, not
    // a cogMenu registry item - only the pivot/graph variant goes through the
    // registry, and that one is gated in `cog_registry_patch.js`.
    insert: "hide_spreadsheet",
    // The form cog's "Add Properties" (form_controller.js:540 on 18, :512 on 19)
    // is the same schema change as the in-field Add button that H6 already gates,
    // so it follows the same flag. Ungated on both versions until now.
    addPropertyFieldValue: "hide_add_property",
};

/**
 * Drop restricted entries from an assembled `actionMenuItems` value.
 *
 * Server-side toolbar actions share the `action` list but are keyed by database
 * id, so they never collide with the string keys above; they are filtered on
 * the server by `ir.actions.actions.get_bindings`.
 */
function filterActionMenuItems(items, aam, resModel) {
    if (!aam || aam.isUnrestricted || !items?.action) {
        return items;
    }
    const model = aam.forModel(resModel);
    const blocked = model.blocked || [];

    // "Hide Action (cog) Menu" says the whole menu goes, so take the static
    // entries too. Clearing only the server-side toolbar actions - which is all
    // `ir.actions.actions.get_bindings` can reach - left the cog on screen with
    // Export, Duplicate and Archive still in it. This is also the one gate that
    // covers entries contributed by apps this module has never heard of.
    //
    // `print` goes as well. The comment this replaces claimed v19 puts reports
    // "in the same cog"; it does not, and neither does v18 -
    // web/static/src/search/action_menus/action_menus.xml is byte-identical in
    // the two trees and renders two dropdowns, a Print button gated on
    // `props.items.print?.length` and a separate Actions cog. So clearing `print`
    // removes the *Print* button, on both versions. That is still the right
    // behaviour for a switch labelled "Hide Action (cog) Menu" - it is what the
    // observed `mrp.bom` symptom actually was - but it is worth naming correctly.
    if (aam.isHidden(resModel, "hide_action_button")) {
        return { ...items, action: [], print: [] };
    }

    const allowed = items.action.filter((item) => {
        const flag = ITEM_FLAGS[item.key];
        if (flag && (aam.isGlobal(flag) || model[flag])) {
            return false;
        }
        // "Delete" and "Duplicate" have no dedicated toggle of their own: they
        // follow the model's unlink and create blocks.
        if (item.key === "delete" && blocked.includes("unlink")) {
            return false;
        }
        if (item.key === "duplicate" && blocked.includes("create")) {
            return false;
        }
        return true;
    });

    return { ...items, action: allowed };
}

patch(FormController.prototype, {
    get actionMenuItems() {
        return filterActionMenuItems(
            super.actionMenuItems,
            this.env.services.aam_policy,
            this.props.resModel
        );
    },
});

patch(ListController.prototype, {
    get actionMenuItems() {
        return filterActionMenuItems(
            super.actionMenuItems,
            this.env.services.aam_policy,
            this.props.resModel
        );
    },
});

// No kanban cog patch on Odoo 18, deliberately. Odoo 19's KanbanController has
// `actionMenuItems` (:255) and `getStaticActionMenuItems` (:378) and renders
// <ActionMenus> when records are selected; v18's has neither, and v18 kanban has
// no record selection at all - `kanban_controller.xml:34` is a bare <CogMenu/>
// holding registry items only. Patching it here would define a getter nobody
// calls. Nothing is lost: there is no static Export / Duplicate / Archive /
// Delete surface on v18 kanban to hide, and the registry entries that *are*
// there stay gated by cog_registry_patch.js.

// "Export All" is a separate cogMenu registry item rather than a static entry,
// so it needs its own gate. isDisplayed is async in core, so keep it async.
const originalExportAllIsDisplayed = exportAllItem.isDisplayed;
exportAllItem.isDisplayed = async (env) => {
    const aam = env.services.aam_policy;
    if (aam && !aam.isUnrestricted && aam.isHidden(env.config.resModel, "hide_export")) {
        return false;
    }
    return originalExportAllIsDisplayed(env);
};
