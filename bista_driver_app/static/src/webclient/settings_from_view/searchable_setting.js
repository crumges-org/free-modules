/** @odoo-module **/

import { SearchableSetting } from "@web/webclient/settings_form_view/settings/searchable_setting";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";


patch(SearchableSetting.prototype,{

        //T2787: Shipment setting layout change
        get fieldClass() {
            const record = this.props.hasOwnProperty('record');
            return (record && this.props.record.resModel === 'shipment.config.settings') ? 'mt4' : 'mt16';
        },

        get classNames() {
            const classNames = super.classNames;
            if(this.props.record.resModel === 'shipment.config.settings' && 'col-lg-3 col-sm-5' in classNames){
                 classNames['col-12']= false;
                 classNames['col-lg-6']= false;
            }
            return classNames;
        }


})