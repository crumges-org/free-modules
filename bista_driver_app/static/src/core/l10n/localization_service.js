/** @odoo-module **/
import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { localizationService } from "@web/core/l10n/localization_service";

patch(localizationService, {
    async start(env, { user }) {
        // 🔁 Call the original (super) method
        if (document.getElementById('shipment_content') && session.length === undefined) {
            session.translationURL = "/api/web/webclient/translations";
        }
        console.log("Localization service patched start() called");
        return super.start(env, { user });
    },
});