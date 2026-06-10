/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";
import { escape } from "@web/core/utils/strings";

export function shipmentNotification(env, action) {
    const params = action.params || {};

    const options = {
        className: params.className || "",
        sticky: params.sticky || false,
        title: params.title || _t("Notification"),
        type: params.type || "info", // success | warning | danger | info
    };

    // Optional links support
    const links = (params.links || []).map((link) => {
        return `<a href="${escape(link.url)}" target="_blank">${escape(link.label)}</a>`;
    });

    const message = markup(
        _t("<b>Success!</b> Driver has been successfully assigned to Shipment #%s",
            params.message || ""
        )
    );

    env.services.notification.add(message, options);

    // If next action provided, execute it
    if (params.next) {
        return env.services.action.doAction(params.next);
    }
}

registry.category("actions").add("shipment_notification", shipmentNotification);