/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";



export class ListBinary extends BinaryField {
    static template = "bista_driver_app.ListBinary";
}

export const listBinary = {
    ...binaryField,
    component: ListBinary,
};

registry.category("fields").add("list_binary", listBinary);
