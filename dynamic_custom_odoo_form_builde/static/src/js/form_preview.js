/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Form Preview Component
 * Handles form preview rendering and interactions
 */
export class FormPreview extends Component {
    setup() {
        super.setup();
        this.state = useState({
            isPreviewMode: false,
            previewData: {},
            isSubmitting: false,
            submitSuccess: false,
            submitError: null,
        });
        this.previewRef = useRef("preview");
        this.rpc = useService("rpc");
    }

    /**
     * Toggle preview mode
     */
    togglePreview() {
        this.state.isPreviewMode = !this.state.isPreviewMode;
        if (this.state.isPreviewMode) {
            this.loadPreviewData();
        }
    }

    /**
     * Load preview data
     */
    async loadPreviewData() {
        try {
            const data = await this.rpc("/web/dataset/call_kw", {
                model: "dynamic.form",
                method: "get_preview_data",
                args: [this.props.formId],
            });
            this.state.previewData = data;
        } catch (error) {
            console.error("Error loading preview data:", error);
        }
    }

    /**
     * Handle form submission in preview
     */
    async handlePreviewSubmit(event) {
        event.preventDefault();
        this.state.isSubmitting = true;
        this.state.submitError = null;

        try {
            const formData = new FormData(event.target);
            const data = {};
            
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }

            // Simulate form submission
            await this.rpc("/web/dataset/call_kw", {
                model: "dynamic.form",
                method: "preview_submit",
                args: [this.props.formId, data],
            });

            this.state.submitSuccess = true;
            this.state.previewData = {}; // Clear form data
            
            // Reset form
            event.target.reset();
            
            // Show success message
            setTimeout(() => {
                this.state.submitSuccess = false;
            }, 3000);

        } catch (error) {
            this.state.submitError = error.message || "An error occurred during submission";
            console.error("Preview submission error:", error);
        } finally {
            this.state.isSubmitting = false;
        }
    }

    /**
     * Handle field value change in preview
     */
    handleFieldChange(event) {
        const fieldName = event.target.name;
        const fieldValue = event.target.value;
        
        this.state.previewData[fieldName] = fieldValue;
    }

    /**
     * Render field in preview mode
     */
    renderField(field) {
        const fieldId = `preview_${field.id}`;
        const fieldName = field.name;
        const fieldValue = this.state.previewData[fieldName] || "";
        
        switch (field.field_type) {
            case "text":
                return this.renderTextField(field, fieldId, fieldName, fieldValue);
            case "email":
                return this.renderEmailField(field, fieldId, fieldName, fieldValue);
            case "phone":
                return this.renderPhoneField(field, fieldId, fieldName, fieldValue);
            case "number":
                return this.renderNumberField(field, fieldId, fieldName, fieldValue);
            case "textarea":
                return this.renderTextareaField(field, fieldId, fieldName, fieldValue);
            case "select":
                return this.renderSelectField(field, fieldId, fieldName, fieldValue);
            case "radio":
                return this.renderRadioField(field, fieldId, fieldName, fieldValue);
            case "checkbox":
                return this.renderCheckboxField(field, fieldId, fieldName, fieldValue);
            case "date":
                return this.renderDateField(field, fieldId, fieldName, fieldValue);
            case "file":
                return this.renderFileField(field, fieldId, fieldName);
            default:
                return this.renderTextField(field, fieldId, fieldName, fieldValue);
        }
    }

    /**
     * Render text field
     */
    renderTextField(field, fieldId, fieldName, fieldValue) {
        return `
            <div class="form-group">
                <label for="${fieldId}" class="form-label">${field.label}${field.required ? ' *' : ''}</label>
                <input type="text" 
                       id="${fieldId}" 
                       name="${fieldName}" 
                       value="${fieldValue}"
                       placeholder="${field.placeholder || ''}"
                       class="form-control"
                       ${field.required ? 'required' : ''}
                       onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.value}}))">
            </div>
        `;
    }

    /**
     * Render email field
     */
    renderEmailField(field, fieldId, fieldName, fieldValue) {
        return `
            <div class="form-group">
                <label for="${fieldId}" class="form-label">${field.label}${field.required ? ' *' : ''}</label>
                <input type="email" 
                       id="${fieldId}" 
                       name="${fieldName}" 
                       value="${fieldValue}"
                       placeholder="${field.placeholder || 'Enter email'}"
                       class="form-control"
                       ${field.required ? 'required' : ''}
                       onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.value}}))">
            </div>
        `;
    }

    /**
     * Render phone field
     */
    renderPhoneField(field, fieldId, fieldName, fieldValue) {
        return `
            <div class="form-group">
                <label for="${fieldId}" class="form-label">${field.label}${field.required ? ' *' : ''}</label>
                <input type="tel" 
                       id="${fieldId}" 
                       name="${fieldName}" 
                       value="${fieldValue}"
                       placeholder="${field.placeholder || 'Enter phone number'}"
                       class="form-control"
                       ${field.required ? 'required' : ''}
                       onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.value}}))">
            </div>
        `;
    }

    /**
     * Render number field
     */
    renderNumberField(field, fieldId, fieldName, fieldValue) {
        return `
            <div class="form-group">
                <label for="${fieldId}" class="form-label">${field.label}${field.required ? ' *' : ''}</label>
                <input type="number" 
                       id="${fieldId}" 
                       name="${fieldName}" 
                       value="${fieldValue}"
                       placeholder="${field.placeholder || 'Enter number'}"
                       class="form-control"
                       ${field.required ? 'required' : ''}
                       onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.value}}))">
            </div>
        `;
    }

    /**
     * Render textarea field
     */
    renderTextareaField(field, fieldId, fieldName, fieldValue) {
        return `
            <div class="form-group">
                <label for="${fieldId}" class="form-label">${field.label}${field.required ? ' *' : ''}</label>
                <textarea id="${fieldId}" 
                          name="${fieldName}" 
                          placeholder="${field.placeholder || 'Enter text'}"
                          class="form-control"
                          rows="3"
                          ${field.required ? 'required' : ''}
                          onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.value}}))">${fieldValue}</textarea>
            </div>
        `;
    }

    /**
     * Render select field
     */
    renderSelectField(field, fieldId, fieldName, fieldValue) {
        const options = field.options ? JSON.parse(field.options) : [];
        
        let optionsHtml = '<option value="">Select an option</option>';
        options.forEach(option => {
            const selected = option === fieldValue ? 'selected' : '';
            optionsHtml += `<option value="${option}" ${selected}>${option}</option>`;
        });
        
        return `
            <div class="form-group">
                <label for="${fieldId}" class="form-label">${field.label}${field.required ? ' *' : ''}</label>
                <select id="${fieldId}" 
                        name="${fieldName}" 
                        class="form-control"
                        ${field.required ? 'required' : ''}
                        onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.value}}))">
                    ${optionsHtml}
                </select>
            </div>
        `;
    }

    /**
     * Render radio field
     */
    renderRadioField(field, fieldId, fieldName, fieldValue) {
        const options = field.options ? JSON.parse(field.options) : [];
        
        let radioHtml = `<div class="form-group">`;
        radioHtml += `<label class="form-label">${field.label}${field.required ? ' *' : ''}</label>`;
        radioHtml += `<div class="radio-group">`;
        
        options.forEach((option, index) => {
            const radioId = `${fieldId}_${index}`;
            const checked = option === fieldValue ? 'checked' : '';
            radioHtml += `
                <div class="form-check">
                    <input type="radio" 
                           id="${radioId}" 
                           name="${fieldName}" 
                           value="${option}" 
                           class="form-check-input"
                           ${checked}
                           ${field.required ? 'required' : ''}
                           onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.value}}))">
                    <label class="form-check-label" for="${radioId}">${option}</label>
                </div>
            `;
        });
        
        radioHtml += `</div></div>`;
        return radioHtml;
    }

    /**
     * Render checkbox field
     */
    renderCheckboxField(field, fieldId, fieldName, fieldValue) {
        const options = field.options ? JSON.parse(field.options) : [];
        const selectedValues = fieldValue ? fieldValue.split(',') : [];
        
        let checkboxHtml = `<div class="form-group">`;
        checkboxHtml += `<label class="form-label">${field.label}${field.required ? ' *' : ''}</label>`;
        checkboxHtml += `<div class="checkbox-group">`;
        
        options.forEach((option, index) => {
            const checkboxId = `${fieldId}_${index}`;
            const checked = selectedValues.includes(option) ? 'checked' : '';
            checkboxHtml += `
                <div class="form-check">
                    <input type="checkbox" 
                           id="${checkboxId}" 
                           name="${fieldName}[]" 
                           value="${option}" 
                           class="form-check-input"
                           ${checked}
                           onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.value}}))">
                    <label class="form-check-label" for="${checkboxId}">${option}</label>
                </div>
            `;
        });
        
        checkboxHtml += `</div></div>`;
        return checkboxHtml;
    }

    /**
     * Render date field
     */
    renderDateField(field, fieldId, fieldName, fieldValue) {
        return `
            <div class="form-group">
                <label for="${fieldId}" class="form-label">${field.label}${field.required ? ' *' : ''}</label>
                <input type="date" 
                       id="${fieldId}" 
                       name="${fieldName}" 
                       value="${fieldValue}"
                       class="form-control"
                       ${field.required ? 'required' : ''}
                       onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.value}}))">
            </div>
        `;
    }

    /**
     * Render file field
     */
    renderFileField(field, fieldId, fieldName) {
        return `
            <div class="form-group">
                <label for="${fieldId}" class="form-label">${field.label}${field.required ? ' *' : ''}</label>
                <input type="file" 
                       id="${fieldId}" 
                       name="${fieldName}" 
                       class="form-control"
                       ${field.required ? 'required' : ''}
                       onchange="this.dispatchEvent(new CustomEvent('fieldChange', {detail: {name: '${fieldName}', value: this.files[0]?.name || ''}}))">
            </div>
        `;
    }
}

FormPreview.template = "dynamic_custom_odoo_form_builde.FormPreview";
FormPreview.props = {
    formId: { type: Number, optional: false },
    fields: { type: Array, optional: true },
    formData: { type: Object, optional: true },
};

// Register the component
registry.category("components").add("FormPreview", FormPreview);

export default FormPreview;
