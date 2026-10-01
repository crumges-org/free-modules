import { patch } from "@web/core/utils/patch";
import { PropertiesField } from "@web/views/fields/properties/properties_field";

/**
 * Hide the "Add a Property" control (feature H6).
 *
 * Adding a property edits the parent record's property *definition*, so it is
 * a schema change disguised as a data entry - which is why it gets its own
 * switch separate from ordinary field access.
 */
patch(PropertiesField.prototype, {
    get aamHideAdd() {
        const aam = this.env.services.aam_policy;
        return Boolean(aam && aam.isGlobal("hide_add_property"));
    },
});
