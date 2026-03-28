/** @odoo-module **/

import {Component, useState, onWillStart, useRef, xml} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class ListDynamicFilter extends Component {
    // we need to define the component template in js itself or else we will get
    // template not found error when mounting the component dynamically. This is because
    // when we mount the component dynamically, Odoo is not able to access the template
    // configured in the xml file.
    static template = xml`
        <div class="o_list_dynamic_filter d-flex align-items-center me-3 mb-2">
            <label t-att-for="props.fieldConfig.field_name" class="me-2 mb-0 fw-bold">
                <t t-esc="props.fieldConfig.name"/>:
            </label>
            <div class="o_list_custom_select_wrapper position-relative" t-ref="selectWrapper">
                <button
                    type="button"
                    class="btn btn-sm btn-light border o_list_custom_select_toggle"
                    t-on-click="toggleDropdown"
                    t-att-aria-expanded="state.isOpen ? 'true' : 'false'"
                >
                    <span class="o_list_custom_select_value" t-esc="state.selectedItem.name"/>
                    <i class="fa fa-caret-down ms-2"/>
                </button>
                <div
                    t-if="state.isOpen"
                    class="o_list_custom_select_menu position-absolute bg-white border rounded shadow-sm"
                    t-ref="dropdown"
                >
                    <div class="o_list_custom_select_search p-2 border-bottom">
                        <input
                            type="text"
                            class="form-control form-control-sm"
                            placeholder="Search..."
                            t-model="state.searchValue"
                            t-on-input="onSearchInput"
                            t-ref="searchInput"
                        />
                    </div>
                    <div class="o_list_custom_select_items" style="max-height: 250px; overflow-y: auto;">
                        <t t-if="state.filteredItems.length === 0">
                            <div class="p-2 text-muted fst-italic">No results found</div>
                        </t>
                        <t t-else="">
                            <t t-foreach="state.filteredItems" t-as="item" t-key="item.id">
                                <div
                                    class="o_list_custom_select_item p-2"
                                    t-att-class="{'o_selected': item.id === state.selectedItem.id, 'bg-primary text-white fw-bold': item.id === state.selectedItem.id}"
                                    t-on-click="() => this.onItemClick(item)"
                                >
                                    <t t-esc="item.name"/>
                                </div>
                            </t>
                        </t>
                    </div>
                </div>
            </div>
        </div>
    `;

    static props = {
        fieldConfig: {type: Object},
        onValueSelected: {type: Function},
    };

    setup() {
        this.orm = useService("orm");
        this.selectWrapperRef = useRef("selectWrapper");
        this.dropdownRef = useRef("dropdown");
        this.searchInputRef = useRef("searchInput");

        this.state = useState({
            items: [],
            filteredItems: [],
            selectedItem: {id: 0, name: "All"},
            isOpen: false,
            searchValue: "",
        });

        onWillStart(async () => {
            await this.fetchItems();
        });
    }

    async fetchItems() {
        const items = await this.orm.call(this.props.fieldConfig.comodel_name, "search_read", [[]], {
            fields: ["id", "name", "display_name"],
        });

        // Add "All" option
        const allItems = [{id: 0, name: "All"}].concat(
            items.map((item) => ({
                id: item.id,
                name: item.name || item.display_name,
            }))
        );

        this.state.items = allItems;
        this.state.filteredItems = allItems;
    }

    toggleDropdown() {
        this.state.isOpen = !this.state.isOpen;

        if (this.state.isOpen) {
            // Reset search when opening
            this.state.searchValue = "";
            this.state.filteredItems = this.state.items;

            // Add click outside listener
            setTimeout(() => {
                document.addEventListener("click", this.onClickOutside);
            }, 0);

            // Focus search input
            setTimeout(() => {
                if (this.searchInputRef.el) {
                    this.searchInputRef.el.focus();
                }
            }, 50);
        } else {
            // Remove click outside listener
            document.removeEventListener("click", this.onClickOutside);
        }
    }

    onClickOutside(event) {
        if (this.selectWrapperRef.el && !this.selectWrapperRef.el.contains(event.target)) {
            this.state.isOpen = false;
            document.removeEventListener("click", this.onClickOutside);
        }
    }

    onSearchInput() {
        const searchTerm = this.state.searchValue.toLowerCase().trim();

        if (searchTerm === "") {
            this.state.filteredItems = this.state.items;
        } else {
            this.state.filteredItems = this.state.items.filter((item) => item.name.toLowerCase().includes(searchTerm));
        }
    }

    onItemClick(item) {
        this.state.selectedItem = item;
        this.state.isOpen = false;
        document.removeEventListener("click", this.onClickOutside);

        // Notify parent component
        this.props.onValueSelected(this.props.fieldConfig.field_name, item);
    }
}
