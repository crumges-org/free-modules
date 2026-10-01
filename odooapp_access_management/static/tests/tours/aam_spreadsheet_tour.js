import { registry } from "@web/core/registry";

/**
 * Insert-in-Spreadsheet, which only exists on Enterprise.
 *
 * Community never ships the entry at all, so the toggle is inert there by
 * design and there was nothing a tour could assert. That made it the one
 * feature in the module with no coverage anywhere - and it was broken twice
 * over: the cog-registry gate named three keys Enterprise does not register,
 * and the list/kanban entry does not come from the registry in the first
 * place. `spreadsheet_edition` patches `getStaticActionMenuItems` and adds it
 * under the key `insert`, which is what `action_menus_patch.js` now gates.
 *
 * Both tours need `documents.group_documents_user`, because that is what turns
 * on `session.can_insert_in_spreadsheet`; without it the entry is absent for
 * everyone and the negative assertion would pass while proving nothing.
 */

const openListCog = [
    {
        // Odoo 18's `base.action_partner_form` is `kanban,list,form`, so it opens
        // on kanban; Odoo 19 reordered it to `list,kanban,form`. Row selection
        // and the cog's data-hotkey='u' are list-only, so switch explicitly.
        content: "Switch to the list view",
        trigger: ".o_cp_switch_buttons .o_switch_view.o_list",
        run: "click",
    },
    {
        content: "The list view renders",
        trigger: ".o_list_view .o_data_row",
    },
    {
        content: "Select every row so the cog menu appears",
        trigger: "thead .o_list_record_selector input",
        run: "click",
    },
    {
        content: "Open the cog menu",
        trigger: ".o_cp_action_menus button[data-hotkey='u']",
        run: "click",
    },
];

registry.category("web_tour.tours").add("aam_spreadsheet_tour", {
    url: "/odoo/action-base.action_partner_form",
    steps: () => [
        ...openListCog,
        {
            content: "Insert in spreadsheet is offered when nothing restricts it",
            trigger: ".o-dropdown--menu .o_menu_item:contains(Insert in spreadsheet)",
        },
    ],
});

registry.category("web_tour.tours").add("aam_spreadsheet_restricted_tour", {
    url: "/odoo/action-base.action_partner_form",
    steps: () => [
        ...openListCog,
        {
            // Duplicate is the positive anchor rather than Export: Export needs
            // `base.group_allow_export`, which an ordinary internal user does
            // not have, so anchoring on it would pass on an empty menu.
            content: "Duplicate stayed, Insert in spreadsheet did not (B7 / H9)",
            trigger: ".o-dropdown--menu:has(.o_menu_item:contains(Duplicate))" +
                ":not(:has(.o_menu_item:contains(Insert in spreadsheet)))",
        },
    ],
});
