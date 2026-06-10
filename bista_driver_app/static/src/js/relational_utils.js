/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { X2ManyFieldDialog } from "@web/views/fields/relational_utils";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

patch(X2ManyFieldDialog.prototype, {
    setup(){
        super.setup();
        this.dialogService = useService("dialog");
    },

     async remove() {
        if (this.props.record.resModel === 'shipment.stop'){
            this.dialogService.add(ConfirmationDialog, {
                 title: _t("Confirmation Required"),
                 body: _t("Are you sure you want to proceed?"),
                 confirmClass: "btn-primary",
                 confirmLabel: _t("Ok"),
                 confirm: async () => {
                        await this.props.delete();
                        this.props.close();
                 },
                 cancelLabel : _t("Cancel"),
                 cancel: () => { },
             });
        }else{
            await this.props.delete();
            this.props.close();
        }

    }
});