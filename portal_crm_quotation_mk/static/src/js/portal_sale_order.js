// Sale Order Portal Functions - Product Selection and Email Wizard

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
        var match = document.cookie.match(/csrf_token=([^;]+)/);
        if (match) {
            return match[1];
        }
        if (typeof odoo !== 'undefined' && odoo.csrf_token) {
            return odoo.csrf_token;
        }
        return '';
    }

    // Update price when product is selected
    window.updateProductPrice = function() {
        var productSelect = document.getElementById('productSelect');
        var priceUnit = document.getElementById('priceUnit');
        if (productSelect && priceUnit) {
            var selectedOption = productSelect.options[productSelect.selectedIndex];
            var price = selectedOption.getAttribute('data-price') || '';
            priceUnit.value = price;
        }
    };

    // Add product line to sale order
    window.addProductLine = function() {
        var form = document.getElementById('addProductForm');
        if (!form || !form.checkValidity()) {
            if (form) form.reportValidity();
            return;
        }

        var formData = new FormData(form);
        var productId = formData.get('product_id');
        var quantity = parseFloat(formData.get('quantity')) || 1;
        var priceUnit = parseFloat(formData.get('price_unit')) || 0;

        if (!productId) {
            alert('Please select a product');
            return;
        }

        // Get order ID from URL
        var orderId = window.location.pathname.match(/\/my\/orders\/(\d+)/);
        if (!orderId) {
            alert('Invalid order ID');
            return;
        }

        var btn = event.target;
        var originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i>';

        jsonRpcCall('/my/quotation/' + orderId[1] + '/add_line', {
            product_id: parseInt(productId),
            quantity: quantity,
            price_unit: priceUnit || false,
            csrf_token: getCSRFToken()
        })
        .then(function(result) {
            if (result.success) {
                alert('Product added successfully!');
                form.reset();
                document.getElementById('priceUnit').value = '';
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to add product'));
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

    // Open send email wizard
    window.openSendEmailWizard = function() {
        var modalEl = document.getElementById('sendEmailWizardModal');
        if (modalEl) {
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                var modal = new bootstrap.Modal(modalEl);
                modal.show();
            } else {
                // Fallback: show modal manually
                modalEl.style.display = 'block';
                modalEl.classList.add('show');
            }
        }
    };

    // Send quotation email
    window.sendQuotationEmail = function() {
        var form = document.getElementById('sendEmailForm');
        if (!form || !form.checkValidity()) {
            if (form) form.reportValidity();
            return;
        }

        var formData = new FormData(form);
        var templateId = formData.get('template_id') || '';
        var recipients = formData.get('recipients') || '';
        var subject = formData.get('subject') || '';
        var body = formData.get('body') || '';

        if (!recipients) {
            alert('Please enter at least one recipient email');
            return;
        }

        // Get order ID from URL
        var orderId = window.location.pathname.match(/\/my\/orders\/(\d+)/);
        if (!orderId) {
            alert('Invalid order ID');
            return;
        }

        var btn = event.target;
        var originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Sending...';

        jsonRpcCall('/my/quotation/' + orderId[1] + '/send_email', {
            template_id: templateId ? parseInt(templateId) : false,
            recipients: recipients,
            subject: subject,
            body: body,
            csrf_token: getCSRFToken()
        })
        .then(function(result) {
            if (result.success) {
                alert(result.message || 'Quotation sent successfully!');
                var modalEl = document.getElementById('sendEmailWizardModal');
                if (modalEl) {
                    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                        var modal = bootstrap.Modal.getInstance(modalEl);
                        if (modal) modal.hide();
                    } else {
                        modalEl.style.display = 'none';
                        modalEl.classList.remove('show');
                    }
                }
                form.reset();
            } else {
                alert('Error: ' + (result.error || 'Failed to send email'));
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

    // Initialize: Add event listener for product selection
    document.addEventListener('DOMContentLoaded', function() {
        var productSelect = document.getElementById('productSelect');
        if (productSelect) {
            productSelect.addEventListener('change', updateProductPrice);
        }
    });

})();
