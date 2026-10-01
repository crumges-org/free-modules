import { registry } from "@web/core/registry";

/**
 * Access Map, then the Access Explainer it launches.
 *
 * The map is the screen whose layout broke silently once already (`.o_action`
 * forces `flex-direction: column`, so the two-pane body collapsed while every
 * Python test stayed green), which is why the inner `.o_aam_map_body` wrapper
 * is asserted explicitly rather than just the root.
 *
 * Fixtures from `tests/test_tours.py`: a group named "AAM Tour Marker" with one
 * read-only ACL row on `res.partner`, so the filter and the matrix are both
 * deterministic.
 */
registry.category("web_tour.tours").add("aam_access_map_tour", {
    url: "/odoo/action-odooapp_access_management.action_aam_access_map",
    steps: () => [
        {
            content: "The client action mounted, with its two-pane body",
            trigger: ".o_aam_map > .o_aam_map_body",
        },
        {
            content: "get_access_map_groups resolved",
            trigger: ".o_aam_map_side .o_aam_grouplist li button .o_aam_gname",
        },
        {
            content: "The first group was auto-selected and its detail loaded",
            trigger: ".o_aam_map_main .o_aam_map_head h1",
        },
        {
            content: "Narrow the group list to the seeded marker group",
            trigger: ".o_aam_map_sidehead input[type='search']",
            run: "edit AAM Tour Marker",
        },
        {
            content: "The filter left exactly one group",
            trigger: ".o_aam_grouplist li:count(1)",
        },
        {
            content: "Select it",
            trigger: ".o_aam_grouplist li button:contains(AAM Tour Marker)",
            run: "click",
        },
        {
            content: "get_access_map_detail resolved for the marker group",
            trigger: ".o_aam_map_main .o_aam_map_head h1:contains(AAM Tour Marker)",
        },
        {
            content: "The members section renders",
            trigger: ".o_aam_section h2:contains(Members)",
        },
        {
            content: "Its one ACL row is in the matrix, with a status badge",
            trigger: ".o_aam_acl tbody tr:has(.o_aam_mono:contains(res.partner)) .o_aam_badge:contains(Read only)",
        },
        {
            content: "Read is granted, the write/delete columns are not",
            trigger: ".o_aam_acl tbody tr:has(.o_aam_mono:contains(res.partner)) td.o_aam_no",
        },
        {
            content: "The 'cannot do' summary renders",
            trigger: ".o_aam_section:has(h2:contains(cannot do)) .o_aam_cannot li",
        },
        {
            content: "Widening the scope re-queries without crashing",
            trigger: ".o_aam_map_head button:contains(Including implied)",
            run: "click",
        },
        {
            content: "…and the matrix comes back",
            trigger: ".o_aam_acl tbody tr",
        },
        {
            content: "The model search matches on the technical id",
            trigger: ".o_aam_section input[placeholder*='Search models']",
            run: "edit res.partner",
        },
        {
            content: "…leaving one row",
            trigger: ".o_aam_acl tbody tr:count(1)",
        },
        {
            content: "A search that matches nothing shows the empty state, not a blank table",
            trigger: ".o_aam_section input[placeholder*='Search models']",
            run: "edit zzz_no_such_model",
        },
        {
            trigger: ".o_aam_map_main .text-muted:contains(No model access rows for this group)",
        },

        // --- The Access Explainer, opened the way a user reaches it -------
        {
            content: "Open the Access Explainer",
            trigger: ".o_aam_map_head button:contains(Explain a user)",
            run: "click",
        },
        {
            content: "The wizard opened, and the dialog_size context took effect",
            trigger: ".modal .modal-dialog.modal-xl .o_form_view .o_field_widget[name='user_id']",
        },
        {
            content: "It defaults to the current user, who is an administrator",
            trigger: ".modal .o_field_widget[name='summary']:contains(never restricted by this module)",
        },
        {
            content: "Explain the restricted tour user instead",
            trigger: ".modal .o_field_widget[name='user_id'] input",
            run: "edit AAM Tour Operator",
        },
        {
            trigger: ".o-autocomplete--dropdown-item a:contains(AAM Tour Operator)",
            run: "click",
        },
        {
            content: "…on res.partner",
            trigger: ".modal .o_field_widget[name='model_id'] input",
            run: "edit res.partner",
        },
        {
            // Pick by label, never by position: the dropdown keeps showing the
            // previous, unfiltered result set until the debounced search lands,
            // so `:first` clicks whatever happened to be there and the wizard
            // then explains the wrong model. No other model matching
            // "res.partner" is named "Contact".
            trigger: ".o-autocomplete--dropdown-item:contains(Contact)",
            run: "click",
        },
        {
            trigger: ".modal .o_field_widget[name='model_id'] input:value(Contact)",
        },
        {
            content: "Run it",
            trigger: ".modal footer button:contains(Explain)",
            run: "click",
        },
        {
            content: "The summary attributes the effects to the rule that caused them",
            trigger: ".modal .o_field_widget[name='summary']:contains(Reached through)",
        },
        {
            content: "…naming the rule",
            trigger: ".modal .o_field_widget[name='summary']:contains(AAM Tour Restrictions)",
        },
        {
            content: "Re-opening kept the extra-large dialog",
            trigger: ".modal .modal-dialog.modal-xl",
        },
        {
            content: "Findings are listed, tagged by source",
            trigger: ".modal .o_field_widget[name='line_ids'] .o_data_row:contains(Access Rule)",
        },
        {
            content: "…across several categories",
            trigger: ".modal .o_field_widget[name='line_ids'] .o_data_row:contains(Field)",
        },
        {
            trigger: ".modal .o_field_widget[name='line_ids'] .o_data_row:contains(Chatter)",
        },
        // Native access rights are the other half of the claim this wizard
        // makes, and they only appear where something is actually denied - so
        // ask about a model the operator genuinely cannot write.
        {
            content: "Explain the same user on res.groups instead",
            trigger: ".modal .o_field_widget[name='model_id'] input",
            run: "edit res.groups",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains(Access Groups)",
            run: "click",
        },
        {
            trigger: ".modal footer button:contains(Explain)",
            run: "click",
        },
        {
            content: "Native ACL denials are attributed too",
            trigger: ".modal .o_field_widget[name='line_ids'] .o_data_row:contains(Model Access)",
        },
        {
            content: "Close the wizard",
            trigger: ".modal footer button:contains(Close)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal)) .o_aam_map",
        },
    ],
});
