import { registry } from "@web/core/registry";

/**
 * The configuration screens: profiles and rules.
 *
 * The profiles kanban is here because it crashed in production-like use while
 * the whole Python suite stayed green - a `t-if` read `record.active.raw_value`
 * without `<field name="active"/>` being declared. Kanban templates are only
 * compiled when a browser renders them, so a tour is the only thing that
 * catches that class of mistake.
 *
 * The rule form is walked page by page for the same reason: each notebook page
 * embeds a different line model with its own list and form arch.
 */
registry.category("web_tour.tours").add("aam_config_tour", {
    url: "/odoo/action-odooapp_access_management.action_aam_profile",
    steps: () => [
        {
            content: "The profiles kanban renders",
            trigger: ".o_kanban_view .o_kanban_record",
        },
        {
            content: "…including the seeded profile",
            trigger: ".o_kanban_record:contains(AAM Tour Profile)",
        },
        {
            content: "Open the search dropdown",
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            // Blocking a profile archives it, so this filter is the only way
            // back to one.
            content: "Show blocked profiles",
            trigger: ".o_filter_menu .o_menu_item:contains(Blocked)",
            run: "click",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            // The exact expression that took this view down once: reading a
            // field through `record` in a t-if without declaring it.
            content: "A blocked profile shows its badge",
            trigger: ".o_kanban_record:contains(AAM Tour Blocked Profile) .badge:contains(Blocked)",
        },
        {
            content: "Drop the filter again",
            trigger: ".o_searchview_facet:contains(Blocked) .o_facet_remove",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:contains(AAM Tour Profile)",
        },
        {
            content: "Switch to the list view",
            trigger: ".o_cp_switch_buttons .o_switch_view.o_list",
            run: "click",
        },
        {
            content: "The list renders, computed counts included",
            trigger: ".o_list_view .o_data_row:contains(AAM Tour Profile)",
        },
        {
            content: "Open the profile",
            trigger: ".o_data_row:contains(AAM Tour Profile) .o_data_cell:first",
            run: "click",
        },
        {
            content: "The profile form renders",
            trigger: ".o_form_view .o_field_widget[name='name'] input:value(AAM Tour Profile)",
        },
        {
            content: "Its rules page renders the embedded list",
            trigger: ".o_notebook .nav-link:contains(Rules)",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_field_widget[name='rule_ids']",
        },
        {
            content: "The stat button reports the rule count",
            trigger: ".o-form-buttonbox button[name='action_view_rules']:contains(Rules)",
        },

        // --- Access Rules --------------------------------------------------
        {
            content: "Open the Configuration menu",
            trigger: ".o_menu_sections button[data-menu-xmlid='odooapp_access_management.menu_aam_config']",
            run: "click",
        },
        {
            content: "Go to Access Rules",
            trigger: ".o-dropdown--menu [data-menu-xmlid='odooapp_access_management.menu_aam_rule']",
            run: "click",
        },
        {
            content: "The rules list renders with its status badge",
            trigger: ".o_list_view .o_data_row:contains(AAM Tour Restrictions) .o_field_badge",
        },
        {
            content: "Open the rule",
            trigger: ".o_data_row:contains(AAM Tour Restrictions) .o_data_cell:first",
            run: "click",
        },
        {
            content: "The rule form renders its targeting block",
            trigger: ".o_form_view .o_field_widget[name='target_type'] input[data-value='user']:checked",
        },
        {
            content: "…and the user it targets",
            trigger: ".o_field_widget[name='user_ids'] .o_tag:contains(AAM Tour Operator)",
        },
        // Every notebook page carries a different embedded arch. Walking them
        // is what proves each one compiles.
        {
            content: "Menus page",
            trigger: ".o_notebook .nav-link:contains(Menus)",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_field_widget[name='menu_line_ids'] .o_data_row",
        },
        {
            content: "Models page",
            trigger: ".o_notebook .nav-link:contains(Models)",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_field_widget[name='model_line_ids'] .o_data_row:contains(Contact)",
        },
        {
            content: "Fields page",
            trigger: ".o_notebook .nav-link:contains(Fields)",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_field_widget[name='field_line_ids'] .o_data_row",
        },
        {
            content: "Buttons & Tabs page",
            trigger: ".o_notebook .nav-link:contains(Buttons)",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_field_widget[name='button_line_ids']",
        },
        {
            content: "Search Panel page",
            trigger: ".o_notebook .nav-link:contains(Search Panel)",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_field_widget[name='search_line_ids'] .o_data_row",
        },
        {
            content: "Chatter page",
            trigger: ".o_notebook .nav-link:contains(Chatter)",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_field_widget[name='chatter_line_ids'] .o_data_row",
        },
        {
            content: "The global toggles page",
            trigger: ".o_notebook .nav-link:contains(Everywhere)",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_field_widget[name='disable_developer_mode']",
        },
        {
            content: "Time Windows page",
            trigger: ".o_notebook .nav-link:contains(Time Windows)",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_field_widget[name='time_window_ids']",
        },

        // --- The two wizards reachable from the same menu ------------------
        {
            content: "Open the Configuration menu again",
            trigger: ".o_menu_sections button[data-menu-xmlid='odooapp_access_management.menu_aam_config']",
            run: "click",
        },
        {
            content: "Preset Library",
            trigger: ".o-dropdown--menu [data-menu-xmlid='odooapp_access_management.menu_aam_preset_library']",
            run: "click",
        },
        {
            // Grouped by category and filtered to what this database can honour,
            // both from the action context. Asserting on a named preset rather
            // than on "some card" keeps the step honest if the catalogue is
            // ever loaded empty.
            content: "The library lists presets grouped by category",
            trigger: ".o_kanban_view .o_kanban_group .o_kanban_record:contains(Read-only Auditor)",
        },
        {
            content: "Cross-app presets are available on every database",
            trigger: ".o_kanban_record:contains(Read-only Auditor):not(:has(:contains(Unavailable)))",
        },
        {
            content: "Use this preset opens the apply wizard preloaded",
            trigger: ".o_kanban_record:contains(Read-only Auditor) button:contains(Use this preset)",
            run: "click",
        },
        {
            trigger: ".modal .o_field_widget[name='preset_ids'] .o_tag:contains(Read-only Auditor)",
        },
        {
            content: "…and the coverage panel says what it will do here",
            trigger: ".modal .o_field_widget[name='coverage']",
        },
        {
            trigger: ".modal footer button:contains(Cancel)",
            run: "click",
        },
        {
            content: "Back out of the library",
            trigger: "body:not(:has(.modal)) .o_menu_sections button[data-menu-xmlid='odooapp_access_management.menu_aam_config']",
            run: "click",
        },
        {
            content: "Load Presets, from the menu this time",
            trigger: ".o-dropdown--menu [data-menu-xmlid='odooapp_access_management.menu_aam_preset']",
            run: "click",
        },
        {
            content: "The wizard opens empty, prompting for a choice",
            trigger: ".modal .o_field_widget[name='preset_ids']",
        },
        {
            trigger: ".modal footer button:contains(Cancel)",
            run: "click",
        },
        {
            content: "Open the Configuration menu once more",
            trigger: "body:not(:has(.modal)) .o_menu_sections button[data-menu-xmlid='odooapp_access_management.menu_aam_config']",
            run: "click",
        },
        {
            content: "Import Rules",
            trigger: ".o-dropdown--menu [data-menu-xmlid='odooapp_access_management.menu_aam_import']",
            run: "click",
        },
        {
            content: "The import wizard renders its dry-run choice",
            trigger: ".modal .o_field_widget[name='mode'] input[type='radio']",
        },
        {
            trigger: ".modal footer button:contains(Close)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },

        // --- The guided setup wizard, driven end to end ------------------
        // Every step of this one is server-rendered: Next writes `state` and
        // returns an act_window at the same record, so a broken step shows up as
        // a dialog that never advances rather than as a Python failure. Nothing
        // but a tour catches that.
        {
            content: "Open the Configuration menu",
            trigger: ".o_menu_sections button[data-menu-xmlid='odooapp_access_management.menu_aam_config']",
            run: "click",
        },
        {
            content: "New Restriction",
            trigger: ".o-dropdown--menu [data-menu-xmlid='odooapp_access_management.menu_aam_rule_wizard']",
            run: "click",
        },
        {
            content: "Step 1 opens on Who",
            trigger: ".modal .o_field_widget[name='target_type'] input[type='radio']",
        },
        {
            content: "Next refuses to leave step 1 with nobody selected",
            trigger: ".modal footer button:contains(Next)",
            run: "click",
        },
        {
            // The view's own `required=` catches this before the request is
            // sent, so what the user gets is the field marked invalid rather
            // than a server round-trip. `_validate_step` still guards the RPC
            // path and is covered by TestRuleWizard.
            content: "...by marking the field, and staying on step 1",
            trigger: ".modal .o_field_invalid[name='user_ids']",
        },
        {
            content: "Pick the tour operator",
            trigger: ".modal .o_field_widget[name='user_ids'] input",
            run: "edit AAM Tour Operator",
        },
        {
            trigger: ".o-autocomplete--dropdown-item a:contains(AAM Tour Operator)",
            run: "click",
        },
        {
            content: "The audience panel counts them",
            trigger: ".modal .o_field_widget[name='audience']:contains(user)",
        },
        {
            trigger: ".modal footer button:contains(Next)",
            run: "click",
        },
        {
            content: "Step 2 asks what it covers",
            trigger: ".modal .o_field_widget[name='model_ids'] input",
            run: "edit Contact",
        },
        {
            trigger: ".o-autocomplete--dropdown-item a:contains(Contact)",
            run: "click",
        },
        {
            trigger: ".modal footer button:contains(Next)",
            run: "click",
        },
        {
            content: "Step 3 offers the access levels",
            trigger: ".modal .o_field_widget[name='access_level'] input[type='radio']",
        },
        {
            content: "Choose View only",
            trigger: ".modal .o_radio_item:contains(View only) input",
            run: "click",
        },
        {
            trigger: ".modal footer button:contains(Next)",
            run: "click",
        },
        {
            content: "The review states in words what will be created",
            trigger: ".modal .o_field_widget[name='summary']:contains(View only)",
        },
        {
            content: "Back keeps what was entered",
            trigger: ".modal footer button:contains(Back)",
            run: "click",
        },
        {
            trigger: ".modal .o_radio_item:contains(View only) input:checked",
        },
        {
            trigger: ".modal footer button:contains(Next)",
            run: "click",
        },
        {
            content: "Apply",
            trigger: ".modal footer button:contains(Apply)",
            run: "click",
        },
        {
            content: "It lands on the rule it created",
            trigger: ".o_form_view .o_field_widget[name='name'] input:value(AAM Tour Operator)",
        },
        {
            content: "...which the wizard can load back in",
            trigger: ".o_form_statusbar button:contains(Edit in Wizard)",
            run: "click",
        },
        {
            trigger: ".modal .o_field_widget[name='user_ids']:contains(AAM Tour Operator)",
        },
        {
            trigger: ".modal footer button:contains(Cancel)",
            run: "click",
        },
    ],
});
