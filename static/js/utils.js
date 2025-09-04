/**
 * Utility functions for Medical Pre-Screening Tool
 * Handles common functionality across pages
 */

const utils = {
    // Get current timestamp formatted
    formatTime() {
        return new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Get session ID from URL or sessionStorage
    getSessionId() {
        const urlParams = new URLSearchParams(window.location.search);
        const urlSessionId = urlParams.get('session_id');
        if (urlSessionId) {
            return urlSessionId;
        }
        return sessionStorage.getItem('sessionId') || null;
    },

    // Get patient data from sessionStorage (legacy support)
    getPatientData() {
        const patientDataStr = sessionStorage.getItem('patientData');
        if (patientDataStr) {
            try {
                return JSON.parse(patientDataStr);
            } catch (e) {
                console.error('Failed to parse patient data:', e);
                return null;
            }
        }
        return null;
    },

    // Store patient data in sessionStorage (legacy support)
    setPatientData(patientData) {
        sessionStorage.setItem('patientData', JSON.stringify(patientData));
    },

    // Navigate to interview page with session_id
    goToInterviewPage(sessionId = null) {
        const sid = sessionId || this.getSessionId();
        if (sid) {
            window.location.href = `/static/interview.html?session_id=${sid}`;
        } else {
            console.error('No session ID available for navigation');
            alert('Session not found. Please try again.');
        }
    },

    // Navigate to patient details page with session_id
    goToPatientDetailsPage(sessionId = null) {
        const sid = sessionId || this.getSessionId();
        if (sid) {
            window.location.href = `/static/patient-details.html?session_id=${sid}`;
        } else {
            console.error('No session ID available for navigation');
            alert('Session not found. Please try again.');
        }
    },

    // Show loading spinner
    showLoading(message = 'Loading...') {
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'global-loading';
        loadingDiv.className = 'global-loading';
        loadingDiv.innerHTML = `
            <div class="loading-overlay">
                <div class="loading-content">
                    <div class="spinner"></div>
                    <p>${message}</p>
                </div>
            </div>
        `;
        document.body.appendChild(loadingDiv);
    },

    // Hide loading spinner
    hideLoading() {
        const loadingDiv = document.getElementById('global-loading');
        if (loadingDiv) {
            loadingDiv.remove();
        }
    },

    // Show error message
    showError(message, duration = 5000) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'global-error';
        errorDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                ${message}
                <button class="close-btn" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        document.body.insertBefore(errorDiv, document.body.firstChild);
        
        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
            }, duration);
        }
    },

    // Show success message
    showSuccess(message, duration = 3000) {
        const successDiv = document.createElement('div');
        successDiv.className = 'global-success';
        successDiv.innerHTML = `
            <div class="alert alert-success">
                <i class="fas fa-check-circle"></i>
                ${message}
                <button class="close-btn" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        document.body.insertBefore(successDiv, document.body.firstChild);
        
        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (successDiv.parentNode) {
                    successDiv.remove();
                }
            }, duration);
        }
    }
};

// Make utils available globally
window.utils = utils;
