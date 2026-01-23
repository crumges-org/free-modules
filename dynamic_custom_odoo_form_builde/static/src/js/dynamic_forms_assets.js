/** @odoo-module **/

/**
 * Dynamic Forms Assets Manager
 * Adds addon-specific CSS classes to body tag for custom styling
 */

/**
 * Function to get current model from URL
 */
function getCurrentModelFromURL() {
    const url = window.location.href;
    
    if (url.includes('dynamic.form')) {
        if (url.includes('field')) {
            return 'dynamic.form.field';
        } else if (url.includes('submission')) {
            return 'dynamic.form.submission';
        } else if (url.includes('email.notification')) {
            return 'dynamic.form.email.notification';
        } else {
            return 'dynamic.form';
        }
    }
    
    return null;
}

/**
 * Function to check if current view is kanban
 */
function isKanbanView() {
    const url = window.location.href;
    const urlParams = new URLSearchParams(window.location.search);
    
    // Check URL parameters
    if (urlParams.get('view_type') === 'kanban') {
        return true;
    }
    
    // Check URL hash/fragment
    if (url.includes('view_type=kanban') || url.includes('kanban')) {
        return true;
    }
    
    // Check if kanban view is active by looking for kanban renderer
    const kanbanRenderer = document.querySelector('.o_kanban_renderer');
    if (kanbanRenderer && url.includes('dynamic.form') && !url.includes('form')) {
        return true;
    }
    
    return false;
}

/**
 * Function to update model classes
 */
function updateModelClasses(model) {
    const body = document.body;
    if (!body) return;

    // Remove existing model classes
    body.classList.remove('dynamic-form-model', 'dynamic-form-field-model', 'dynamic-form-submission-model', 'dynamic-form-email-notification-model');
    
    // Add specific model class
    if (model) {
        switch (model) {
            case 'dynamic.form':
                body.classList.add('dynamic-form-model');
                break;
            case 'dynamic.form.field':
                body.classList.add('dynamic-form-field-model');
                break;
            case 'dynamic.form.submission':
                body.classList.add('dynamic-form-submission-model');
                break;
            case 'dynamic.form.email.notification':
                body.classList.add('dynamic-form-email-notification-model');
                break;
        }
    }
}

/**
 * Function to initialize classes
 */
function initializeClasses() {
    const body = document.body;
    if (body) {
        // Check if we're on dynamic.form kanban view
        const currentModel = getCurrentModelFromURL();
        const isKanban = isKanbanView();
        
        // Add main addon class only for dynamic.form model
        if (currentModel === 'dynamic.form') {
            if (!body.classList.contains('dynamic-forms-addon')) {
                body.classList.add('dynamic-forms-addon');
            }
            
            // Add kanban-specific class
            if (isKanban) {
                if (!body.classList.contains('dynamic-form-kanban-view')) {
                    body.classList.add('dynamic-form-kanban-view');
                }
            } else {
                body.classList.remove('dynamic-form-kanban-view');
            }
        } else {
            // Remove classes if not on dynamic.form
            body.classList.remove('dynamic-forms-addon', 'dynamic-form-kanban-view');
        }
        
        // Add model-specific class
        updateModelClasses(currentModel);
    }
}

// Run immediately if body exists, otherwise wait for DOM
if (document.body) {
    initializeClasses();
} else {
    document.addEventListener('DOMContentLoaded', initializeClasses);
}

// Also run on window load to catch any late changes
window.addEventListener('load', initializeClasses);

// Watch for URL changes using history API (for SPA navigation)
let currentUrl = window.location.href;
const urlCheckInterval = setInterval(() => {
    if (window.location.href !== currentUrl) {
        currentUrl = window.location.href;
        initializeClasses();
    }
}, 1000);

// Clean up interval when page unloads
window.addEventListener('beforeunload', () => {
    clearInterval(urlCheckInterval);
});

// Export for potential future use
export { initializeClasses, getCurrentModelFromURL, updateModelClasses, isKanbanView };
