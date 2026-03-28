/** @odoo-module */

import { registry } from "@web/core/registry";

// Register product.brand model for POS
const ProductBrand = {
    model: 'product.brand',
    fields: ['id', 'name', 'code', 'sequence', 'image_128'],
    domain: function(params) {
        return [];
    },
    loaded: function(self, brands) {
        self.brands = brands;
        self.brand_by_id = {};
        for (let brand of brands) {
            self.brand_by_id[brand.id] = brand;
        }
    },
};

// Extend POS models
registry.category("pos_models").add("product.brand", ProductBrand);
