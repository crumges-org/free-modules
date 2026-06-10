/** @odoo-module **/

import { SettingsPage } from "@web/webclient/settings_form_view/settings/settings_page";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";


patch(SettingsPage.prototype,{

      //T2787: setting tab hide
      setup(){
           super.setup()
            const currentModel = this.env?.model?.config?.resModel || false;
            onMounted(async () => {
               if (currentModel && currentModel === 'shipment.config.settings' && document.getElementsByClassName("settings_tab").length > 0){
                  document.getElementsByClassName("settings_tab")[0].childNodes[0].click();
                  document.getElementsByClassName("settings_tab")[0].classList.add("d-none");
           }
            });

      }


})