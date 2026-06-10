/** @odoo-module **/

console.log("Dropdown JS Loaded");

const ELD_ACTION_LABEL = 'Sync ELD Location History';
const ELD_TOOLTIP = "Pulls location pings from the assigned Samsara ELD and merges them into this shipment’s Location History.";

// Update tooltip for all matching dropdown items
function updateELDTooltip() {
    document.querySelectorAll('span.dropdown-item.o_menu_item').forEach(item => {
        if (item.textContent.trim() === ELD_ACTION_LABEL) {
            if (item.getAttribute('title') !== ELD_TOOLTIP) {
                item.setAttribute('title', ELD_TOOLTIP);
                // Optionally, update aria-label for accessibility
                item.setAttribute('aria-label', ELD_TOOLTIP);
                console.log('Updated tooltip for Sync ELD Location History');
            }
        }
    });
}

// Debounce utility to avoid excessive DOM updates
function debounce(fn, delay) {
    let timer = null;
    return function () {
        clearTimeout(timer);
        timer = setTimeout(fn, delay);
    };
}

const debouncedUpdate = debounce(updateELDTooltip, 100);

// Observe DOM changes to handle dynamic dropdowns
function handleDynamicContent() {
    const observer = new MutationObserver((mutations) => {
        let found = false;
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === 1 && node.textContent && node.textContent.includes(ELD_ACTION_LABEL)) {
                    found = true;
                    break;
                }
            }
            if (found) break;
        }
        if (found) debouncedUpdate();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return observer;
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        updateELDTooltip();
        handleDynamicContent();
    });
} else {
    // updateELDTooltip();
    // handleDynamicContent();
    init();
}
