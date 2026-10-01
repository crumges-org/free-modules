import { patch } from "@web/core/utils/patch";
import { SearchModel } from "@web/search/search_model";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";

/**
 * Hide search menus the policy restricts (features F3, F4, F7, H11).
 *
 * Named filters and group-bys (F1, F2) and the search panel (F6) are stripped
 * from the view arch on the server, so they never reach the browser. What is
 * left here are the menus the client builds for itself, which have no arch to
 * edit:
 *
 *   - the whole Filters / Group By / Favourites dropdowns, gated on
 *     `searchModel.searchMenuTypes`;
 *   - "Add Custom Group", gated on `searchModel.hideCustomGroupBy`;
 *   - "Custom Filter..." and the favourites' edit icon, gated by getters read
 *     from search_menu_patch.xml.
 */

/** Policy flag -> the searchMenuTypes entry it removes. */
const MENU_FLAGS = [
    ["hide_all_filters", "hide_filter", "filter"],
    ["hide_all_groupby", "hide_group_by", "groupBy"],
    ["hide_favourite", "hide_favourite", "favorite"],
    // Odoo 18 only. v19 removed the Comparison panel entirely; on 18 it is a
    // fourth searchMenuType (search_bar_menu.js:137) that pivot and graph views
    // enable. Without this, a user with all three flags set still gets the search
    // dropdown on those views - `searchMenuTypes.size` is 1, so the whole menu
    // renders, showing only Comparison. Comparison refines a date filter, so it
    // follows the filter toggle.
    ["hide_all_filters", "hide_filter", "comparison"],
];

patch(SearchModel.prototype, {
    /**
     * `load()`, not `setup()`: `this.resModel`, `searchMenuTypes` and
     * `hideCustomGroupBy` are all assigned here, and `setup()` runs before any
     * of them exist. Hooking setup silently applied only the database-wide
     * flags and dropped every per-model one - which no Python test could see,
     * because none of this runs outside a browser.
     */
    async load(config) {
        await super.load(config);

        const aam = this.env?.services?.aam_policy;
        if (!aam || aam.isUnrestricted) {
            return;
        }

        for (const [modelFlag, globalFlag, menuType] of MENU_FLAGS) {
            if (aam.isSearchHidden(this.resModel, modelFlag, globalFlag)) {
                this.searchMenuTypes.delete(menuType);
            }
        }

        if (aam.isSearchHidden(this.resModel, "hide_custom_groupby", "hide_custom_group_by")) {
            this.hideCustomGroupBy = true;
        }
    },
});

patch(SearchBarMenu.prototype, {
    /** Read by the template extension in search_menu_patch.xml. */
    get aamHideCustomFilter() {
        const aam = this.env.services.aam_policy;
        if (!aam || aam.isUnrestricted) {
            return false;
        }
        return aam.isSearchHidden(
            this.env.searchModel.resModel, "hide_custom_filter", "hide_custom_filter");
    },
});

patch(SearchBarMenu.prototype, {
    /**
     * Take the way to delete a saved filter off the favourites (feature F5).
     *
     * Read by the FavoriteItem extension in search_menu_patch.xml.
     *
     * Odoo 18 puts a delete (trash) icon on every favourite; 19 and 20 replace
     * it with an "Edit favorite" icon whose form can delete it. This replaces
     * a `_createGroupOfFavorites` patch that set `item.removable = false`,
     * which nothing in `web/static/src` reads on any of the three versions.
     *
     * Favourites are `ir.filters` records, so a user who may not remove one is
     * stopped by ordinary access rights anyway - this stops the interface
     * offering a way in that would then fail.
     */
    get aamHideDeleteFilter() {
        const aam = this.env.services.aam_policy;
        if (!aam || aam.isUnrestricted) {
            return false;
        }
        return aam.isSearchHidden(
            this.env.searchModel.resModel, "hide_delete_filter", "hide_delete_filter");
    },
});
