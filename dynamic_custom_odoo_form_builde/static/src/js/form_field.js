/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Form Field Component
 * Handles individual form field rendering and interactions
 */
export class FormField extends Component {
    setup() {
        super.setup();
        this.state = useState({
            isEditing: false,
            isDragging: false,
            isSelected: false,
        });
        this.fieldRef = useRef("field");
        this.rpc = useService("rpc");
    }

    /**
     * Toggle field editing mode
     */
    toggleEdit() {
        this.state.isEditing = !this.state.isEditing;
    }

    /**
     * Handle field selection
     */
    selectField() {
        this.state.isSelected = true;
        this.props.onFieldSelect?.(this.props.field);
    }

    /**
     * Handle field deletion
     */
    async deleteField() {
        if (confirm("Are you sure you want to delete this field?")) {
            try {
                await this.rpc("/web/dataset/call_kw", {
                    model: "dynamic.form.field",
                    method: "unlink",
                    args: [[this.props.field.id]],
                });
                this.props.onFieldDeleted?.(this.props.field.id);
            } catch (error) {
                console.error("Error deleting field:", error);
            }
        }
    }

    /**
     * Handle field duplication
     */
    async duplicateField() {
        try {
            const newField = await this.rpc("/web/dataset/call_kw", {
                model: "dynamic.form.field",
                method: "copy",
                args: [this.props.field.id],
            });
            this.props.onFieldDuplicated?.(newField);
        } catch (error) {
            console.error("Error duplicating field:", error);
        }
    }

    /**
     * Handle drag start
     */
    onDragStart(event) {
        this.state.isDragging = true;
        event.dataTransfer.setData("text/plain", JSON.stringify(this.props.field));
        event.dataTransfer.effectAllowed = "move";
    }

    /**
     * Handle drag end
     */
    onDragEnd() {
        this.state.isDragging = false;
    }

    /**
     * Render field preview based on field type
     */
    renderFieldPreview() {
        const { field } = this.props;
        
        switch (field.field_type) {
            case "text":
                return `<input type="text" placeholder="${field.placeholder || 'Enter text'}" class="form-control" readonly>`;
            case "email":
                return `<input type="email" placeholder="${field.placeholder || 'Enter email'}" class="form-control" readonly>`;
            case "phone":
                return `<input type="tel" placeholder="${field.placeholder || 'Enter phone'}" class="form-control" readonly>`;
            case "number":
                return `<input type="number" placeholder="${field.placeholder || 'Enter number'}" class="form-control" readonly>`;
            case "textarea":
                return `<textarea placeholder="${field.placeholder || 'Enter text'}" class="form-control" rows="3" readonly></textarea>`;
            case "select":
                return this.renderSelectPreview();
            case "radio":
                return this.renderRadioPreview();
            case "checkbox":
                return this.renderCheckboxPreview();
            case "date":
                return `<input type="date" class="form-control" readonly>`;
            case "file":
                return `<input type="file" class="form-control" readonly>`;
            default:
                return `<input type="text" placeholder="Field preview" class="form-control" readonly>`;
        }
    }

    /**
     * Render select field preview
     */
    renderSelectPreview() {
        const { field } = this.props;
        const options = field.options ? JSON.parse(field.options) : [];
        
        let optionsHtml = '<option value="">Select an option</option>';
        options.forEach(option => {
            optionsHtml += `<option value="${option}">${option}</option>`;
        });
        
        return `<select class="form-control" readonly>${optionsHtml}</select>`;
    }

    /**
     * Render radio field preview
     */
    renderRadioPreview() {
        const { field } = this.props;
        const options = field.options ? JSON.parse(field.options) : [];
        
        let radioHtml = '';
        options.forEach((option, index) => {
            radioHtml += `
                <div class="form-check">
                    <input type="radio" class="form-check-input" name="radio_${field.id}" id="radio_${field.id}_${index}" readonly>
                    <label class="form-check-label" for="radio_${field.id}_${index}">${option}</label>
                </div>
            `;
        });
        
        return radioHtml;
    }

    /**
     * Render checkbox field preview
     */
    renderCheckboxPreview() {
        const { field } = this.props;
        const options = field.options ? JSON.parse(field.options) : [];
        
        let checkboxHtml = '';
        options.forEach((option, index) => {
            checkboxHtml += `
                <div class="form-check">
                    <input type="checkbox" class="form-check-input" id="checkbox_${field.id}_${index}" readonly>
                    <label class="form-check-label" for="checkbox_${field.id}_${index}">${option}</label>
                </div>
            `;
        });
        
        return checkboxHtml;
    }
}

FormField.template = "dynamic_custom_odoo_form_builde.FormField";
FormField.props = {
    field: { type: Object, optional: false },
    onFieldSelect: { type: Function, optional: true },
    onFieldDeleted: { type: Function, optional: true },
    onFieldDuplicated: { type: Function, optional: true },
};

// Register the component
registry.category("components").add("FormField", FormField);

export default FormField;
