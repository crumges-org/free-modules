/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillStart, useState } from "@odoo/owl";

export class FormBuilderWidget extends Component {
    setup() {
        super.setup();
        this.state = useState({
            availableFields: [
                { type: 'text', label: 'Text Input', icon: 'fa-font' },
                { type: 'email', label: 'Email', icon: 'fa-envelope' },
                { type: 'phone', label: 'Phone', icon: 'fa-phone' },
                { type: 'number', label: 'Number', icon: 'fa-hashtag' },
                { type: 'textarea', label: 'Text Area', icon: 'fa-align-left' },
                { type: 'select', label: 'Dropdown', icon: 'fa-list' },
                { type: 'radio', label: 'Radio Buttons', icon: 'fa-dot-circle-o' },
                { type: 'checkbox', label: 'Checkbox', icon: 'fa-check-square-o' },
                { type: 'date', label: 'Date', icon: 'fa-calendar' },
                { type: 'datetime', label: 'Date & Time', icon: 'fa-calendar-plus-o' },
                { type: 'file', label: 'File Upload', icon: 'fa-upload' },
                { type: 'url', label: 'URL', icon: 'fa-link' },
                { type: 'password', label: 'Password', icon: 'fa-lock' },
                { type: 'hidden', label: 'Hidden Field', icon: 'fa-eye-slash' },
            ],
            formFields: [],
            selectedField: null,
            isDragging: false,
        });

        this.setupDragAndDrop();
        this.initializeFormFields();
    }

    initializeFormFields() {
        // Initialize form fields from existing data
        if (this.props.record && this.props.record.data.field_ids) {
            const existingFields = this.props.record.data.field_ids;
            this.state.formFields = existingFields.map((field, index) => ({
                id: field.id || Date.now() + index,
                name: field.name || `field_${index + 1}`,
                label: field.label || 'Untitled Field',
                type: field.field_type || 'text',
                required: field.required || false,
                readonly: field.readonly || false,
                placeholder: field.placeholder || '',
                help_text: field.help_text || '',
                default_value: field.default_value || '',
                min_length: field.min_length || null,
                max_length: field.max_length || null,
                min_value: field.min_value || null,
                max_value: field.max_value || null,
                pattern: field.pattern || '',
                options: field.options || '',
                allowed_file_types: field.allowed_file_types || '',
                max_file_size: field.max_file_size || 5,
                conditional_logic: field.conditional_logic || false,
                condition_field_id: field.condition_field_id || null,
                condition_operator: field.condition_operator || 'equals',
                condition_value: field.condition_value || '',
                css_class: field.css_class || '',
                width: field.width || '100',
                active: field.active !== false,
                sequence: field.sequence || index + 1,
            }));
        }
    }

    setupDragAndDrop() {
        // Setup drag and drop functionality
        this.onFieldDragStart = this.onFieldDragStart.bind(this);
        this.onFieldDragOver = this.onFieldDragOver.bind(this);
        this.onFieldDrop = this.onFieldDrop.bind(this);
        this.onFieldDragEnd = this.onFieldDragEnd.bind(this);
    }

    onFieldDragStart(event, fieldType) {
        this.state.isDragging = true;
        event.dataTransfer.setData('text/plain', fieldType);
        event.dataTransfer.effectAllowed = 'copy';
    }

    onFieldDragOver(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
    }

    onFieldDrop(event) {
        event.preventDefault();
        const fieldType = event.dataTransfer.getData('text/plain');
        this.addField(fieldType);
        this.state.isDragging = false;
    }

    onFieldDragEnd(event) {
        this.state.isDragging = false;
    }

    addField(fieldType) {
        const fieldConfig = this.state.availableFields.find(f => f.type === fieldType);
        if (!fieldConfig) return;

        // Generate a unique name for the field
        const fieldIndex = this.state.formFields.length + 1;
        const fieldName = `field_${fieldIndex}`;

        const newField = {
            id: Date.now(),
            name: fieldName,
            label: fieldConfig.label,
            type: fieldType,
            required: false,
            readonly: false,
            placeholder: '',
            help_text: '',
            default_value: '',
            min_length: null,
            max_length: null,
            min_value: null,
            max_value: null,
            pattern: '',
            options: '',
            allowed_file_types: '',
            max_file_size: 5,
            conditional_logic: false,
            condition_field_id: null,
            condition_operator: 'equals',
            condition_value: '',
            css_class: '',
            width: '100',
            active: true,
            sequence: fieldIndex,
        };

        this.state.formFields.push(newField);
        this.updateFormData();
    }

    removeField(fieldId) {
        const index = this.state.formFields.findIndex(f => f.id === fieldId);
        if (index > -1) {
            this.state.formFields.splice(index, 1);
            this.updateFormData();
        }
    }

    updateField(fieldId, updates) {
        const field = this.state.formFields.find(f => f.id === fieldId);
        if (field) {
            Object.assign(field, updates);
            this.updateFormData();
        }
    }

    selectField(fieldId) {
        this.state.selectedField = this.state.formFields.find(f => f.id === fieldId);
    }

    moveField(fieldId, direction) {
        const index = this.state.formFields.findIndex(f => f.id === fieldId);
        if (index === -1) return;

        if (direction === 'up' && index > 0) {
            [this.state.formFields[index], this.state.formFields[index - 1]] = 
            [this.state.formFields[index - 1], this.state.formFields[index]];
        } else if (direction === 'down' && index < this.state.formFields.length - 1) {
            [this.state.formFields[index], this.state.formFields[index + 1]] = 
            [this.state.formFields[index + 1], this.state.formFields[index]];
        }

        this.updateFormData();
    }

    updateFormData() {
        // Update the form record with the new field data
        if (this.props.record) {
            this.props.record.update({
                field_ids: this.state.formFields.map(field => ({
                    id: field.id,
                    name: field.name,
                    label: field.label,
                    field_type: field.type,
                    required: field.required,
                    readonly: field.readonly,
                    placeholder: field.placeholder,
                    help_text: field.help_text,
                    default_value: field.default_value,
                    min_length: field.min_length,
                    max_length: field.max_length,
                    min_value: field.min_value,
                    max_value: field.max_value,
                    pattern: field.pattern,
                    options: field.options,
                    allowed_file_types: field.allowed_file_types,
                    max_file_size: field.max_file_size,
                    conditional_logic: field.conditional_logic,
                    condition_field_id: field.condition_field_id,
                    condition_operator: field.condition_operator,
                    condition_value: field.condition_value,
                    css_class: field.css_class,
                    width: field.width,
                    active: field.active,
                    sequence: field.sequence,
                }))
            });
        }
    }

    renderFieldPreview(field) {
        const fieldConfig = this.state.availableFields.find(f => f.type === field.type);
        return `
            <div class="field-preview">
                <i class="fa ${fieldConfig?.icon || 'fa-question'}"></i>
                <span>${field.label}</span>
                ${field.required ? '<span class="required-indicator">*</span>' : ''}
            </div>
        `;
    }
}

FormBuilderWidget.template = 'dynamic_custom_odoo_form_builde.FormBuilderWidget';
FormBuilderWidget.props = {
    ...standardFieldProps,
};

registry.category("fields").add("form_builder", FormBuilderWidget);
