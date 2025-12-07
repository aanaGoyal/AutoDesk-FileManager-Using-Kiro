/**
 * Main JavaScript file for File Management System
 * Provides common utilities and form validation
 */

// Global utility functions
const Utils = {
    /**
     * Show a status message
     */
    showMessage: function(elementId, message, type) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = message;
            element.className = `status-message active ${type}`;
            element.style.display = 'block';
        }
    },

    /**
     * Hide a status message
     */
    hideMessage: function(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'none';
        }
    },

    /**
     * Show loading spinner
     */
    showSpinner: function(spinnerId = 'spinner') {
        const spinner = document.getElementById(spinnerId);
        if (spinner) {
            spinner.classList.add('active');
        }
    },

    /**
     * Hide loading spinner
     */
    hideSpinner: function(spinnerId = 'spinner') {
        const spinner = document.getElementById(spinnerId);
        if (spinner) {
            spinner.classList.remove('active');
        }
    },

    /**
     * Validate directory path
     */
    validatePath: function(path) {
        if (!path || path.trim().length === 0) {
            return { valid: false, message: 'Path cannot be empty' };
        }
        
        // Basic path validation (works for both Windows and Unix)
        const windowsPath = /^[a-zA-Z]:\\|^\\\\/;
        const unixPath = /^\//;
        
        if (!windowsPath.test(path) && !unixPath.test(path) && !path.startsWith('.')) {
            return { valid: false, message: 'Invalid path format' };
        }
        
        return { valid: true };
    },

    /**
     * Format file size
     */
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 B';
        
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const k = 1024;
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + units[i];
    },

    /**
     * Confirm destructive action
     */
    confirmAction: function(message) {
        return confirm(message);
    },

    /**
     * Disable button
     */
    disableButton: function(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = true;
            button.style.opacity = '0.6';
            button.style.cursor = 'not-allowed';
        }
    },

    /**
     * Enable button
     */
    enableButton: function(buttonId) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = false;
            button.style.opacity = '1';
            button.style.cursor = 'pointer';
        }
    },

    /**
     * Update progress bar
     */
    updateProgress: function(progressId, percentage) {
        const progressFill = document.getElementById(progressId);
        if (progressFill) {
            progressFill.style.width = percentage + '%';
            progressFill.textContent = percentage + '%';
        }
    },

    /**
     * Show element
     */
    show: function(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'block';
        }
    },

    /**
     * Hide element
     */
    hide: function(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = 'none';
        }
    },

    /**
     * Make AJAX request
     */
    ajax: async function(url, method, data) {
        try {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            const response = await fetch(url, options);
            const result = await response.json();
            
            return { success: true, data: result, status: response.status };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
};

// Form validation
document.addEventListener('DOMContentLoaded', function() {
    // Add validation to all forms
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Prevent default form submission
        form.addEventListener('submit', function(e) {
            e.preventDefault();
        });
        
        // Add input validation
        const inputs = form.querySelectorAll('input[type="text"], textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.hasAttribute('required') && !this.value.trim()) {
                    this.style.borderColor = '#e74c3c';
                } else {
                    this.style.borderColor = '#ddd';
                }
            });
        });
    });
    
    // Add confirmation to destructive buttons
    const dangerButtons = document.querySelectorAll('.btn-danger');
    dangerButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!this.hasAttribute('data-no-confirm')) {
                const message = this.getAttribute('data-confirm-message') || 
                               'Are you sure you want to perform this action?';
                if (!confirm(message)) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            }
        });
    });
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter to submit forms
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const activeElement = document.activeElement;
        if (activeElement.tagName === 'TEXTAREA' || activeElement.tagName === 'INPUT') {
            const form = activeElement.closest('form');
            if (form) {
                const submitButton = form.querySelector('button[type="submit"], button.btn:not(.btn-secondary):not(.btn-danger)');
                if (submitButton) {
                    submitButton.click();
                }
            }
        }
    }
    
    // Escape to close modals or cancel operations
    if (e.key === 'Escape') {
        // Hide any visible status messages
        const statusMessages = document.querySelectorAll('.status-message.active');
        statusMessages.forEach(msg => {
            msg.classList.remove('active');
            msg.style.display = 'none';
        });
    }
});

// Handle network errors globally
window.addEventListener('online', function() {
    Utils.showMessage('statusMessage', 'Connection restored', 'success');
    setTimeout(() => Utils.hideMessage('statusMessage'), 3000);
});

window.addEventListener('offline', function() {
    Utils.showMessage('statusMessage', 'No internet connection', 'error');
});

// Export Utils for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Utils;
}
