/** @odoo-module **/
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { systrayItem } from "@web_studio/systray_item/systray_item";

registry.category("systray").add("StudioSystrayItem", {
    Component: systrayItem.Component,
    isDisplayed: () => {
        return user.isSystem && session.studio_control_access === true;
    },
}, {
    force: true,
    sequence: 1,
});