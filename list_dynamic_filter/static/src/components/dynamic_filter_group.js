/** @odoo-module **/

import {Component, xml} from "@odoo/owl";
import {ListDynamicFilter} from "./dynamic_filter";

export class ListDynamicFilterGroup extends Component {
    static template = xml`
        <div class="d-flex flex-wrap">
            <t t-foreach="props.filterFields" t-as="field" t-key="field.field_name">
                <ListDynamicFilter
                    fieldConfig="field"
                    onValueSelected="(fieldName, value) => props.onFilterValueSelected(fieldName, value)"
                />
            </t>
        </div>
    `;
    static components = {ListDynamicFilter};
    static props = {
        filterFields: {type: Array},
        onFilterValueSelected: {type: Function},
    };
}
