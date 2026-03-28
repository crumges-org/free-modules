/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { AlternativeProductPopup } from "@pos_alternative_products/js/AlternativeProductPopup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
     setup(){
     super.setup();
     this.orm = useService("orm");
     },
     async addProductToOrder(product) {
     let selectedProduct = product.product_tmpl_id
         const alternativeIds = selectedProduct.alternative_product_ids.map(prod => prod.id);
         const alter_products = this.pos.product_template.filter(dataObj => {
               return alternativeIds.includes(dataObj.id);
         });

          for(var i=0; i < alter_products.length; i++){
              alter_products[i]['image_url'] = window.location.origin + "/web/image/product.template/" + alter_products[i].id + "/image_128";
          }
          if (alter_products.length == 0) {
            return super.addProductToOrder(...arguments);
          }
          if(selectedProduct.qty_available == 0){
             this.dialog.add(AlternativeProductPopup, {
               title: _t("Alternative Product"),
               cancelText: _t("Cancel"),
               body: alter_products,
             });
          }
          else {
            return super.addProductToOrder(...arguments);
          }
    },
});