/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { BrandSelector } from "@am_product_brand/js/BrandSelector";
import { useState } from "@odoo/owl";

// Patch ProductScreen to add brand filtering
patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.brandState = useState({
            selectedBrandId: null,
        });
    },

    get products() {
        let products = super.products;
        
        // Filter by brand if selected
        if (this.brandState.selectedBrandId && this.pos.config.use_product_brand) {
            products = products.filter(product => 
                product.brand_id && product.brand_id[0] === this.brandState.selectedBrandId
            );
        }
        
        return products;
    },

    onBrandSelect(brandId) {
        this.brandState.selectedBrandId = brandId;
    },

    get showBrandSelector() {
        return this.pos.config.use_product_brand && 
               this.pos.brands && 
               this.pos.brands.length > 0;
    },
});

// Add BrandSelector as a sub-component
ProductScreen.components = {
    ...ProductScreen.components,
    BrandSelector,
};
