/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

// Brand Selector Component
export class BrandSelector extends Component {
    static template = "am_product_brand.BrandSelector";
    
    setup() {
        this.pos = usePos();
        this.state = useState({
            selectedBrandId: null,
        });
    }

    get brands() {
        return this.pos.brands || [];
    }

    get selectedBrand() {
        if (!this.state.selectedBrandId) return null;
        return this.pos.brand_by_id[this.state.selectedBrandId];
    }

    get showBrandImages() {
        return this.pos.config.show_brand_images;
    }

    get isEnabled() {
        return this.pos.config.use_product_brand && this.brands.length > 0;
    }

    selectBrand(brandId) {
        if (this.state.selectedBrandId === brandId) {
            // Deselect if clicking the same brand
            this.state.selectedBrandId = null;
        } else {
            this.state.selectedBrandId = brandId;
        }
        // Trigger product filtering
        this.props.onBrandSelect(this.state.selectedBrandId);
    }

    clearBrand() {
        this.state.selectedBrandId = null;
        this.props.onBrandSelect(null);
    }

    getBrandImage(brand) {
        if (brand.image_128) {
            return `data:image/png;base64,${brand.image_128}`;
        }
        return '/am_product_brand/static/src/img/default_brand.png';
    }
}

BrandSelector.props = {
    onBrandSelect: Function,
};
