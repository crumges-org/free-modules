/** @odoo-module */

import {ListRenderer} from '@web/views/list/list_renderer';
import {patch} from '@web/core/utils/patch';
import { _t } from "@web/core/l10n/translation";

patch(ListRenderer.prototype, {
    setup(){
        super.setup(...arguments);
        if (this.props.list.resModel == 'shipment.document'){
        this.creates = this.props.archInfo.creates.length
            ? this.props.archInfo.creates
            : [{ type: "create", string: _t("Add a Document") }];
        }
    },
})



