/**
 * Medical Interview Handler for Medical Pre-Screening Tool
 * Manages chatbot-style medical Q&A interface
 */

class MedicalInterviewHandler {
    constructor() {
        console.log('[FRONTEND_DEBUG] MedicalInterviewHandler constructor called');
        this.patientData = null;
        
        // Check if APIClient is available
        if (typeof APIClient === 'undefined') {
            console.error('[FRONTEND_DEBUG] APIClient class not found');
            throw new Error('APIClient class not available');
        }
        
        this.apiClient = new APIClient();
        console.log('[FRONTEND_DEBUG] APIClient instance created:', this.apiClient);
        console.log('[FRONTEND_DEBUG] APIClient methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(this.apiClient)));
        
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInputArea = document.getElementById('chat-input-area');
        this.answerTextarea = document.getElementById('patient-answer');
        this.sendButton = document.getElementById('send-answer');
        this.dontKnowButton = document.getElementById('dont-know-btn');
        this.audioToggleBtn2 = document.getElementById('toggle-audio-2');
        this.assessingLoading = document.getElementById('assessing-loading');
        this.assessmentSection = document.getElementById('assessment-section');
        
        console.log('[FRONTEND_DEBUG] DOM elements found:', {
            chatMessages: !!this.chatMessages,
            chatInputArea: !!this.chatInputArea,
            answerTextarea: !!this.answerTextarea,
            sendButton: !!this.sendButton,
            dontKnowButton: !!this.dontKnowButton,
            assessingLoading: !!this.assessingLoading,
            assessmentSection: !!this.assessmentSection
        });
        
        this.currentQuestion = '';
        this.questionNumber = 0;
        this.unknownCount = 0;
        this.interviewActive = false;
        
        this.init();
    }

    async init() {
        try {
            // Load patient data from session using direct API call as fallback
            console.log('[FRONTEND_DEBUG] Loading patient data...');
            
            if (typeof this.apiClient.getPatientData === 'function') {
                console.log('[FRONTEND_DEBUG] Using APIClient.getPatientData method');
                this.patientData = await this.apiClient.getPatientData();
            } else {
                console.log('[FRONTEND_DEBUG] Using fallback method to get patient data');
                // Fallback: get session_id from URL and make direct API call
                const urlParams = new URLSearchParams(window.location.search);
                const sessionId = urlParams.get('session_id');
                
                if (!sessionId) {
                    throw new Error('No session ID found in URL');
                }
                
                const response = await fetch(`/api/session/${sessionId}`);
                if (!response.ok) {
                    throw new Error(`Failed to get session data: ${response.status}`);
                }
                
                const sessionData = await response.json();
                this.patientData = sessionData.patient_info;
            }
            
            console.log('[FRONTEND_DEBUG] Patient data loaded:', this.patientData);
            
            this.displayPatientInfo();
            this.setupEventListeners();
            this.startInterview();
            this.setWelcomeTime();
        } catch (error) {
            console.error('[FRONTEND_DEBUG] Failed to load patient data:', error);
            this.showError('Failed to load patient data. Please try again.');
        }
    }

    displayPatientInfo() {
        const patientInfo = document.getElementById('patient-info');
        if (this.patientData && patientInfo) {
            patientInfo.innerHTML = `
                <div><strong>${this.patientData.name}</strong></div>
                <div>${this.patientData.age}y, ${this.patientData.gender}</div>
            `;
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                ${message}
            </div>
        `;
        document.body.insertBefore(errorDiv, document.body.firstChild);
    }

    setWelcomeTime() {
        const welcomeTime = document.getElementById('welcome-time');
        if (welcomeTime) {
            welcomeTime.textContent = window.utils ? utils.formatTime() : new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        }
    }

    setupEventListeners() {
        console.log('[FRONTEND_DEBUG] Setting up event listeners');
        
        // Send answer button
        this.sendButton.addEventListener('click', () => this.submitAnswer());
        
        // Enter key to send
        this.answerTextarea.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.submitAnswer();
            }
        });

        // Auto-resize textarea
        this.answerTextarea.addEventListener('input', () => this.autoResizeTextarea());

        // Second audio toggle button (below textbox)
        if (this.audioToggleBtn2) {
            this.audioToggleBtn2.addEventListener('click', () => {
                // Use the same toggle function as the main audio button
                if (window.simpleTTS) {
                    window.simpleTTS.toggleTTS();
                    this.updateSecondAudioButton();
                }
            });
        }

        // Assessment generation button
        const generateBtn = document.getElementById('generate-assessment-btn');
        console.log('[FRONTEND_DEBUG] Generate assessment button found:', !!generateBtn);
        if (generateBtn) {
            generateBtn.addEventListener('click', () => {
                console.log('[FRONTEND_DEBUG] Generate assessment button clicked');
                this.generateAssessment();
            });
        }

        // Navigation buttons
        document.getElementById('back-to-form')?.addEventListener('click', () => utils.goToPatientForm());
        document.getElementById('restart-interview')?.addEventListener('click', () => this.restartInterview());

        // Assessment action buttons
        document.getElementById('accept-prescreening-btn')?.addEventListener('click', () => this.acceptPrescreening());
        document.getElementById('start-new-btn')?.addEventListener('click', () => this.startNewAssessment());
    }

    updateSecondAudioButton() {
        if (!this.audioToggleBtn2 || !window.simpleTTS) return;
        
        const icon = this.audioToggleBtn2.querySelector('i');
        
        if (window.simpleTTS.isEnabled) {
            this.audioToggleBtn2.textContent = '';
            this.audioToggleBtn2.innerHTML = '<i class="fas fa-volume-up"></i> Disable Audio Questions';
            this.audioToggleBtn2.classList.remove('disabled');
        } else {
            this.audioToggleBtn2.textContent = '';
            this.audioToggleBtn2.innerHTML = '<i class="fas fa-volume-mute"></i> Enable Audio Questions';
            this.audioToggleBtn2.classList.add('disabled');
        }
    }

    autoResizeTextarea() {
        this.answerTextarea.style.height = 'auto';
        this.answerTextarea.style.height = Math.min(this.answerTextarea.scrollHeight, 150) + 'px';
    }

    async startInterview() {
        if (!this.patientData) {
            this.showError('Patient data not found. Please complete registration first.');
            return;
        }

        // Get interview type from session storage
        const interviewType = sessionStorage.getItem('interviewType') || 'help';
        console.log('[FRONTEND_DEBUG] Interview type:', interviewType);

        try {
            utils.showLoading('Starting medical interview...');
            
            let response;
            
            // Route to appropriate service based on interview type
            if (interviewType === 'followup') {
                console.log('[FRONTEND_DEBUG] Starting follow-up interview');
                console.log('[FRONTEND_DEBUG] Patient ID for followup:', this.patientData.patient_id);
                console.log('[FRONTEND_DEBUG] Full patient data:', this.patientData);
                
                // Ensure patient_id exists, fallback to id if needed
                const patientId = this.patientData.patient_id || this.patientData.id;
                console.log('[FRONTEND_DEBUG] Final Patient ID for followup:', patientId);
                
                if (!patientId) {
                    throw new Error('Patient ID is missing from patient data');
                }
                
                response = await api.startFollowupInterview(patientId);
            } else {
                console.log('[FRONTEND_DEBUG] Starting regular medical interview');
                response = await api.startMedicalInterview(this.patientData.patient_id);
            }
            
            if (response.success && response.question) {
                this.displayQuestion(response.question);
                this.updateProgress(response.progress);
                this.enableInput();
                this.interviewActive = true;
                this.interviewType = interviewType; // Store for later use
            } else {
                throw new Error(response.message || 'Failed to start interview');
            }

        } catch (error) {
            console.error('Error starting interview:', error);
            this.showError(`Failed to start interview: ${error.message}`);
        } finally {
            utils.hideLoading();
        }
    }

    displayQuestion(question) {
        this.currentQuestion = question;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system question';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-text">${question}</div>
                <div class="message-time">${utils.formatTime()}</div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // TTS Integration: Convert AI question to speech
        if (window.simpleTTS) {
            window.simpleTTS.playQuestion(question);
        }
        
        // Auto-focus the text input after displaying question
        setTimeout(() => {
            if (this.answerTextarea) {
                this.answerTextarea.focus();
            }
        }, 100);
    }

    displayUserAnswer(answer) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="message-content">
                <div class="message-text">${answer}</div>
                <div class="message-time">${utils.formatTime()}</div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    async submitAnswer() {
        const answer = this.answerTextarea.value.trim();
        
        if (!answer) {
            this.answerTextarea.focus();
            return;
        }

        if (!this.interviewActive) {
            return;
        }

        try {
            this.disableInput();
            this.displayUserAnswer(answer);
            this.answerTextarea.value = '';
            
            utils.showLoading('Processing your answer...');
            
            let response;
            const interviewType = this.interviewType || sessionStorage.getItem('interviewType') || 'help';
            
            // Route to appropriate service based on interview type
            if (interviewType === 'followup') {
                console.log('[FRONTEND_DEBUG] Submitting follow-up answer');
                response = await api.submitFollowupAnswer(this.patientData.patient_id, answer);
            } else {
                console.log('[FRONTEND_DEBUG] Submitting regular medical answer');
                response = await api.submitAnswer(this.patientData.patient_id, answer);
            }
            
            if (response.success) {
                if (response.interview_complete) {
                    this.completeInterview();
                } else if (response.next_question) {
                    this.displayQuestion(response.next_question);
                    this.updateProgress(response.progress);
                    this.enableInput();
                } else {
                    throw new Error('No next question received');
                }
            } else {
                throw new Error(response.message || 'Failed to submit answer');
            }

        } catch (error) {
            console.error('Error submitting answer:', error);
            this.showError(`Failed to submit answer: ${error.message}`);
            this.enableInput();
        } finally {
            utils.hideLoading();
        }
    }

    submitDontKnow() {
        this.answerTextarea.value = "I don't know";
        this.submitAnswer();
    }

    updateProgress(progress) {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const unknownCountElement = document.getElementById('unknown-count');
        
        if (progressFill) {
            progressFill.style.width = `${progress.completion_percent}%`;
        }
        
        if (progressText) {
            progressText.textContent = `Question ${progress.current_question} of ${progress.max_questions}`;
        }
        
        if (unknownCountElement) {
            unknownCountElement.textContent = `Unknown responses: ${progress.unknown_count}/${progress.max_unknowns}`;
        }
        
        this.questionNumber = progress.current_question;
        this.unknownCount = progress.unknown_count;
    }

    enableInput() {
        if (this.answerTextarea) this.answerTextarea.disabled = false;
        if (this.sendButton) this.sendButton.disabled = false;
        if (this.dontKnowButton) this.dontKnowButton.disabled = false;
        if (this.answerTextarea) this.answerTextarea.focus();
        const restartBtn = document.getElementById('restart-interview');
        if (restartBtn) restartBtn.disabled = false;
    }

    disableInput() {
        if (this.answerTextarea) this.answerTextarea.disabled = true;
        if (this.sendButton) this.sendButton.disabled = true;
        if (this.dontKnowButton) this.dontKnowButton.disabled = true;
    }

    completeInterview() {
        this.interviewActive = false;
        this.disableInput();
        this.chatInputArea.classList.add('hidden');
        
        // Show assessing loading state
        if (this.assessingLoading) {
            this.assessingLoading.classList.remove('hidden');
        }
        
        // Update progress to 100%
        const progressFill = document.getElementById('progress-fill');
        if (progressFill) {
            progressFill.style.width = '100%';
        }
        
        // Auto-generate assessment after showing loading
        setTimeout(() => {
            this.generateAssessment();
        }, 1500); // Brief delay to show loading state
    }

    async generateAssessment() {
        try {
            console.log('🔄 Generating assessment...');
            this.showLoadingState('Generating your assessment...');
            
            // Check interview type for routing
            const interviewType = sessionStorage.getItem('interviewType');
            const patientData = JSON.parse(sessionStorage.getItem('patientData') || '{}');
            
            console.log(`📋 [ASSESSMENT] Interview type: ${interviewType}`);
            console.log(`📋 [ASSESSMENT] Patient data:`, patientData);
            console.log(`📋 [ASSESSMENT] Patient ID: ${patientData.patient_id}`);
            
            // Ensure patient_id exists, fallback to id if needed
            const patientId = patientData.patient_id || patientData.id;
            console.log(`📋 [ASSESSMENT] Final Patient ID: ${patientId}`);
            
            let response;
            
            if (interviewType === 'followup') {
                console.log('🔄 [FOLLOWUP] Generating follow-up assessment...');
                
                // Call follow-up assessment endpoint
                response = await api.makeRequest('/followup/generate-assessment', {
                    method: 'POST',
                    body: JSON.stringify({
                        session_id: api.sessionId,
                        patient_id: patientId
                    })
                });
                
                console.log('✅ [FOLLOWUP] Follow-up assessment generated');
            } else {
                console.log('🔄 [MEDICAL] Generating regular medical assessment...');
                response = await api.generateAssessment(patientId);
            }
            
            if (response.success) {
                this.displayAssessment(response);
                this.showAssessmentSection();
            } else {
                throw new Error(response.message || 'Assessment generation failed');
            }
            
        } catch (error) {
            console.error('❌ Assessment generation failed:', error);
            this.showError('Failed to generate assessment. Please try again.');
        } finally {
            this.hideLoadingState();
        }
    }

    displayAssessment(assessmentResponse) {
        console.log('[FRONTEND_DEBUG] Assessment response:', assessmentResponse);
        
        const { recommended_doctor, recommended_department } = assessmentResponse;
        
        // Get interview type and chosen doctor data from session
        const interviewType = sessionStorage.getItem('interviewType') || 'help';
        console.log('[FRONTEND_DEBUG] Interview type from session:', interviewType);
        
        // Get session data that contains doctor selection
        const sessionData = JSON.parse(sessionStorage.getItem('sessionData') || '{}');
        const patientData = JSON.parse(sessionStorage.getItem('patientData') || '{}');
        
        console.log('[FRONTEND_DEBUG] Session data:', sessionData);
        console.log('[FRONTEND_DEBUG] Patient data:', patientData);
        console.log('[FRONTEND_DEBUG] All sessionStorage keys:', Object.keys(sessionStorage));
        
        // Debug: Print all sessionStorage contents for follow-up
        if (interviewType === 'followup') {
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                console.log('[FRONTEND_DEBUG] SessionStorage[' + key + ']:', sessionStorage.getItem(key));
            }
        }
        
        // Extract chosen doctor information from session data
        let chosenDoctor = null;
        let chosenDepartment = null;
        
        // Get selectedDoctorChoice from sessionStorage (stored with camelCase key)
        const selectedDoctorChoice = JSON.parse(sessionStorage.getItem('selectedDoctorChoice') || '{}');
        
        console.log('[FRONTEND_DEBUG] Session data:', sessionData);
        console.log('[FRONTEND_DEBUG] Selected doctor choice from storage:', selectedDoctorChoice);
        
        if (selectedDoctorChoice && selectedDoctorChoice.doctor_name) {
            chosenDoctor = selectedDoctorChoice.doctor_name;
            chosenDepartment = selectedDoctorChoice.department;
        }
        
        console.log('[FRONTEND_DEBUG] Chosen doctor:', chosenDoctor);
        console.log('[FRONTEND_DEBUG] Recommended doctor:', recommended_doctor);
        
        // Hide all unwanted elements
        const elementsToHide = ['confidence-level', 'doctor-analysis', 'pre-consultation-diagnostics'];
        elementsToHide.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = 'none';
            }
        });
        
        // Hide doctor recommendations element too (we'll use recommended-action for our custom message)
        const doctorRecommendationsEl = document.getElementById('doctor-recommendations');
        if (doctorRecommendationsEl) {
            doctorRecommendationsEl.style.display = 'none';
        }
        
        // Generate custom message based on interview type
        let customMessage = '';
        
        if (interviewType === 'followup') {
            // For follow-up visits, get doctor name from consultation data
            const consultationData = sessionData.consultation_data || {};
            
            // Try multiple paths to get the doctor name
            let followupDoctorName = consultationData.doctor_name || 
                                   (selectedDoctorChoice && selectedDoctorChoice.doctor_name) ||
                                   recommended_doctor;
            
            const followupDepartment = consultationData.doctor_specialty || 
                                     (selectedDoctorChoice && selectedDoctorChoice.department) ||
                                     recommended_department || '';
            
            // If still no valid doctor name, check if assessment response has it
            if (!followupDoctorName || followupDoctorName === 'undefined') {
                // Last resort - check if assessment has doctor info 
                if (assessmentResponse && assessmentResponse.doctor_name) {
                    followupDoctorName = assessmentResponse.doctor_name;
                } else {
                    followupDoctorName = 'your previous doctor';
                }
            }
            
            console.log('[FRONTEND_DEBUG] Consultation data:', consultationData);
            console.log('[FRONTEND_DEBUG] Selected doctor choice:', selectedDoctorChoice);
            console.log('[FRONTEND_DEBUG] Follow-up doctor name:', followupDoctorName);
            console.log('[FRONTEND_DEBUG] Follow-up department:', followupDepartment);
            
            customMessage = `Your Pre-Screening information has been sent to Dr. ${followupDoctorName}.<br><br>Thank You.`;
        } else if (interviewType === 'help') {
            // Help me choose a doctor
            customMessage = `Your Pre-Screening information has been sent to Dr. ${recommended_doctor}.<br><br>Thank You.`;
        } else if (interviewType === 'new') {
            // Visit new doctor - always show chosen doctor
            console.log('[FRONTEND_DEBUG] New visit - Chosen doctor:', chosenDoctor);
            console.log('[FRONTEND_DEBUG] New visit - Recommended doctor:', recommended_doctor);
            
            if (chosenDoctor) {
                // Always use chosen doctor for new visits
                customMessage = `Your Pre-Screening information has been sent to Dr. ${chosenDoctor}.<br><br>Thank You.`;
            } else {
                // Fallback if no chosen doctor found
                customMessage = `Your Pre-Screening information has been submitted to your chosen doctor.<br><br>Thank You.`;
            }
        } else {
            // Fallback for unknown types
            customMessage = `Your Pre-Screening information has been submitted to your chosen doctor.<br><br>Thank You.`;
        }
        
        console.log('[FRONTEND_DEBUG] Generated message:', customMessage);
        
        // Display the custom message in recommended-action element
        const recommendedActionEl = document.getElementById('recommended-action');
        if (recommendedActionEl) {
            recommendedActionEl.innerHTML = customMessage;
        }
    }

    showLoadingState(message) {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            const loadingMessage = loadingOverlay.querySelector('#loading-message');
            if (loadingMessage) {
                loadingMessage.textContent = message;
            }
            loadingOverlay.style.display = 'flex';
        }
    }

    hideLoadingState() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
        
        // Remove any temporary loading messages
        const loadingMessage = document.getElementById('loading-message');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    showAssessmentSection() {
        // Hide assessing loading and show assessment section
        if (this.assessingLoading) {
            this.assessingLoading.classList.add('hidden');
        }
        
        if (this.assessmentSection) {
            this.assessmentSection.classList.remove('hidden');
        }
    }

    enableInput() {
        if (this.answerTextarea) this.answerTextarea.disabled = false;
        if (this.sendButton) this.sendButton.disabled = false;
        if (this.dontKnowButton) this.dontKnowButton.disabled = false;
    }

    formatAssessmentText(text) {
        if (!text) return '';
        
        // Handle non-string values (objects, arrays, etc.)
        if (typeof text !== 'string') {
            // If it's an object or array, stringify it
            if (typeof text === 'object') {
                text = JSON.stringify(text, null, 2);
            } else {
                text = String(text);
            }
        }
        
        return text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    restartInterview() {
        if (confirm('Are you sure you want to restart the interview? This will clear all current progress.')) {
            this.resetInterview();
            this.startInterview();
        }
    }

    resetInterview() {
        this.interviewActive = false;
        this.currentQuestion = '';
        this.questionNumber = 0;
        this.unknownCount = 0;
        
        // Clear chat messages except welcome
        const messages = this.chatMessages.querySelectorAll('.message:not(.system:first-child)');
        messages.forEach(msg => msg.remove());
        
        // Reset UI elements
        this.chatInputArea.classList.remove('hidden');
        if (this.assessingLoading) this.assessingLoading.classList.add('hidden');
        this.assessmentSection.classList.add('hidden');
        
        // Reset progress
        this.updateProgress({
            current_question: 0,
            max_questions: 6,
            unknown_count: 0,
            max_unknowns: 2,
            completion_percent: 0
        });
        
        this.disableInput();
    }

    startNewAssessment() {
        if (confirm('Start a new assessment? This will clear all current data and return to patient registration.')) {
            utils.clearSessionData();
            utils.goToPatientForm();
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message system error';
        errorDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div class="message-content">
                <div class="message-text" style="background: #e74c3c; color: white;">
                    <strong>Error:</strong> ${message}
                </div>
                <div class="message-time">${utils.formatTime()}</div>
            </div>
        `;
        
        this.chatMessages.appendChild(errorDiv);
        this.scrollToBottom();
    }

    async acceptPrescreening() {
        console.log('[FRONTEND_DEBUG] Accept pre-screening button clicked');
        
        try {
            const acceptButton = document.getElementById('accept-prescreening-btn');
            if (acceptButton) {
                acceptButton.disabled = true;
                acceptButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
            }
            
            utils.showLoading('Submitting pre-screening data...');
            
            // Get session ID from sessionStorage (using correct key)
            const sessionId = sessionStorage.getItem('sessionId') || 
                            sessionStorage.getItem('session_id') || 
                            this.patientData?.mobile || 
                            `session_${Date.now()}`;
            
            console.log('[FRONTEND_DEBUG] Using session ID for Accept API:', sessionId);
            
            const response = await fetch('/api/prescreening/accept', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    session_id: sessionId
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                console.log('[FRONTEND_DEBUG] Pre-screening accepted successfully:', result);
                
                // Show success message
                this.showSuccessMessage('Thank You for Visiting');
                
                // Remove accept button after successful submission
                if (acceptButton) {
                    acceptButton.remove();
                }
                
            } else {
                throw new Error(result.detail || result.message || 'Failed to submit pre-screening data');
            }
            
        } catch (error) {
            console.error('[FRONTEND_DEBUG] Error accepting pre-screening:', error);
            this.showError(`Failed to submit pre-screening data: ${error.message}`);
            
            // Re-enable button on error
            const acceptButton = document.getElementById('accept-prescreening-btn');
            if (acceptButton) {
                acceptButton.disabled = false;
                acceptButton.innerHTML = '<i class="fas fa-check-circle"></i> Accept & Submit Pre-Screening';
            }
        } finally {
            utils.hideLoading();
        }
    }

    showSuccessMessage(title, details = '') {
        const successHtml = `
            <div class="alert alert-success" style="margin: 20px 0; padding: 15px; border-radius: 8px; background: #d4edda; border: 1px solid #c3e6cb; color: #155724;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fas fa-check-circle" style="color: #28a745; font-size: 1.2rem;"></i>
                    <div>
                        <strong>${title}</strong>
                    </div>
                </div>
            </div>
        `;
        
        // Insert success message after assessment content
        const assessmentContent = document.querySelector('.assessment-content');
        if (assessmentContent) {
            assessmentContent.insertAdjacentHTML('afterend', successHtml);
        }
    }

    showJSONModal() {
        const jsonOutput = document.getElementById('json-output');
        const modal = document.getElementById('json-modal');
        
        if (this.assessmentData && jsonOutput) {
            jsonOutput.textContent = JSON.stringify(this.assessmentData, null, 2);
        }
        
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    hideJSONModal() {
        const modal = document.getElementById('json-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
}

// Initialize the interview handler when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('[FRONTEND_DEBUG] DOM loaded, initializing MedicalInterviewHandler');
    try {
        const handler = new MedicalInterviewHandler();
        console.log('[FRONTEND_DEBUG] MedicalInterviewHandler initialized successfully');
    } catch (error) {
        console.error('[FRONTEND_DEBUG] Failed to initialize MedicalInterviewHandler:', error);
    }
});
