/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { executeButtonCallback } from "@web/views/view_button/view_button_hook";

patch(ListController.prototype, {
    async onClickCreate() {
        if (this.props.resModel === 'shipment.shipment') {
            await executeButtonCallback(this.rootRef.el, () =>
                this.openAction()
            );
        }else{
            return executeButtonCallback(this.rootRef.el, () => this.createRecord());
        }
    },

    async openAction() {
        await this.actionService.doAction({
            name : _t("Create Shipments"),
            type: "ir.actions.act_window",
            res_model: "shipment.wizard",
            views: [[false, "form"]],
            target: "new",
        }, {
            onClose: async () => {
                await this.model.root.load();
            },
        });
    }

});
