/**
 * API Communication Layer for Medical Pre-Screening Tool
 * Handles all backend API calls and responses
 */

class APIClient {
    constructor() {
        this.baseURL = '';  // Use relative URLs since FastAPI serves static files
        this.sessionId = this.getSessionId();
    }

    // Session Management
    getSessionId() {
        return sessionStorage.getItem('sessionId') || null;
    }

    setSessionId(sessionId) {
        this.sessionId = sessionId;
        sessionStorage.setItem('sessionId', sessionId);
    }

    // Generic API call method
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseURL}/api${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error(`API Error for ${endpoint}:`, error);
            throw error;
        }
    }

    // Patient API calls
    async registerPatient(patientData) {
        const response = await this.makeRequest('/patients/register', {
            method: 'POST',
            body: JSON.stringify(patientData)
        });

        if (response.success && response.session_id) {
            this.setSessionId(response.session_id);
        }

        return response;
    }

    async getPatient(patientId) {
        return await this.makeRequest(`/patients/${patientId}?session_id=${this.sessionId}`);
    }

    // Department API calls
    async getDepartments() {
        return await this.makeRequest('/departments');
    }

    async getDoctorsByDepartment(department) {
        return await this.makeRequest(`/departments/${encodeURIComponent(department)}/doctors`);
    }

    async getAllDepartmentsWithDoctors() {
        return await this.makeRequest('/departments/all');
    }

    // Medical Interview API calls
    async startMedicalInterview(patientId) {
        return await this.makeRequest('/medical/start-interview', {
            method: 'POST',
            body: JSON.stringify({
                session_id: this.sessionId,
                patient_id: String(patientId)  // Ensure patient_id is always a string
            })
        });
    }

    async submitAnswer(patientId, answer) {
        return await this.makeRequest('/medical/submit-answer', {
            method: 'POST',
            body: JSON.stringify({
                session_id: this.sessionId,
                patient_id: String(patientId),  // Ensure patient_id is always a string
                answer: answer
            })
        });
    }

    async getInterviewStatus() {
        return await this.makeRequest(`/medical/interview/${this.sessionId}`);
    }

    // Assessment API calls
    async generateAssessment(patientId) {
        return await this.makeRequest('/assessment/generate', {
            method: 'POST',
            body: JSON.stringify({
                session_id: this.sessionId,
                patient_id: String(patientId)  // Ensure patient_id is always a string
            })
        });
    }

    async getAssessment() {
        return await this.makeRequest(`/assessment/${this.sessionId}`);
    }

    // Follow-up Interview API calls
    async startFollowupInterview(patientId) {
        return await this.makeRequest('/followup/start-interview', {
            method: 'POST',
            body: JSON.stringify({
                session_id: this.sessionId,
                patient_id: String(patientId)  // Ensure patient_id is always a string
            })
        });
    }

    async submitFollowupAnswer(patientId, answer) {
        return await this.makeRequest('/followup/submit-answer', {
            method: 'POST',
            body: JSON.stringify({
                session_id: this.sessionId,
                patient_id: String(patientId),  // Ensure patient_id is always a string
                answer: answer
            })
        });
    }

    async getFollowupInterviewStatus() {
        return await this.makeRequest(`/followup/interview/${this.sessionId}`);
    }
}

// Utility functions
const utils = {
    // Form validation helpers
    validateName(name) {
        const trimmedName = name.trim();
        if (trimmedName.length < 2) {
            return { valid: false, message: 'Name must be at least 2 characters long' };
        }
        if (!/^[a-zA-Z\s]+$/.test(trimmedName)) {
            return { valid: false, message: 'Name can only contain letters and spaces' };
        }
        return { valid: true, value: trimmedName };
    },

    validateMobile(mobile) {
        const cleanedMobile = mobile.replace(/\D/g, '');
        if (cleanedMobile.length !== 10) {
            return { valid: false, message: 'Mobile number must be exactly 10 digits' };
        }
        if (!/^[6-9]/.test(cleanedMobile)) {
            return { valid: false, message: 'Mobile number must start with 6, 7, 8, or 9' };
        }
        return { valid: true, value: cleanedMobile };
    },

    validateAge(age) {
        const ageNum = parseInt(age);
        if (isNaN(ageNum) || ageNum < 1 || ageNum > 120) {
            return { valid: false, message: 'Age must be between 1 and 120' };
        }
        return { valid: true, value: ageNum };
    },

    validateGender(gender) {
        const validGenders = ['Male', 'Female', 'Other'];
        if (!validGenders.includes(gender)) {
            return { valid: false, message: 'Please select a valid gender' };
        }
        return { valid: true, value: gender };
    },

    // UI helpers
    showError(elementId, message) {
        const errorElement = document.getElementById(elementId);
        const inputElement = document.getElementById(elementId.replace('-error', ''));
        
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.add('show');
        }
        
        if (inputElement) {
            inputElement.parentElement.classList.add('error');
        }
    },

    hideError(elementId) {
        const errorElement = document.getElementById(elementId);
        const inputElement = document.getElementById(elementId.replace('-error', ''));
        
        if (errorElement) {
            errorElement.textContent = '';
            errorElement.classList.remove('show');
        }
        
        if (inputElement) {
            inputElement.parentElement.classList.remove('error');
        }
    },

    showLoading(message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        const loadingText = document.getElementById('loading-text');
        
        if (overlay) {
            overlay.classList.remove('hidden');
        }
        
        if (loadingText) {
            loadingText.textContent = message;
        }
    },

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    },

    // Date/time formatting
    formatTime(date = new Date()) {
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
    },

    formatDate(date = new Date()) {
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    // Storage helpers
    savePatientData(patientData) {
        sessionStorage.setItem('patientData', JSON.stringify(patientData));
    },

    getPatientData() {
        const data = sessionStorage.getItem('patientData');
        return data ? JSON.parse(data) : null;
    },

    clearSessionData() {
        sessionStorage.removeItem('sessionId');
        sessionStorage.removeItem('patientData');
        sessionStorage.removeItem('interviewData');
        sessionStorage.removeItem('interviewType');
        sessionStorage.removeItem('selectedDoctorChoice');
        sessionStorage.removeItem('consultationData');
    },

    // Navigation helpers
    goToInterviewPage() {
        window.location.href = '/interview';
    },

    goToPatientForm() {
        window.location.href = '/';
    }
};

// Create global API instance
const api = new APIClient();
