/**
 * Simple Voice Input using Browser Web Speech API
 * Provides voice-to-text transcription without external dependencies
 */

class SimpleVoiceInput {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.voiceButton = null;
        this.textInput = null;
        this.isSupported = false;
        this.finalTranscript = '';
        this.interimTranscript = '';
        this.silenceTimer = null;
        this.maxSilenceDuration = 4000; // 6 seconds of silence before auto-submit
        this.manualSubmitInProgress = false; // Flag to prevent auto-submit during manual submission
        
        this.init();
    }
    
    init() {
        // Check if Web Speech API is supported
        this.isSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        
        if (!this.isSupported) {
            console.log('[VOICE] Web Speech API not supported in this browser');
            return;
        }
        
        // Initialize speech recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Configure recognition settings for longer sentences
        this.recognition.continuous = true;          // Enable continuous listening
        this.recognition.interimResults = true;      // Show interim results
        this.recognition.lang = 'ta-IN';            // Tamil language for transcription
        this.recognition.maxAlternatives = 1;       // Only need best result
        
        // Setup DOM elements
        this.setupDOM();
        this.setupEventListeners();
        this.setupSubmitButtonListener();
        
        console.log('[VOICE] Simple voice input initialized with continuous mode');
    }
    
    setupDOM() {
        // Find the input container
        const inputContainer = document.querySelector('.input-container');
        if (!inputContainer) return;
        
        // Get the text input
        this.textInput = document.getElementById('patient-answer');
        if (!this.textInput) return;
        
        // Create voice button
        this.voiceButton = document.createElement('button');
        this.voiceButton.id = 'simple-voice-btn';
        this.voiceButton.className = 'voice-button';
        this.voiceButton.type = 'button';
        this.voiceButton.title = 'Voice Input (Tamil) - Click to start/stop';
        this.voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        
        // Insert before send button
        const sendButton = document.getElementById('send-answer');
        inputContainer.insertBefore(this.voiceButton, sendButton);
        
        // Add styles
        this.addStyles();
        
        // Show/hide based on support
        if (this.isSupported) {
            this.voiceButton.style.display = 'flex';
        } else {
            this.voiceButton.style.display = 'none';
        }
    }
    
    setupEventListeners() {
        if (!this.voiceButton || !this.recognition) return;
        
        // Voice button click
        this.voiceButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.toggleListening();
        });
        
        // Speech recognition events
        this.recognition.onstart = () => {
            console.log('[VOICE] Speech recognition started (continuous mode)');
            this.updateUI(true);
            this.finalTranscript = '';
            this.interimTranscript = '';
            this.manualSubmitInProgress = false; // Reset flag when starting new recording
        };
        
        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = this.finalTranscript;
            let hasNewFinal = false;
            
            // Process all results
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                const transcript = result[0].transcript;
                
                if (result.isFinal) {
                    finalTranscript += transcript + ' ';
                    hasNewFinal = true;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Update stored transcripts
            this.finalTranscript = finalTranscript;
            this.interimTranscript = interimTranscript;
            
            // Combine final and interim for display
            const combinedTranscript = (finalTranscript + interimTranscript).trim();
            
            // Update text input with combined transcript
            if (combinedTranscript) {
                this.textInput.value = combinedTranscript;
                
                // Trigger input event to enable send button
                this.textInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
            
            // Start silence timer when we get final results (speech segment ended)
            if (hasNewFinal) {
                console.log('[VOICE] Final result received, starting silence timer');
                this.startSilenceTimer();
            }
            
            console.log('[VOICE] Final:', finalTranscript, 'Interim:', interimTranscript, 'HasNewFinal:', hasNewFinal);
        };
        
        this.recognition.onend = () => {
            console.log('[VOICE] Speech recognition ended');
            this.isListening = false;
            this.updateUI(false);
            this.clearSilenceTimer();
            
            // If we have accumulated transcript, keep it in the input
            const finalText = this.finalTranscript.trim();
            if (finalText) {
                this.textInput.value = finalText;
                this.textInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
        };
        
        this.recognition.onerror = (event) => {
            console.error('[VOICE] Speech recognition error:', event.error);
            this.isListening = false;
            this.updateUI(false);
            this.clearSilenceTimer();
            
            // Show user-friendly error message
            if (event.error === 'no-speech') {
                this.showMessage('No speech detected. Please try again.');
            } else if (event.error === 'not-allowed') {
                this.showMessage('Microphone access denied. Please allow microphone access.');
            } else if (event.error === 'aborted') {
                // User manually stopped - don't show error
                console.log('[VOICE] Recognition manually stopped');
            } else {
                this.showMessage('Voice input error. Please type your answer.');
            }
        };
        
        // Handle speech silence detection - remove these as they conflict with onresult timing
        // this.recognition.onspeechend = () => {
        //     console.log('[VOICE] Speech ended, starting silence timer');
        //     this.startSilenceTimer();
        // };
        
        // this.recognition.onspeechstart = () => {
        //     console.log('[VOICE] Speech started, clearing silence timer');
        //     this.clearSilenceTimer();
        // };
    }
    
    setupSubmitButtonListener() {
        // Monitor the submit button for manual submissions
        const sendButton = document.getElementById('send-answer');
        if (sendButton) {
            sendButton.addEventListener('click', () => {
                console.log('[VOICE] Manual submit detected - stopping recording and clearing timer');
                this.handleManualSubmit();
            });
        }
        
        // Also monitor for Enter key submissions on the textarea
        const textarea = document.getElementById('patient-answer');
        if (textarea) {
            textarea.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    console.log('[VOICE] Manual submit via Enter key - stopping recording and clearing timer');
                    this.handleManualSubmit();
                }
            });
        }
    }
    
    handleManualSubmit() {
        // Set flag to prevent auto-submit
        this.manualSubmitInProgress = true;
        
        // Stop recording immediately
        if (this.isListening) {
            this.stopListening();
        }
        
        // Clear any pending auto-submit timer
        this.clearSilenceTimer();
        
        // Clear text input after manual submission
        setTimeout(() => {
            this.clearTextInput();
        }, 500);
        
        // Reset the flag after a short delay to allow for new recordings
        setTimeout(() => {
            this.manualSubmitInProgress = false;
            console.log('[VOICE] Manual submit completed - ready for new recording');
        }, 1000);
    }
    
    resetSilenceTimer() {
        this.clearSilenceTimer();
        // Don't start silence timer immediately - wait for speech to end
    }
    
    startSilenceTimer() {
        this.clearSilenceTimer();
        this.silenceTimer = setTimeout(() => {
            console.log('[VOICE] Auto-submitting due to 6 seconds of silence');
            this.autoSubmitAnswer();
        }, this.maxSilenceDuration);
    }
    
    clearSilenceTimer() {
        if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = null;
        }
    }
    
    autoSubmitAnswer() {
        console.log('[VOICE] Auto-submit triggered');
        
        // Check if manual submit is in progress - if so, abort auto-submit
        if (this.manualSubmitInProgress) {
            console.log('[VOICE] Manual submit in progress - aborting auto-submit');
            return;
        }
        
        // Stop listening first
        this.stopListening();
        
        // Get the final transcript
        const finalText = this.finalTranscript.trim();
        console.log('[VOICE] Final text for auto-submit:', finalText);
        
        if (finalText) {
            console.log('[VOICE] Auto-submitting answer:', finalText);
            
            // Set flag to prevent duplicate submissions
            this.manualSubmitInProgress = true;
            
            // Set the text in the input field
            this.textInput.value = finalText;
            this.textInput.dispatchEvent(new Event('input', { bubbles: true }));
            
            // Wait a moment for the input event to process, then submit
            setTimeout(() => {
                // Double-check that manual submit hasn't occurred in the meantime
                if (!this.manualSubmitInProgress) {
                    console.log('[VOICE] Manual submit occurred during auto-submit delay - aborting');
                    return;
                }
                
                // Trigger the submit answer functionality
                // Look for the send button and click it programmatically
                const sendButton = document.getElementById('send-answer');
                console.log('[VOICE] Send button found:', !!sendButton, 'Disabled:', sendButton?.disabled);
                
                if (sendButton && !sendButton.disabled) {
                    console.log('[VOICE] Clicking send button via auto-submit');
                    sendButton.click();
                } else {
                    // Fallback: try to call the submit function directly if available
                    if (window.medicalInterviewHandler && typeof window.medicalInterviewHandler.submitAnswer === 'function') {
                        console.log('[VOICE] Using direct submit function via auto-submit');
                        window.medicalInterviewHandler.submitAnswer();
                    } else {
                        console.log('[VOICE] Could not auto-submit - no submit mechanism found');
                        console.log('[VOICE] Available handlers:', Object.keys(window));
                        this.showMessage('Voice input completed. Please click Send to submit your answer.');
                    }
                }
                
                // Clear text input after auto-submit
                setTimeout(() => {
                    this.clearTextInput();
                }, 500);
                
                // Reset flag after auto-submit
                setTimeout(() => {
                    this.manualSubmitInProgress = false;
                    console.log('[VOICE] Auto-submit completed - ready for new recording');
                }, 1000);
            }, 100);
        } else {
            console.log('[VOICE] No transcript to submit');
            this.showMessage('No speech detected. Please try again or type your answer.');
        }
    }
    
    clearTextInput() {
        console.log('[VOICE] Clearing text input field');
        if (this.textInput) {
            this.textInput.value = '';
            this.textInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        // Also clear internal transcript variables
        this.finalTranscript = '';
        this.interimTranscript = '';
    }
    
    toggleListening() {
        if (!this.recognition) return;
        
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }
    
    startListening() {
        if (!this.recognition || this.isListening) return;
        
        try {
            // Set language to Tamil for direct transcription
            this.recognition.lang = 'ta-IN'; // Tamil transcription only
            
            this.recognition.start();
            this.isListening = true;
            console.log('[VOICE] Starting continuous listening...');
        } catch (error) {
            console.error('[VOICE] Failed to start listening:', error);
            this.showMessage('Voice input not available. Please type your answer.');
        }
    }
    
    stopListening() {
        if (!this.recognition || !this.isListening) return;
        
        this.recognition.stop();
        this.isListening = false;
        this.clearSilenceTimer();
        console.log('[VOICE] Stopped listening');
    }
    
    updateUI(listening) {
        if (!this.voiceButton) return;
        
        if (listening) {
            this.voiceButton.classList.add('listening');
            this.voiceButton.innerHTML = '<i class="fas fa-stop"></i>';
            this.voiceButton.title = 'Stop Voice Input - Click to stop recording';
        } else {
            this.voiceButton.classList.remove('listening');
            this.voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
            this.voiceButton.title = 'Voice Input (Tamil) - Click to start/stop';
        }
    }
    
    showMessage(message) {
        // Try to use existing error display mechanism
        if (window.medicalInterviewHandler && window.medicalInterviewHandler.showError) {
            window.medicalInterviewHandler.showError(message);
        } else {
            // Fallback to console
            console.log('[VOICE] Message:', message);
        }
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .voice-button {
                background: #28a745;
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
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                position: relative;
            }
            
            .voice-button:hover {
                background: #218838;
                transform: scale(1.05);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }
            
            .voice-button:active {
                transform: scale(0.95);
            }
            
            .voice-button.listening {
                background: #dc3545;
                animation: pulse 1.5s infinite;
            }
            
            .voice-button.listening:hover {
                background: #c82333;
            }
            
            .voice-button.listening::after {
                content: '';
                position: absolute;
                top: -3px;
                right: -3px;
                width: 12px;
                height: 12px;
                background: #ffc107;
                border-radius: 50%;
                animation: blink 1s infinite;
            }
            
            @keyframes pulse {
                0% { 
                    transform: scale(1); 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                50% { 
                    transform: scale(1.05); 
                    box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4);
                }
                100% { 
                    transform: scale(1); 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
            }
            
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0; }
            }
            
            /* Hide voice button if not supported */
            .voice-button.unsupported {
                display: none !important;
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Wait for other components to initialize
    setTimeout(() => {
        window.simpleVoiceInput = new SimpleVoiceInput();
    }, 500);
});
