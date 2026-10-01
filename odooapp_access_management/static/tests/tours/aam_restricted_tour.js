import { registry } from "@web/core/registry";
// Odoo 18 keeps stepUtils under tour_service/; the flat `@web_tour/tour_utils`
// is a v19 reorganisation of the whole web_tour/static/src/js/ subtree. A
// missing module takes the entire web.assets_tests bundle down, so this one
// line would fail all eight tours, not just this file.
import { stepUtils } from "@web_tour/tour_service/tour_utils";

/**
 * The same screens as `aam_core_views_tour`, seen by a restricted user.
 *
 * Run back to back the two tours are a differential test: every assertion here
 * has a matching positive assertion there, so a step that fails because the
 * element never renders for anybody is told apart from one that fails because
 * the policy did not apply.
 *
 * The rule behind it lives in `tests/test_tours.py`. It deliberately leaves
 * neighbours visible - Archive stays in the cog menu, Filters stays in the
 * search dropdown, Send Message stays in the chatter - so each step has a
 * positive anchor and cannot pass on an empty page.
 *
 * All of this is UI. The server-side half of each restriction is covered in
 * `test_enforcement.py`; the point here is that the browser agrees.
 */
registry.category("web_tour.tours").add("aam_restricted_tour", {
    url: "/odoo/action-base.action_partner_form",
    steps: () => [
        {
            // Odoo 18's `base.action_partner_form` is `kanban,list,form`, so it
            // opens on kanban; Odoo 19 reordered it to `list,kanban,form`.
            // Everything below is list-specific - row selectors, the cog's
            // data-hotkey='u' - so switch explicitly rather than depending on
            // which view the action happens to default to.
            content: "Switch to the list view",
            trigger: ".o_cp_switch_buttons .o_switch_view.o_list",
            run: "click",
        },
        {
            content: "The list view renders",
            trigger: ".o_list_view .o_data_row",
        },
        {
            content: "Open the search dropdown",
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            content: "Filters survive, Group By is gone (F-series, hide_all_groupby)",
            trigger: ".o_search_bar_menu:has(.o_filter_menu):not(:has(.o_group_by_menu))",
        },
        {
            content: "…and so is the Custom Filter entry (hide_custom_filter)",
            trigger: ".o_search_bar_menu .o_filter_menu:not(:has(.o_add_custom_filter))",
        },
        {
            // The favourite itself is the positive anchor: it must still be
            // listed and usable, only the way into its edit form is gone.
            content: "The favourite is listed without its delete icon (hide_delete_filter)",
            trigger: ".o_favorite_menu .o_menu_item:contains('AAM Tour Favourite'):not(:has(i.fa-trash-o))",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            content: "Select every row so the list cog menu appears",
            trigger: "thead .o_list_record_selector input",
            run: "click",
        },
        {
            content: "Open the list cog menu",
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },
        {
            // Archive is a real anchor here: the fixture user has
            // `base.group_allow_export`, so Export would genuinely be on offer
            // if the policy were not removing it.
            content: "Archive stayed, Export and Duplicate did not (B5, B4)",
            trigger: ".o-dropdown--menu:has(.o_menu_item:contains(Archive))" +
                ":not(:has(.o_menu_item:contains(Export)))" +
                ":not(:has(.o_menu_item:contains(Duplicate)))",
        },
        {
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },
        {
            content: "Clear the selection",
            trigger: "thead .o_list_record_selector input:checked",
            run: "click",
        },
        {
            content: "Open a record",
            trigger: ".o_data_row:contains(AAM Tour Contact) .o_data_cell:first",
            run: "click",
        },
        {
            // Not `textarea:value(...)`: which tag the name field renders as
            // depends on its widget, and installing `partner_autocomplete`
            // swaps the textarea for an input. Assert that the field mounted,
            // then that it is the right record.
            content: "The form renders",
            trigger: ".o_form_view .o_field_widget[name='name']",
        },
        {
            trigger: ".o_last_breadcrumb_item:contains(AAM Tour Contact)",
        },
        {
            // Arch injection, not a client-side hide: the field is not in the
            // view the server sent.
            content: "Email survives, Website was stripped from the arch (C1)",
            trigger: ".o_form_view:has(.o_field_widget[name='email']):not(:has(.o_field_widget[name='website']))",
        },
        // H6 (hide_add_property) is covered by `aam_properties_restricted_tour`:
        // `res.partner` has no properties field on Odoo 18.
        {
            content: "Send Message stayed, Log Note did not (G3)",
            trigger: ".o-mail-Chatter:has(.o-mail-Chatter-sendMessage):not(:has(.o-mail-Chatter-logNote))",
        },
        {
            content: "Open the form cog menu",
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },
        {
            content: "Duplicate is gone here too",
            trigger: ".o-dropdown--menu:not(:has(.o_menu_item:contains(Duplicate)))",
        },
        {
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },

        // --- Menus (A1): hidden server-side, in `_load_menus_blacklist` ----
        // Community puts the app list behind `.o_navbar_apps_menu`; Enterprise
        // behind the home-menu toggle. `stepUtils` picks the right one - each of
        // its steps carries an `isActive` guard, so the pair is a no-op on the
        // edition it does not apply to.
        ...stepUtils.toggleHomeMenu(),
        ...stepUtils.goToAppSteps(
            "odooapp_access_management.menu_aam_root", "Go to Access Management"),
        {
            content: "Configuration survived, Reporting was blacklisted",
            trigger: ".o_menu_sections" +
                ":has(button[data-menu-xmlid='odooapp_access_management.menu_aam_config'])" +
                ":not(:has([data-menu-xmlid='odooapp_access_management.menu_aam_reporting']))",
        },
    ],
});

/**
 * "Hide Action (cog) Menu" (B9 / H8) takes the whole menu, not just the
 * server-side toolbar actions.
 *
 * Worth its own tour because the flag used to be half-implemented: clearing
 * `ir.actions.actions.get_bindings` removed the bound actions but left the cog
 * on screen with Export, Duplicate and Archive still in it - the opposite of
 * what the label promises. It is also the only gate that reaches cog entries
 * contributed by apps this module knows nothing about.
 */
registry.category("web_tour.tours").add("aam_no_cog_tour", {
    url: "/odoo/action-base.action_partner_form",
    steps: () => [
        {
            // Odoo 18's `base.action_partner_form` is `kanban,list,form`, so it
            // opens on kanban; Odoo 19 reordered it to `list,kanban,form`.
            // Everything below is list-specific - row selectors, the cog's
            // data-hotkey='u' - so switch explicitly rather than depending on
            // which view the action happens to default to.
            content: "Switch to the list view",
            trigger: ".o_cp_switch_buttons .o_switch_view.o_list",
            run: "click",
        },
        {
            content: "The list view renders",
            trigger: ".o_list_view .o_data_row",
        },
        {
            // Selecting rows is what normally brings the cog up, so this is the
            // state in which its absence actually means something.
            content: "Select every row",
            trigger: "thead .o_list_record_selector input",
            run: "click",
        },
        {
            content: "The selection banner is up but the cog menu is not",
            trigger: ".o_control_panel:has(.o_list_selection_box):not(:has(.o_cp_action_menus button[data-hotkey='u']))",
        },
    ],
});
