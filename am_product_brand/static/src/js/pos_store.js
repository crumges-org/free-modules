/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.brands = [];
        this.brand_by_id = {};
    },

    async _processData(loadedData) {
        await super._processData(...arguments);
        
        // Process brands data
        if (loadedData['product.brand']) {
            this.brands = loadedData['product.brand'];
            this.brand_by_id = {};
            for (const brand of this.brands) {
                this.brand_by_id[brand.id] = brand;
            }
        }
    },

    getBrandById(brandId) {
        return this.brand_by_id[brandId] || null;
    },

    getProductsByBrand(brandId) {
        if (!brandId) {
            return this.db.get_product_by_category(0);
        }
        return this.db.get_product_by_category(0).filter(
            product => product.brand_id && product.brand_id[0] === brandId
        );
    },
});
