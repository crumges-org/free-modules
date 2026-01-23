/**
 * Dynamic Forms Embed Script
 * This script handles the embedding of dynamic forms in external websites
 */

(function() {
    'use strict';
    
    // Global configuration
    window.DynamicForms = window.DynamicForms || {};
    
    // Form class
    function DynamicForm(config) {
        this.config = config;
        this.container = null;
        this.form = null;
        this.fields = [];
        this.isInitialized = false;
        
        this.init();
    }
    
    DynamicForm.prototype.init = function() {
        this.createContainer();
        this.renderForm();
        this.setupEventListeners();
        this.isInitialized = true;
    };
    
    DynamicForm.prototype.createContainer = function() {
        this.container = document.createElement('div');
        this.container.id = 'dynamic-form-' + this.config.id;
        this.container.className = 'dynamic-form-container';
        this.container.style.cssText = this.getContainerStyles();
        
        // Insert into page
        document.currentScript.parentNode.insertBefore(this.container, document.currentScript);
    };
    
    DynamicForm.prototype.getContainerStyles = function() {
        return `
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
            border: 1px solid #e9ecef;
        `;
    };
    
    DynamicForm.prototype.renderForm = function() {
        this.container.innerHTML = this.getFormHTML();
        this.form = this.container.querySelector('#dynamic-form');
        this.renderFields();
    };
    
    DynamicForm.prototype.getFormHTML = function() {
        return `
            <div class="form-header" style="padding: 30px; text-align: center; border-bottom: 1px solid #e9ecef;">
                <h2 class="form-title" style="font-size: 24px; font-weight: 600; color: #333; margin: 0 0 10px 0;">
                    ${this.config.name}
                </h2>
                ${this.config.description ? `
                    <p class="form-description" style="color: #666; font-size: 16px; line-height: 1.5; margin: 0;">
                        ${this.config.description}
                    </p>
                ` : ''}
            </div>
            <div class="form-body" style="padding: 30px;">
                ${this.config.show_progress_bar ? `
                    <div class="form-progress" style="margin-bottom: 30px;">
                        <div class="progress-bar" style="width: 100%; height: 6px; background-color: #e9ecef; border-radius: 3px; overflow: hidden;">
                            <div class="progress-fill" style="height: 100%; background-color: ${this.config.primary_color || '#007bff'}; transition: width 0.3s ease; width: 0%;"></div>
                        </div>
                    </div>
                ` : ''}
                <div id="form-messages"></div>
                <form id="dynamic-form" novalidate>
                    <div id="form-fields"></div>
                    ${this.config.show_submit_button ? `
                        <div class="form-submit" style="text-align: center; margin-top: 30px;">
                            <button type="submit" class="submit-button" style="background-color: ${this.config.primary_color || '#007bff'}; color: white; border: none; padding: 15px 40px; font-size: 18px; font-weight: 600; border-radius: 6px; cursor: pointer; transition: background-color 0.3s ease;">
                                ${this.config.submit_button_text || 'Submit'}
                            </button>
                        </div>
                    ` : ''}
                </form>
            </div>
        `;
    };
    
    DynamicForm.prototype.renderFields = function() {
        const fieldsContainer = this.container.querySelector('#form-fields');
        fieldsContainer.innerHTML = '';
        
        this.config.fields.forEach(field => {
            const fieldElement = this.createFieldElement(field);
            if (fieldElement) {
                fieldsContainer.appendChild(fieldElement);
            }
        });
    };
    
    DynamicForm.prototype.createFieldElement = function(field) {
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'form-field';
        fieldDiv.style.cssText = `
            margin-bottom: 25px;
            width: ${field.width || 100}%;
        `;
        
        const label = document.createElement('label');
        label.className = 'field-label';
        label.htmlFor = field.name;
        label.innerHTML = field.label;
        if (field.required) {
            label.innerHTML += ' <span class="field-required" style="color: #dc3545;">*</span>';
        }
        label.style.cssText = `
            display: block;
            font-weight: 500;
            color: #333;
            margin-bottom: 8px;
        `;
        
        const input = this.createInputElement(field);
        
        fieldDiv.appendChild(label);
        fieldDiv.appendChild(input);
        
        if (field.help_text) {
            const help = document.createElement('div');
            help.className = 'field-help';
            help.innerHTML = field.help_text;
            help.style.cssText = `
                font-size: 14px;
                color: #666;
                margin-top: 5px;
            `;
            fieldDiv.appendChild(help);
        }
        
        return fieldDiv;
    };
    
    DynamicForm.prototype.createInputElement = function(field) {
        let input;
        
        switch (field.type) {
            case 'textarea':
                input = document.createElement('textarea');
                input.style.cssText = `
                    width: 100%;
                    padding: 12px 15px;
                    border: 2px solid #e9ecef;
                    border-radius: 6px;
                    font-size: 16px;
                    transition: border-color 0.3s ease;
                    min-height: 100px;
                    resize: vertical;
                    font-family: inherit;
                `;
                break;
            case 'select':
                input = document.createElement('select');
                input.style.cssText = `
                    width: 100%;
                    padding: 12px 15px;
                    border: 2px solid #e9ecef;
                    border-radius: 6px;
                    font-size: 16px;
                    transition: border-color 0.3s ease;
                    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
                    background-position: right 12px center;
                    background-repeat: no-repeat;
                    background-size: 16px;
                    padding-right: 40px;
                    font-family: inherit;
                `;
                if (field.options) {
                    field.options.forEach(option => {
                        const optionElement = document.createElement('option');
                        optionElement.value = option;
                        optionElement.textContent = option;
                        input.appendChild(optionElement);
                    });
                }
                break;
            case 'radio':
                input = document.createElement('div');
                input.style.cssText = `
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                `;
                if (field.options) {
                    field.options.forEach((option, index) => {
                        const radioDiv = document.createElement('div');
                        radioDiv.style.cssText = `
                            display: flex;
                            align-items: center;
                            gap: 10px;
                        `;
                        
                        const radio = document.createElement('input');
                        radio.type = 'radio';
                        radio.name = field.name;
                        radio.value = option;
                        radio.id = field.name + '_' + index;
                        radio.style.cssText = `
                            width: 18px;
                            height: 18px;
                        `;
                        
                        const radioLabel = document.createElement('label');
                        radioLabel.htmlFor = field.name + '_' + index;
                        radioLabel.textContent = option;
                        radioLabel.style.cssText = `
                            font-family: inherit;
                            color: #333;
                        `;
                        
                        radioDiv.appendChild(radio);
                        radioDiv.appendChild(radioLabel);
                        input.appendChild(radioDiv);
                    });
                }
                break;
            case 'checkbox':
                input = document.createElement('input');
                input.type = 'checkbox';
                input.style.cssText = `
                    width: 18px;
                    height: 18px;
                `;
                break;
            case 'file':
                input = document.createElement('input');
                input.type = 'file';
                input.style.cssText = `
                    width: 100%;
                    padding: 12px 15px;
                    border: 2px solid #e9ecef;
                    border-radius: 6px;
                    font-size: 16px;
                    transition: border-color 0.3s ease;
                    font-family: inherit;
                `;
                break;
            default:
                input = document.createElement('input');
                input.type = field.type;
                input.style.cssText = `
                    width: 100%;
                    padding: 12px 15px;
                    border: 2px solid #e9ecef;
                    border-radius: 6px;
                    font-size: 16px;
                    transition: border-color 0.3s ease;
                    font-family: inherit;
                `;
                break;
        }
        
        input.name = field.name;
        input.id = field.name;
        
        if (field.required) {
            input.required = true;
        }
        
        if (field.readonly) {
            input.readOnly = true;
        }
        
        if (field.placeholder) {
            input.placeholder = field.placeholder;
        }
        
        if (field.default_value) {
            input.value = field.default_value;
        }
        
        // Add focus styles
        input.addEventListener('focus', () => {
            input.style.outline = 'none';
            input.style.borderColor = this.config.primary_color || '#007bff';
        });
        
        input.addEventListener('blur', () => {
            input.style.borderColor = '#e9ecef';
        });
        
        return input;
    };
    
    DynamicForm.prototype.setupEventListeners = function() {
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitForm();
        });
        
        if (this.config.show_progress_bar) {
            this.setupProgressBar();
        }
    };
    
    DynamicForm.prototype.submitForm = function() {
        const submitButton = this.form.querySelector('.submit-button');
        const messagesContainer = this.container.querySelector('#form-messages');
        
        // Show loading state
        submitButton.disabled = true;
        submitButton.textContent = 'Submitting...';
        submitButton.style.backgroundColor = '#6c757d';
        
        // Clear previous messages
        messagesContainer.innerHTML = '';
        
        // Collect form data
        const formData = this.collectFormData();
        
        // Validate form
        if (!this.validateForm(formData)) {
            submitButton.disabled = false;
            submitButton.textContent = this.config.submit_button_text || 'Submit';
            submitButton.style.backgroundColor = this.config.primary_color || '#007bff';
            return;
        }
        
        // Submit form
        fetch(this.config.submit_url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                form_data: formData
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showMessage('success', data.message);
                this.form.reset();
            } else {
                this.showMessage('error', data.error);
            }
        })
        .catch(error => {
            this.showMessage('error', 'An error occurred. Please try again.');
            console.error('Error:', error);
        })
        .finally(() => {
            submitButton.disabled = false;
            submitButton.textContent = this.config.submit_button_text || 'Submit';
            submitButton.style.backgroundColor = this.config.primary_color || '#007bff';
        });
    };
    
    DynamicForm.prototype.collectFormData = function() {
        const formData = {};
        
        const fields = this.form.querySelectorAll('input, select, textarea');
        fields.forEach(field => {
            if (field.type === 'checkbox') {
                formData[field.name] = field.checked;
            } else if (field.type === 'radio') {
                if (field.checked) {
                    formData[field.name] = field.value;
                }
            } else if (field.type === 'file') {
                if (field.files.length > 0) {
                    formData[field.name] = field.files[0];
                }
            } else {
                formData[field.name] = field.value;
            }
        });
        
        return formData;
    };
    
    DynamicForm.prototype.validateForm = function(formData) {
        const fields = this.config.fields || [];
        let isValid = true;
        
        fields.forEach(field => {
            const value = formData[field.name];
            const fieldElement = document.getElementById(field.name);
            
            // Clear previous errors
            this.clearFieldError(fieldElement);
            
            // Required validation
            if (field.required && (!value || value === '')) {
                this.showFieldError(fieldElement, 'This field is required.');
                isValid = false;
                return;
            }
            
            // Type-specific validation
            if (value && value !== '') {
                if (!this.validateFieldValue(field, value)) {
                    isValid = false;
                }
            }
        });
        
        return isValid;
    };
    
    DynamicForm.prototype.validateFieldValue = function(field, value) {
        const fieldElement = document.getElementById(field.name);
        
        // Email validation
        if (field.type === 'email') {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                this.showFieldError(fieldElement, 'Please enter a valid email address.');
                return false;
            }
        }
        
        // Length validation
        if (field.validation_rules) {
            const rules = field.validation_rules;
            
            if (rules.min_length && value.length < rules.min_length) {
                this.showFieldError(fieldElement, `Minimum length is ${rules.min_length} characters.`);
                return false;
            }
            
            if (rules.max_length && value.length > rules.max_length) {
                this.showFieldError(fieldElement, `Maximum length is ${rules.max_length} characters.`);
                return false;
            }
            
            if (rules.min_value !== undefined && parseFloat(value) < rules.min_value) {
                this.showFieldError(fieldElement, `Minimum value is ${rules.min_value}.`);
                return false;
            }
            
            if (rules.max_value !== undefined && parseFloat(value) > rules.max_value) {
                this.showFieldError(fieldElement, `Maximum value is ${rules.max_value}.`);
                return false;
            }
            
            if (rules.pattern) {
                const regex = new RegExp(rules.pattern);
                if (!regex.test(value)) {
                    this.showFieldError(fieldElement, 'Format is invalid.');
                    return false;
                }
            }
        }
        
        return true;
    };
    
    DynamicForm.prototype.showFieldError = function(fieldElement, message) {
        if (!fieldElement) return;
        
        fieldElement.style.borderColor = '#dc3545';
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            color: #dc3545;
            font-size: 14px;
            margin-top: 5px;
        `;
        
        fieldElement.parentNode.appendChild(errorDiv);
    };
    
    DynamicForm.prototype.clearFieldError = function(fieldElement) {
        if (!fieldElement) return;
        
        fieldElement.style.borderColor = '#e9ecef';
        
        const errorDiv = fieldElement.parentNode.querySelector('.field-error');
        if (errorDiv) {
            errorDiv.remove();
        }
    };
    
    DynamicForm.prototype.showMessage = function(type, message) {
        const messagesContainer = this.container.querySelector('#form-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'form-message message-' + type;
        messageDiv.textContent = message;
        messageDiv.style.cssText = `
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            text-align: center;
            ${type === 'success' ? 
                'background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;' : 
                'background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;'
            }
        `;
        
        messagesContainer.appendChild(messageDiv);
        
        // Auto-remove success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                messageDiv.remove();
            }, 5000);
        }
    };
    
    DynamicForm.prototype.setupProgressBar = function() {
        const progressFill = this.container.querySelector('.progress-fill');
        if (!progressFill) return;
        
        const fields = this.container.querySelectorAll('.form-field');
        const totalFields = fields.length;
        
        fields.forEach(field => {
            const inputs = field.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('input', () => {
                    this.updateProgress();
                });
            });
        });
        
        this.updateProgress = function() {
            const filledFields = this.container.querySelectorAll('.form-field input:not([type="submit"]):valid, .form-field select:valid, .form-field textarea:valid');
            const progress = (filledFields.length / totalFields) * 100;
            progressFill.style.width = Math.min(progress, 100) + '%';
        };
    };
    
    // Global API
    window.DynamicForms.create = function(config) {
        return new DynamicForm(config);
    };
    
    window.DynamicForms.load = function(formId, options = {}) {
        const baseUrl = options.baseUrl || window.location.origin;
        
        fetch(`${baseUrl}/dynamic-form/view/${formId}.js`)
            .then(response => response.text())
            .then(scriptContent => {
                // Execute the script content
                const script = document.createElement('script');
                script.textContent = scriptContent;
                document.head.appendChild(script);
            })
            .catch(error => {
                console.error('Error loading dynamic form:', error);
            });
    };
    
})();
