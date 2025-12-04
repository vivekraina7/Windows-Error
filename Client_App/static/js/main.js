/* static/js/main.js - Main JavaScript Functions */

// Global variables
let scanInProgress = false;

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
    
    console.log('Main JavaScript loaded successfully');
});

// Utility Functions
function showAlert(type, message, autoClose = true) {
    const alertType = type === 'error' ? 'danger' : type;
    const iconMap = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    
    const icon = iconMap[type] || 'info-circle';
    
    const alertHtml = `
        <div class="alert alert-${alertType} alert-dismissible fade show fade-in" role="alert">
            <i class="fas fa-${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Remove existing alerts of same type
    $(`.alert-${alertType}`).remove();
    
    // Add new alert
    $('main .container').prepend(alertHtml);
    
    // Auto close after 5 seconds if requested
    if (autoClose) {
        setTimeout(function() {
            $(`.alert-${alertType}`).alert('close');
        }, 5000);
    }
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Progress Animation
function animateProgressBar(elementId, targetPercent, duration = 1000) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    let current = 0;
    const increment = targetPercent / (duration / 16); // 60fps
    
    const timer = setInterval(function() {
        current += increment;
        if (current >= targetPercent) {
            current = targetPercent;
            clearInterval(timer);
        }
        
        element.style.width = current + '%';
        element.setAttribute('aria-valuenow', current);
    }, 16);
}

// Loading Modal Functions
function showLoadingModal(title = 'Processing...', showProgress = true) {
    $('#loadingText').text(title);
    if (showProgress) {
        $('.progress').show();
        $('#scanProgress').css('width', '0%');
    } else {
        $('.progress').hide();
    }
    $('#loadingModal').modal('show');
}

function hideLoadingModal() {
    $('#loadingModal').modal('hide');
}

function updateLoadingProgress(percent, text) {
    $('#scanProgress').css('width', percent + '%');
    if (text) {
        $('#loadingText').text(text);
    }
}

// Error Handling
function handleAjaxError(xhr, status, error) {
    console.error('Ajax error:', error);
    
    let message = 'An unexpected error occurred.';
    
    if (xhr.status === 404) {
        message = 'The requested resource was not found.';
    } else if (xhr.status === 500) {
        message = 'Server error occurred. Please try again later.';
    } else if (xhr.status === 0) {
        message = 'Network connection error. Please check your connection.';
    }
    
    showAlert('error', message);
    hideLoadingModal();
}

// Form Validation
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
        
        // Special validation for email
        if (field.type === 'email' && field.value.trim()) {
            if (!validateEmail(field.value.trim())) {
                field.classList.add('is-invalid');
                isValid = false;
            }
        }
    });
    
    return isValid;
}

// Local Storage Helpers
function saveToStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {
        console.error('Error saving to storage:', e);
    }
}

function getFromStorage(key, defaultValue = null) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : defaultValue;
    } catch (e) {
        console.error('Error reading from storage:', e);
        return defaultValue;
    }
}

// Scan Progress Simulation (for better UX)
function simulateScanProgress() {
    let progress = 0;
    const phases = [
        { percent: 20, text: 'Scanning directories...' },
        { percent: 40, text: 'Validating dump files...' },
        { percent: 60, text: 'Analyzing dump files...' },
        { percent: 80, text: 'Searching knowledge base...' },
        { percent: 95, text: 'Preparing results...' }
    ];
    
    let currentPhase = 0;
    
    const interval = setInterval(function() {
        if (currentPhase < phases.length) {
            const phase = phases[currentPhase];
            updateLoadingProgress(phase.percent, phase.text);
            currentPhase++;
        } else {
            clearInterval(interval);
        }
    }, 1000);
    
    return interval;
}

// Copy to Clipboard Function
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showAlert('success', 'Copied to clipboard!', true);
        }).catch(function(err) {
            console.error('Failed to copy: ', err);
            fallbackCopyTextToClipboard(text);
        });
    } else {
        fallbackCopyTextToClipboard(text);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showAlert('success', 'Copied to clipboard!', true);
        } else {
            showAlert('error', 'Failed to copy to clipboard', true);
        }
    } catch (err) {
        console.error('Fallback copy failed: ', err);
        showAlert('error', 'Copy to clipboard not supported', true);
    }
    
    document.body.removeChild(textArea);
}

// Export functions for use in other scripts
window.AppUtils = {
    showAlert,
    formatDateTime,
    formatFileSize,
    animateProgressBar,
    showLoadingModal,
    hideLoadingModal,
    updateLoadingProgress,
    handleAjaxError,
    validateEmail,
    validateForm,
    saveToStorage,
    getFromStorage,
    simulateScanProgress,
    copyToClipboard
};
