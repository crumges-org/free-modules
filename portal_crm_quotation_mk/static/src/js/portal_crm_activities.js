// Activity management functions - Global functions for portal templates
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

    window.scheduleActivity = function() {
        var form = document.getElementById('scheduleActivityForm');
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

        var leadId = window.location.pathname.match(/\/(\d+)$/);
        if (!leadId) {
            alert('Invalid lead ID');
            return;
        }

        var btn = event.target;
        var originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> Scheduling...';

        data.csrf_token = getCSRFToken();
        
        jsonRpcCall('/my/lead/' + leadId[1] + '/schedule_activity', data)
        .then(function(result) {
            if (result.success) {
                alert('Activity scheduled successfully!');
                // Close modal using data-bs-dismiss or jQuery fallback
                var modalEl = document.getElementById('scheduleActivityModal');
                if (modalEl) {
                    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                        var modal = bootstrap.Modal.getInstance(modalEl);
                        if (modal) modal.hide();
                    } else {
                        var closeBtn = modalEl.querySelector('[data-bs-dismiss="modal"]');
                        if (closeBtn) closeBtn.click();
                    }
                }
                form.reset();
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to schedule activity'));
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

    window.logNote = function() {
        var form = document.getElementById('logNoteForm');
        if (!form) {
            alert('Form not found');
            return;
        }
        
        // Get note directly from textarea
        var noteTextarea = form.querySelector('textarea[name="note"]');
        var note = '';
        
        if (noteTextarea) {
            note = noteTextarea.value || '';
        }
        
        // Fallback to FormData
        if (!note) {
            var formData = new FormData(form);
            note = formData.get('note') || '';
        }

        note = note.trim();
        
        if (!note) {
            alert('Please enter a note');
            return;
        }
        
        console.log('Sending note:', note);

        var leadId = window.location.pathname.match(/\/(\d+)$/);
        if (!leadId) {
            alert('Invalid lead ID');
            return;
        }

        var btn = event.target;
        var originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> Logging...';

        jsonRpcCall('/my/lead/' + leadId[1] + '/log_note', {
            note: note,
            csrf_token: getCSRFToken()
        })
        .then(function(result) {
            if (result.success) {
                alert('Note logged successfully!');
                // Close modal using data-bs-dismiss or jQuery fallback
                var modalEl = document.getElementById('logNoteModal');
                if (modalEl) {
                    // Try Bootstrap 5
                    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                        var modal = bootstrap.Modal.getInstance(modalEl);
                        if (modal) modal.hide();
                    } else {
                        // Fallback: click the close button
                        var closeBtn = modalEl.querySelector('[data-bs-dismiss="modal"]');
                        if (closeBtn) closeBtn.click();
                    }
                }
                form.reset();
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to log note'));
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

})();
