import { registry } from "@web/core/registry";

/**
 * `web.PropertiesField`, extended by `properties_patch.xml`.
 *
 * This lives in its own file, and on `project.task` rather than `res.partner`,
 * because Odoo 18's `res.partner` has no `properties` field at all - it comes
 * from `properties.base.definition.mixin`, which is v19-only. `project.task`
 * carries `task_properties` (project/models/project_task.py:188), with its
 * definition on `project_id.task_properties_definition`, and is available on
 * both Community and Enterprise.
 *
 * Two things are being proved, and the first matters more than it looks:
 *
 * 1. The `t-inherit` still applies. An xpath that stops matching raises at
 *    *render* time and takes down every view using the template - which is how a
 *    stale `hasclass()` once blanked every list view in the database while all
 *    the Python tests passed.
 * 2. `hide_add_property` (H6) removes the way a user adds a property, while the
 *    properties themselves keep working. The positive half is the point: a tour
 *    that only checked the control was gone would pass just as well on a widget
 *    that failed to mount.
 *
 * The control asserted on is the form cog's "Add Properties" entry, not the
 * in-field `.o_field_property_add` button. That button is gated on
 * `state.showAddButton`, which core reads from a `showAddButton` attribute in
 * the view arch (properties_field.js:952) - `project.task`'s form does not set
 * it, so the node never renders and asserting on it would be vacuous. The cog
 * entry is the surface that actually exists here: `form_arch_parser.js:34` turns
 * `activeActions.addPropertyFieldValue` on for any form carrying a properties
 * field, and `form_controller.js:540` publishes it as "Add Properties".
 */

const openSeededTask = [
    {
        content: "The task list renders",
        trigger: ".o_list_view .o_data_row",
    },
    {
        content: "Open the seeded task",
        trigger: ".o_data_row .o_data_cell:contains(AAM Tour Task)",
        run: "click",
    },
    {
        content: "The task form is up",
        trigger: ".o_form_view .o_field_widget[name='name']",
    },
];

registry.category("web_tour.tours").add("aam_properties_tour", {
    url: "/odoo/action-project.action_view_all_task",
    steps: () => [
        ...openSeededTask,
        {
            content: "The properties field renders its seeded property",
            trigger:
                ".o_form_view .o_field_widget[name='task_properties'] .o_property_field:contains(Tour Property)",
        },
        {
            content: "Open the form cog menu",
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },
        {
            // Present for an unrestricted user, and the anchor that gives the
            // restricted tour's negative assertion something to mean.
            content: "Add Properties is offered",
            trigger: ".o-dropdown--menu .o_menu_item:contains(Add Properties)",
        },
    ],
});

registry.category("web_tour.tours").add("aam_properties_restricted_tour", {
    url: "/odoo/action-project.action_view_all_task",
    steps: () => [
        ...openSeededTask,
        {
            content: "The properties widget still works under the restriction",
            trigger:
                ".o_form_view .o_field_widget[name='task_properties'] .o_property_field:contains(Tour Property)",
        },
        {
            content: "Open the form cog menu",
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            run: "click",
        },
        {
            // The dropdown having opened at all is the positive anchor: a
            // `:not(:has(...))` on a menu that never rendered would pass for the
            // wrong reason. The step above already proved the widget mounted.
            content: "…but Add Properties was removed from the cog (H6)",
            trigger: ".o-dropdown--menu:not(:has(.o_menu_item:contains(Add Properties)))",
        },
    ],
});
