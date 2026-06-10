/** @odoo-module **/

import { BadgeField } from "@web/views/fields/badge/badge_field";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { patch } from '@web/core/utils/patch';
import { onWillStart } from "@odoo/owl";

patch(BadgeField.prototype, {
    async setup() {
        super.setup(...arguments);
        this.colorIndexShipment = false
        onWillStart(async () => {
            if (this.props.record.resModel === 'shipment.shipment' && this.props.name === 'status_id'){
                const result = await this.props.record.model.orm.call(
                    'shipment.status',
                    'search_read',
                    [[['id', '=', this.props.record.data.status_id[0]]], ["id","color"]],
                );
                if (result && result[0] && result[0].color){
                    this.colorIndexShipment = result[0].color
                }
            }
        })

    },

    get classFromDecoration() {
        const res = super.classFromDecoration;
        if (this.props.record.resModel === 'shipment.shipment' && this.props.name === 'status_id'){
            const evalContext = this.props.record.evalContextWithVirtualIds;
            for (const decorationName in this.props.decorations) {
                if (this.colorIndexShipment){
                    return `oe_badge_color_${this.colorIndexShipment}`;
                }
                if (evaluateBooleanExpr(this.props.decorations[decorationName], evalContext)) {
                    return `text-bg-${decorationName}`;
                }
            }
            return "";
        }else{
            return res
        }

    }
})
