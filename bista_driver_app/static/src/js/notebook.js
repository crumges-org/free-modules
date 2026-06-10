/* @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Notebook } from "@web/core/notebook/notebook";
import {
    useEffect,
} from "@odoo/owl";

patch(Notebook.prototype,{
    setup() {
        super.setup();
        useEffect(
        () => {
            if (
                this.env.model?.root?.resModel === "shipment.shipment"
            ) {
                this.state.showMap =
                    this.state.currentPage === "page_1";
            }
        },
        () => [this.state.currentPage]
        );
    },
})