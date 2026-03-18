// Global functions for portal templates
// These functions must be globally available for onclick handlers

(function() {
    'use strict';

    // Helper function to make JSON-RPC calls to Odoo
    function jsonRpcCall(url, params) {
        var payload = {
            jsonrpc: '2.0',
            method: 'call',
            params: params,
            id: Math.floor(Math.random() * 1000000)
        };
        
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(function(response) {
            // Handle JSON-RPC format: {jsonrpc: "2.0", result: {...}}
            if (response.error) {
                throw new Error(response.error.data ? response.error.data.message : response.error.message || 'Server error');
            }
            return response.result || response;
        });
    }

    // Get CSRF token
    function getCSRFToken() {
        var csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) {
            return csrfInput.value;
        }
        // Try to get from cookie
        var match = document.cookie.match(/csrf_token=([^;]+)/);
        if (match) {
            return match[1];
        }
        // Try odoo global
        if (typeof odoo !== 'undefined' && odoo.csrf_token) {
            return odoo.csrf_token;
        }
        return '';
    }
    
    // Make getCSRFToken globally available
    window.getCSRFToken = getCSRFToken;

    window.createLead = function() {
        var form = document.getElementById('createLeadForm');
        if (!form) {
            alert('Form not found');
            return;
        }
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        var formData = new FormData(form);
        var data = {};
        formData.forEach(function(value, key) {
            data[key] = value;
        });

        var btn = event.target;
        var originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> Creating...';

        data.csrf_token = getCSRFToken();
        
        jsonRpcCall('/my/lead/create', data)
        .then(function(result) {
            if (result.success) {
                alert('Lead created successfully!');
                // Close modal using data-bs-dismiss or jQuery fallback
                var modalEl = document.getElementById('createLeadModal');
                if (modalEl) {
                    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                        var modal = bootstrap.Modal.getInstance(modalEl);
                        if (modal) modal.hide();
                    } else {
                        var closeBtn = modalEl.querySelector('[data-bs-dismiss="modal"]');
                        if (closeBtn) closeBtn.click();
                    }
                }
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to create lead'));
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
            btn.disabled = false;
            btn.innerHTML = originalText;
        });
    };

})(); // End IIFE
