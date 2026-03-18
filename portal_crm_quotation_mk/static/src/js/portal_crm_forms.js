// Global functions for CRM forms - Portal templates
// These functions must be globally available for onclick handlers

(function() {
    'use strict';
    
    var editMode = false;
    var originalFormData = {};

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

    window.toggleEditMode = function() {
        editMode = !editMode;
        var form = document.getElementById('leadForm') || document.getElementById('opportunityForm');
        if (!form) return;

        var inputs = form.querySelectorAll('input, textarea, select');
        var saveBtnContainer = document.getElementById('saveBtnContainer');
        var editBtn = document.querySelector('button[onclick="toggleEditMode()"]');
        var editBtnText = document.getElementById('editBtnText');

        if (editMode) {
            // Save original data
            inputs.forEach(function(input) {
                originalFormData[input.name] = input.value;
                input.removeAttribute('readonly');
                input.classList.add('form-control');
            });
            
            form.classList.add('edit-mode');
            if (saveBtnContainer) saveBtnContainer.style.display = 'block';
            if (editBtnText) editBtnText.textContent = 'Cancel';
        } else {
            // Restore original data
            inputs.forEach(function(input) {
                input.setAttribute('readonly', 'readonly');
                if (originalFormData[input.name] !== undefined) {
                    input.value = originalFormData[input.name];
                }
            });
            
            form.classList.remove('edit-mode');
            if (saveBtnContainer) saveBtnContainer.style.display = 'none';
            if (editBtnText) editBtnText.textContent = 'Edit';
            originalFormData = {};
        }
    };

    window.cancelEdit = function() {
        editMode = false;
        toggleEditMode();
    };

    window.saveLead = function() {
        var form = document.getElementById('leadForm');
        if (!form) return;

        var formData = new FormData(form);
        var data = {};
        formData.forEach(function(value, key) {
            data[key] = value;
        });

        var leadId = window.location.pathname.match(/\/(\d+)$/);
        if (!leadId) {
            alert('Invalid lead ID');
            return;
        }

        var btn = event.target;
        var originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> Saving...';

        data.csrf_token = getCSRFToken();
        
        jsonRpcCall('/my/lead/' + leadId[1] + '/update', data)
        .then(function(result) {
            if (result.success) {
                alert('Lead updated successfully!');
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to update lead'));
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

    window.changeStage = function(element) {
        var stageId = element.getAttribute('data-stage-id');
        var leadId = window.location.pathname.match(/\/(\d+)$/);
        if (!leadId) {
            alert('Invalid lead ID');
            return;
        }

        // Don't ask for confirmation on statusbar clicks (like Odoo backend)
        var btn = element;
        var originalClass = btn.className;
        btn.style.opacity = '0.6';
        btn.style.cursor = 'wait';

        jsonRpcCall('/my/lead/' + leadId[1] + '/change_stage', {
            stage_id: parseInt(stageId),
            csrf_token: getCSRFToken()
        })
        .then(function(result) {
            if (result.success) {
                // Reload page to show updated data
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to change stage'));
                btn.className = originalClass;
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
            btn.className = originalClass;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
        });
    };

    window.restoreOpportunity = function() {
        var oppId = window.location.pathname.match(/\/(\d+)$/);
        if (!oppId) {
            alert('Invalid opportunity ID');
            return;
        }

        if (!confirm('Are you sure you want to restore this opportunity?')) {
            return;
        }

        jsonRpcCall('/my/lead/' + oppId[1] + '/restore', {
            csrf_token: getCSRFToken()
        })
        .then(function(result) {
            if (result.success) {
                alert('Opportunity restored successfully!');
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to restore opportunity'));
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
        });
    };

    window.winOpportunity = function() {
        var oppId = window.location.pathname.match(/\/(\d+)$/);
        if (!oppId) {
            alert('Invalid opportunity ID');
            return;
        }

        if (!confirm('Are you sure you want to mark this opportunity as won?')) {
            return;
        }

        jsonRpcCall('/my/lead/' + oppId[1] + '/win', {
            csrf_token: getCSRFToken()
        })
        .then(function(result) {
            if (result.success) {
                alert('Opportunity marked as won!');
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to mark as won'));
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
        });
    };

    window.lostOpportunity = function() {
        var oppId = window.location.pathname.match(/\/(\d+)$/);
        if (!oppId) {
            alert('Invalid opportunity ID');
            return;
        }

        if (!confirm('Are you sure you want to mark this opportunity as lost?')) {
            return;
        }

        jsonRpcCall('/my/lead/' + oppId[1] + '/lost', {
            csrf_token: getCSRFToken()
        })
        .then(function(result) {
            if (result.success) {
                alert('Opportunity marked as lost!');
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to mark as lost'));
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
        });
    };

    window.createQuotation = function() {
        var leadId = window.location.pathname.match(/\/(\d+)$/);
        if (!leadId) {
            alert('Invalid lead ID');
            return;
        }

        if (!confirm('Create a new quotation from this lead/opportunity?')) {
            return;
        }

        var btn = event.target;
        var originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> Creating...';

        jsonRpcCall('/my/lead/' + leadId[1] + '/create_quotation', {
            csrf_token: getCSRFToken()
        })
        .then(function(result) {
            if (result.success || result.id) {
                alert('Quotation created successfully!');
                // Odoo 17 uses /my/orders/ for quotations
                window.location.href = '/my/orders/' + (result.id || result.quotation_id);
            } else {
                alert('Error: ' + (result.error || 'Failed to create quotation'));
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
