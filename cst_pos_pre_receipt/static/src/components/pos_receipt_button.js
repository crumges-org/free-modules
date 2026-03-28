/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(ReceiptScreen, {
    props: {
        ...ReceiptScreen.props,
        preReceipt: { type: Boolean, optional: true },
    },
});


patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();

        // Props passed to ReceiptScreen
        this.preReceiptProps = {
            preReceipt: true,
        };
    },

    async printReceipt() {
        const order = this.pos.get_order();

        if (!order || order.get_orderlines().length === 0) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Warning"),
                body: _t("No products found. Please add at least one item."),
            });
            return false;
        }

        this.pos.showScreen("ReceiptScreen", this.preReceiptProps);
    },
});
