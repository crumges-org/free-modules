/** @odoo-module **/


import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {FormViewDialog} from '@web/views/view_dialogs/form_view_dialog';
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { _t } from "@web/core/l10n/translation";

patch(StatusBarField.prototype, {
    setup(){
        super.setup();
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.action = useService("action");
    },

    async selectItem(item) {
        if (this.props.record.resModel === 'shipment.shipment') {
            var string = "Are you sure you want to mark as " + item.label + "?";
            if (item.label === 'Pending'){
                string = "Are you sure you want to mark as 'Pending' and remove the assigned Driver?";
            }

            this.dialogService.add(ConfirmationDialog, {
                 title: _t("Confirmation"),
                 body: _t(string),
                 confirmClass: "btn-primary",
                 confirmLabel: _t("Ok"),
                 confirm: async () => {
                        if (item.label === 'Cancelled'){
                            const action = await this.orm.call(
                                "shipment.shipment",
                                "action_get_cancelled",
                                [[this.props.record.resId]]
                            );
                            this.dialogService.add(FormViewDialog, {
                                context: action.context,
                                resModel: action.res_model,
                                viewId: action.form_id,
                                onRecordSaved: async (res) => {
                                    const { name, record } = this.props;
                                    const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
                                    await record.update({ [name]: value });
                                    await record.save();
                                },
                            });
                        }
                        else if (['Pending', 'At Pickup', 'In Transit', 'At Delivery', 'Delivered', 'Assigned', 'Dispatched'].includes(item.label)){
                            if (item.label === 'Pending'){
                                const action = await this.orm.call(
                                    "shipment.shipment",
                                    "action_set_pending",
                                    [[this.props.record.resId]]
                                );
                                const { name, record } = this.props;
                                const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
                                await record.update({ [name]: value });
                                await record.save();
                            }
                            else if (item.label === 'Dispatched'){
                                const action = await this.orm.call(
                                    "shipment.shipment",
                                    "action_set_accepted",
                                    [[this.props.record.resId]]
                                );
                                const { name, record } = this.props;
                                const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
                                await record.update({ [name]: value });
                                await record.save();
                            }

                            else if (item.label === 'At Pickup'){
                                const action = await this.orm.call(
                                    "shipment.shipment",
                                    "action_set_at_pickup",
                                    [[this.props.record.resId]]
                                );
                                const { name, record } = this.props;
                                const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
                                await record.update({ [name]: value });
                                await record.save();
                            }
                            else if (item.label === 'In Transit'){
                                const action = await this.orm.call(
                                    "shipment.shipment",
                                    "action_set_in_transit",
                                    [[this.props.record.resId]]
                                );
                                const { name, record } = this.props;
                                const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
                                await record.update({ [name]: value });
                                await record.save();
                            }
                            else if (item.label === 'At Delivery'){
                                const action = await this.orm.call(
                                    "shipment.shipment",
                                    "action_set_at_delivery",
                                    [[this.props.record.resId]]
                                );
                                const { name, record } = this.props;
                                const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
                                await record.update({ [name]: value });
                                await record.save();
                            }
                            else if (item.label === 'Delivered'){
                                const action = await this.orm.call(
                                    "shipment.shipment",
                                    "action_set_delivered",
                                    [[this.props.record.resId]]
                                );
                                const { name, record } = this.props;
                                const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
                                await record.update({ [name]: value });
                                await record.save();
                            }
                            else if (item.label === 'Assigned'){
                                const action = await this.orm.call(
                                    "shipment.shipment",
                                    "action_set_assigned",
                                    [[this.props.record.resId]]
                                );
                                if (action.status === 'assigned'){
                                    const { name, record } = this.props;
                                    const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
                                    await record.update({ [name]: value });
                                    await record.save();
                                }else{
                                    this.dialogService.add(ConfirmationDialog, {
                                        title: _t("Warning"),
                                        body: _t(action.message),
                                        confirmClass: "btn-primary",
                                        confirmLabel: _t("Ok"),
                                        confirm: () => { },
                                    });
                                }
                            }

                        }else{
                            const { name, record } = this.props;
                            const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
                            await record.update({ [name]: value });
                            await record.save();
                        }
                 },
                 cancelLabel : _t("Cancel"),
                 cancel: () => { },
             });
        }else{
            await super.selectItem(item);
        }
    }
});

