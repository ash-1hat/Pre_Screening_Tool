/**
 * Voice Recorder for Medical Interview
 * Handles voice recording, waveform visualization, and STT integration
 */

class VoiceRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.dataArray = null;
        this.animationId = null;
        this.voiceAvailable = false;
        
        // DOM elements
        this.voiceButton = null;
        this.recordingIndicator = null;
        this.waveformCanvas = null;
        this.waveformContext = null;
        
        this.init();
    }
    
    async init() {
        console.log('[VOICE] Initializing voice recorder...');
        
        // Setup DOM elements first
        this.setupDOM();
        
        // Setup event listeners after DOM creation
        this.setupEventListeners();
        
        // Check voice availability
        await this.checkVoiceAvailability();
        
        // Update button visibility after availability check
        this.updateVoiceButtonVisibility();
        
        console.log('[VOICE] Voice recorder initialized, available:', this.voiceAvailable);
    }
    
    async checkVoiceAvailability() {
        try {
            const response = await fetch('/api/voice-health');
            const result = await response.json();
            this.voiceAvailable = result.success && result.voice_available;
            console.log('[VOICE] Voice availability check:', this.voiceAvailable, result);
        } catch (error) {
            console.error('[VOICE] Voice availability check failed:', error);
            this.voiceAvailable = false;
        }
    }
    
    setupDOM() {
        // Always create DOM elements, then show/hide based on availability
        this.createVoiceButton();
        this.createRecordingIndicator();
        this.createWaveformCanvas();
        
        // Show/hide voice button based on availability
        this.updateVoiceButtonVisibility();
    }
    
    updateVoiceButtonVisibility() {
        if (this.voiceButton) {
            if (this.voiceAvailable) {
                this.voiceButton.style.display = 'flex';
                console.log('[VOICE] Voice button shown - Voice_Modal is available');
            } else {
                this.voiceButton.style.display = 'none';
                console.log('[VOICE] Voice button hidden - Voice_Modal unavailable');
            }
        }
    }
    
    createVoiceButton() {
        const inputContainer = document.querySelector('.input-container');
        if (!inputContainer) return;
        
        // Create voice button
        this.voiceButton = document.createElement('button');
        this.voiceButton.id = 'voice-input-btn';
        this.voiceButton.className = 'voice-button';
        this.voiceButton.type = 'button';
        this.voiceButton.title = 'Voice Input';
        this.voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        
        // Insert before send button
        const sendButton = document.getElementById('send-answer');
        inputContainer.insertBefore(this.voiceButton, sendButton);
        
        // Add CSS styles
        this.addVoiceButtonStyles();
    }
    
    createRecordingIndicator() {
        const chatContainer = document.querySelector('.chat-container');
        if (!chatContainer) return;
        
        // Create recording indicator overlay
        const recordingOverlay = document.createElement('div');
        recordingOverlay.id = 'recording-overlay';
        recordingOverlay.className = 'recording-overlay hidden';
        recordingOverlay.innerHTML = `
            <div class="recording-content">
                <div class="recording-dot"></div>
                <div class="recording-text">Recording...</div>
                <canvas id="waveform-canvas" width="300" height="100"></canvas>
                <button id="stop-recording-btn" class="stop-recording-btn">
                    <i class="fas fa-stop"></i> Stop Recording
                </button>
            </div>
        `;
        
        chatContainer.appendChild(recordingOverlay);
        this.recordingIndicator = recordingOverlay;
        
        // Add recording indicator styles
        this.addRecordingStyles();
    }
    
    createWaveformCanvas() {
        this.waveformCanvas = document.getElementById('waveform-canvas');
        if (this.waveformCanvas) {
            this.waveformContext = this.waveformCanvas.getContext('2d');
        }
    }
    
    setupEventListeners() {
        if (this.voiceButton) {
            console.log('[VOICE] Setting up click listener for voice button');
            this.voiceButton.addEventListener('click', (e) => {
                console.log('[VOICE] Voice button clicked!');
                e.preventDefault();
                e.stopPropagation();
                this.toggleRecording();
            });
        } else {
            console.error('[VOICE] Voice button not found when setting up event listeners');
        }
        
        // Stop recording button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'stop-recording-btn' || e.target.closest('#stop-recording-btn')) {
                console.log('[VOICE] Stop recording button clicked');
                this.stopRecording();
            }
        });
    }
    
    async toggleRecording() {
        console.log('[VOICE] Toggle recording called, current state:', this.isRecording);
        console.log('[VOICE] Voice available:', this.voiceAvailable);
        
        if (!this.voiceAvailable) {
            console.error('[VOICE] Voice not available, cannot record');
            this.showError('Voice service is not available');
            return;
        }
        
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }
    
    async startRecording() {
        try {
            console.log('[VOICE] Starting recording...');
            
            // Request microphone permission
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });
            
            // Setup audio context for waveform
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.microphone = this.audioContext.createMediaStreamSource(stream);
            this.microphone.connect(this.analyser);
            
            this.analyser.fftSize = 256;
            const bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(bufferLength);
            
            // Setup media recorder
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            
            this.audioChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.processRecording();
            };
            
            // Start recording
            this.mediaRecorder.start();
            this.isRecording = true;
            
            // Update UI
            this.showRecordingIndicator();
            this.startWaveformAnimation();
            
            console.log('[VOICE] Recording started');
            
        } catch (error) {
            console.error('[VOICE] Failed to start recording:', error);
            this.showError('Voice Input Error, Please Type Manually');
        }
    }
    
    async stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;
        
        console.log('[VOICE] Stopping recording...');
        
        this.isRecording = false;
        this.mediaRecorder.stop();
        
        // Stop waveform animation
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        
        // Stop microphone stream
        if (this.microphone && this.microphone.mediaStream) {
            this.microphone.mediaStream.getTracks().forEach(track => track.stop());
        }
        
        // Close audio context
        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
        }
        
        // Hide recording indicator
        this.hideRecordingIndicator();
        
        console.log('[VOICE] Recording stopped');
    }
    
    async processRecording() {
        try {
            console.log('[VOICE] Processing recording...');
            
            // Show processing state
            this.showProcessing();
            
            // Create audio blob
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            
            // Convert to base64
            const audioBase64 = await this.blobToBase64(audioBlob);
            
            // Get patient ID
            const patientData = utils.getPatientData();
            if (!patientData || !patientData.patient_id) {
                throw new Error('Patient data not found');
            }
            
            // Send to voice API - match Voice_Modal format
            const formData = new FormData();
            formData.append('patient_id', patientData.patient_id);
            formData.append('audio', audioBlob); // Send as binary blob like Voice_Modal
            formData.append('stt_provider', 'sarvam'); // Required by Voice_Modal
            const response = await fetch('/api/voice-input', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('[VOICE] Voice processing successful');
                
                // Display the transcribed answer in chat
                if (window.medicalInterviewHandler) {
                    window.medicalInterviewHandler.displayUserAnswer(result.english_transcript || 'Voice input processed');
                    
                    // Display next question if available
                    if (result.next_question) {
                        window.medicalInterviewHandler.displayQuestion(result.next_question);
                        window.medicalInterviewHandler.updateProgress(result.progress);
                    }
                    
                    // Check if interview is complete
                    if (result.interview_complete) {
                        window.medicalInterviewHandler.completeInterview();
                    }
                }
                
            } else {
                console.error('[VOICE] Voice processing failed:', result.message);
                this.showError(result.message || 'Voice Input Error, Please Type Manually');
            }
            
        } catch (error) {
            console.error('[VOICE] Recording processing error:', error);
            this.showError('Voice Input Error, Please Type Manually');
        } finally {
            this.hideProcessing();
        }
    }
    
    blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }
    
    showRecordingIndicator() {
        if (this.recordingIndicator) {
            this.recordingIndicator.classList.remove('hidden');
        }
        
        if (this.voiceButton) {
            this.voiceButton.classList.add('recording');
            this.voiceButton.innerHTML = '<i class="fas fa-stop"></i>';
        }
    }
    
    hideRecordingIndicator() {
        if (this.recordingIndicator) {
            this.recordingIndicator.classList.add('hidden');
        }
        
        if (this.voiceButton) {
            this.voiceButton.classList.remove('recording');
            this.voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        }
    }
    
    startWaveformAnimation() {
        if (!this.waveformCanvas || !this.waveformContext || !this.analyser) return;
        
        const draw = () => {
            if (!this.isRecording) return;
            
            this.animationId = requestAnimationFrame(draw);
            
            this.analyser.getByteFrequencyData(this.dataArray);
            
            const canvas = this.waveformCanvas;
            const ctx = this.waveformContext;
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            const barWidth = (canvas.width / this.dataArray.length) * 2.5;
            let barHeight;
            let x = 0;
            
            for (let i = 0; i < this.dataArray.length; i++) {
                barHeight = (this.dataArray[i] / 255) * canvas.height * 0.8;
                
                ctx.fillStyle = `rgb(${barHeight + 100}, 50, 50)`;
                ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                
                x += barWidth + 1;
            }
        };
        
        draw();
    }
    
    showProcessing() {
        if (window.utils && window.utils.showLoading) {
            window.utils.showLoading('Processing voice input...');
        }
    }
    
    hideProcessing() {
        if (window.utils && window.utils.hideLoading) {
            window.utils.hideLoading();
        }
    }
    
    showError(message) {
        if (window.medicalInterviewHandler) {
            window.medicalInterviewHandler.showError(message);
        } else {
            console.error('[VOICE] Error:', message);
            alert(message);
        }
    }
    
    addVoiceButtonStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .voice-button {
                background: #007bff;
                border: none;
                border-radius: 50%;
                width: 45px;
                height: 45px;
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-left: 10px;
                transition: all 0.3s ease;
                font-size: 18px;
            }
            
            .voice-button:hover {
                background: #0056b3;
                transform: scale(1.05);
            }
            
            .voice-button.recording {
                background: #dc3545;
                animation: pulse 1s infinite;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }
    
    addRecordingStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .recording-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            }
            
            .recording-overlay.hidden {
                display: none;
            }
            
            .recording-content {
                background: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            }
            
            .recording-dot {
                width: 20px;
                height: 20px;
                background: #dc3545;
                border-radius: 50%;
                margin: 0 auto 15px;
                animation: pulse 1s infinite;
            }
            
            .recording-text {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 20px;
                color: #333;
            }
            
            #waveform-canvas {
                border: 1px solid #ddd;
                border-radius: 5px;
                margin: 20px 0;
                background: #f8f9fa;
            }
            
            .stop-recording-btn {
                background: #dc3545;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                transition: background 0.3s ease;
            }
            
            .stop-recording-btn:hover {
                background: #c82333;
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize voice recorder when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for the interview handler to initialize
    setTimeout(() => {
        window.voiceRecorder = new VoiceRecorder();
    }, 1000);
});
