import { registry } from "@web/core/registry";

/**
 * Stock Odoo views, loaded by a user this module does not restrict.
 *
 * This tour asserts nothing about access control. Its whole job is to prove the
 * module's template extensions still apply cleanly to core templates: a
 * `t-inherit` whose xpath no longer matches raises at *render* time, and takes
 * down every view that uses the template it patched.
 *
 * That is exactly what happened once - `hasclass('o_add_custom_filter')` in the
 * SearchBarMenu extension stopped matching because the target's class is an OWL
 * expression, and every list view in the database went blank while all 74
 * Python tests passed. Python never renders OWL, so only a browser can catch it.
 *
 * `res.partner` is the subject because it exercises the templates this module
 * extends - `web.SearchBarMenu` and `mail.Chatter` - plus both patched
 * controllers, in one form. The third, `web.PropertiesField`, needs a model that
 * has a properties field: see `aam_properties_tour`.
 */
registry.category("web_tour.tours").add("aam_core_views_tour", {
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
            // web.SearchBarMenu, extended by search_menu_patch.xml.
            content: "Open the search dropdown",
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            content: "All three search menus are present for an unrestricted user",
            trigger: ".o_search_bar_menu .o_filter_menu",
        },
        {
            trigger: ".o_search_bar_menu .o_group_by_menu",
        },
        {
            trigger: ".o_search_bar_menu .o_favorite_menu",
        },
        {
            content: "…and so is the entry the template extension guards",
            trigger: ".o_search_bar_menu .o_add_custom_filter",
        },
        {
            // web.SearchBarMenu.FavoriteItem, extended by search_menu_patch.xml.
            // Odoo 18 shows the trash icon at all times and gives the row no
            // `o_favorite_item` class (19 added it), hence `.o_menu_item`. The
            // `:visible` sits on the menu, not the icon, as on 19 and 20, where
            // the icon only appears on hover.
            content: "A favourite keeps its delete icon for an unrestricted user",
            trigger: ".o_favorite_menu:visible .o_menu_item:contains('AAM Tour Favourite') i.fa-trash-o",
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
            // ListController.getStaticActionMenuItems, patched in JS.
            content: "Open the list cog menu",
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },
        {
            content: "Export is offered when nothing restricts it",
            trigger: ".o-dropdown--menu .o_menu_item:contains(Export)",
        },
        {
            content: "…and so is Duplicate",
            trigger: ".o-dropdown--menu .o_menu_item:contains(Duplicate)",
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
            content: "The website field is present for an unrestricted user",
            trigger: ".o_form_view .o_field_widget[name='website']",
        },
        // web.PropertiesField is covered by `aam_properties_tour`, not here:
        // `res.partner` has no `properties` field on Odoo 18 (it arrives in 19
        // via properties.base.definition.mixin), so the host is
        // `project.task.task_properties` instead.
        {
            // mail.Chatter, extended by chatter_patch.xml.
            content: "The chatter renders with all of its controls",
            trigger: ".o-mail-Chatter .o-mail-Chatter-sendMessage",
        },
        {
            trigger: ".o-mail-Chatter .o-mail-Chatter-logNote",
        },
        {
            trigger: ".o-mail-Chatter .o-mail-Followers",
        },
        {
            // FormController.getStaticActionMenuItems, patched in JS.
            content: "Open the form cog menu",
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu .o_menu_item:contains(Duplicate)",
        },
        {
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },
    ],
});
