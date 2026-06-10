/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { executeButtonCallback } from "@web/views/view_button/view_button_hook";

patch(FormController.prototype, {
    async setup(){
        super.setup();
        // Default false until we check permissions
        this.is_display = false;

        if (this.props.resModel === "shipment.location") {
            // const dispatcher_group = await this.user.hasGroup('bista_driver_app.group_shipment_dispatcher_access');
            // const admin_group = await this.user.hasGroup('base.group_system');
            const dispatcher_group = await user.hasGroup('bista_driver_app.group_shipment_dispatcher_access');
            const admin_group = await user.hasGroup('base.group_system');
            this.is_display = dispatcher_group || admin_group;
        }
    },

    // async save(params) {
//        if (this.model.root.resModel === 'call.out.request') {
//            const record = this.model.root;
//
//            // Step 1: Capture original driver_id values using _values
//            const oldDriverMap = {};
//            const oldShipmentLines = record.data.shipment_ids?.records || [];
//
//            for (const line of oldShipmentLines) {
//                const shipmentId = line.data.name;
//                const originDriverId = line._values?.driver_id?.[0] || null;
//                if (shipmentId) {
//                    oldDriverMap[shipmentId] = originDriverId;
//                }
//            }
//
//            // Step 2: Save form
//            let saved = false;
//            if (this.props.saveRecord) {
//                saved = await this.props.saveRecord(record, params);
//            } else {
//                saved = await record.save(params);
//            }
//
//            // Step 3: Compare to updated values after save
//            if (saved) {
//                const updatedShipmentLines = this.model.root.data.shipment_ids?.records || [];
//
//                for (const line of updatedShipmentLines) {
//                    const shipmentId = line.data.name;
//                    const newDriverId = line.data.driver_id?.[0] || null;
//                    const oldDriverId = oldDriverMap[shipmentId];
//
//                    const driverChanged = oldDriverId !== newDriverId && newDriverId;
//
//                    if (driverChanged) {
//                        const shipmentName = line.data.name || 'Shipment';
//                        const content = markup(
//                            _t('<b>Success!</b> Driver has been successfully assigned to Shipment #%s', shipmentName)
//                        );
//                        this.env.services.notification.add(content, {
//                            type: "success",
//                            sticky: false,
//                        });
//                    }
//                }
//
//                if (this.props.onSave) {
//                    this.props.onSave(record, params);
//                }
//            }
//
//            return saved;
//        } else {
//            return super.save(params);
//        }
    // },

    async create() {
        if (this.props.resModel === 'shipment.shipment') {
            await executeButtonCallback(this.ui.activeElement, () =>
                this.openAction()
            );
        }
        else{
            const dirty = await this.model.root.isDirty();
            const onError = this.onSaveError.bind(this);
            const canProceed = !dirty || (await this.model.root.save({ onError }));
            // FIXME: disable/enable not done in onPagerUpdate
            if (canProceed) {
                await executeButtonCallback(this.ui.activeElement, () =>
                    this.model.load({ resId: false })
                );
            }
        }
    },

    async openAction() {
        await this.env.services.action.doAction({
            name : _t("Create Shipments"),
            type: "ir.actions.act_window",
            res_model: "shipment.wizard",
            views: [[false, "form"]],
            target: "new",
        });
    },

    get actionMenuItems() {
        const result = super.actionMenuItems; // ← super call

        // Apply custom filtering logic
        if (this.props.resModel === "shipment.location" && !this.is_display) {
            // Filter static action items
            result.action = result.action.filter(
                (item) => item.key !== 'unarchive' && item.key !== 'archive'
            );
        }

        return result;
    }


});
