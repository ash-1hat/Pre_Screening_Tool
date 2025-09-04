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
        // First try to get from URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const urlSessionId = urlParams.get('session_id');
        if (urlSessionId) {
            return urlSessionId;
        }
        // Fallback to sessionStorage for backward compatibility
        return sessionStorage.getItem('sessionId') || null;
    }

    setSessionId(sessionId) {
        this.sessionId = sessionId;
        sessionStorage.setItem('sessionId', sessionId);
    }

    // Get session data from backend
    async getSessionData(sessionId) {
        return await this.makeRequest(`/session/${sessionId}`);
    }

    // Get patient data from session
    async getPatientData() {
        const sessionId = this.getSessionId();
        if (!sessionId) {
            throw new Error('No session ID found');
        }
        
        try {
            const sessionData = await this.getSessionData(sessionId);
            return sessionData.patient_info;
        } catch (error) {
            console.error('Failed to get patient data from session:', error);
            throw error;
        }
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

// Create global API instance
const api = new APIClient();
