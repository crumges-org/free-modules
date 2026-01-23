/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Custom Form Field Widget
 * Adds options button for dropdown, radio, and checkbox fields
 */
export class FormFieldWidget extends CharField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.rpc = useService("rpc");
    }

    /**
     * Open options dialog for field
     */
    async openOptionsDialog() {
        const fieldRecord = this.props.record;
        const fieldType = fieldRecord.data.field_type;
        
        if (!['select', 'radio', 'checkbox'].includes(fieldType)) {
            return;
        }

        // Create options dialog
        const dialogProps = {
            title: `Configure Options for ${fieldRecord.data.label || 'Field'}`,
            body: this.createOptionsDialogBody(fieldRecord),
            buttons: [
                {
                    text: "Save Options",
                    primary: true,
                    click: () => this.saveOptions(fieldRecord),
                },
                {
                    text: "Cancel",
                    close: true,
                },
            ],
        };

        this.dialog.add(OptionsDialog, dialogProps);
    }

    /**
     * Create options dialog body
     */
    createOptionsDialogBody(fieldRecord) {
        const currentOptions = fieldRecord.data.options || '';
        const fieldType = fieldRecord.data.field_type;
        
        return `
            <div class="options-dialog-body">
                <div class="alert alert-info">
                    <strong>Instructions:</strong>
                    <ul>
                        <li>Enter each option on a separate line</li>
                        <li>For ${fieldType} fields: Options will appear as ${this.getFieldTypeDescription(fieldType)}</li>
                        <li>At least one option is required</li>
                    </ul>
                </div>
                <div class="form-group">
                    <label for="options-textarea">Options (one per line):</label>
                    <textarea id="options-textarea" class="form-control" rows="8" placeholder="Enter options, one per line&#10;Example:&#10;Option 1&#10;Option 2&#10;Option 3">${currentOptions}</textarea>
                </div>
                <div class="form-group">
                    <label for="help-text">Help Text (optional):</label>
                    <textarea id="help-text" class="form-control" rows="3" placeholder="Enter help text for this field">${fieldRecord.data.help_text || ''}</textarea>
                </div>
            </div>
        `;
    }

    /**
     * Get field type description
     */
    getFieldTypeDescription(fieldType) {
        switch (fieldType) {
            case 'select':
                return 'dropdown menu options';
            case 'radio':
                return 'radio button choices';
            case 'checkbox':
                return 'individual checkboxes';
            default:
                return 'options';
        }
    }

    /**
     * Save options from dialog
     */
    async saveOptions(fieldRecord) {
        const optionsTextarea = document.getElementById('options-textarea');
        const helpTextarea = document.getElementById('help-text');
        
        if (!optionsTextarea) {
            return;
        }

        const options = optionsTextarea.value;
        const helpText = helpTextarea ? helpTextarea.value : '';

        // Validate options
        if (!options.trim()) {
            alert('At least one option is required for this field type.');
            return;
        }

        try {
            // Update the field record
            fieldRecord.update({
                options: options,
                help_text: helpText,
            });

            // Close dialog
            this.dialog.close();
            
            // Show success message
            this.env.services.notification.add('Options saved successfully!', {
                type: 'success',
            });
        } catch (error) {
            console.error('Error saving options:', error);
            this.env.services.notification.add('Error saving options. Please try again.', {
                type: 'danger',
            });
        }
    }
}

/**
 * Options Dialog Component
 */
class OptionsDialog {
    constructor(props) {
        this.props = props;
    }

    setup() {
        // Dialog setup
    }

    close() {
        this.props.close();
    }
}

// Register the widget
registry.category("fields").add("form_field_widget", FormFieldWidget);

export default FormFieldWidget;
