/**
 * TTS Audio Player for ElevenLabs Text-to-Speech Integration
 * Handles audio playback, controls, and UI for medical interview questions
 */

class TTSPlayer {
    constructor() {
        this.isPlaying = false;
        this.currentAudio = null;
        this.ttsEnabled = true;
        this.currentLanguage = 'en';
        this.autoPlay = false;
        this.volume = 0.8;
        
        this.initializePlayer();
        this.checkTTSHealth();
    }

    /**
     * Initialize TTS player UI and controls
     */
    initializePlayer() {
        // Create TTS control container if it doesn't exist
        if (!document.getElementById('tts-controls')) {
            this.createTTSControls();
        }
        
        // Bind event listeners
        this.bindEventListeners();
        
        console.log('TTS Player initialized');
    }

    /**
     * Create TTS control UI elements
     */
    createTTSControls() {
        const controlsHTML = `
            <div id="tts-controls" class="tts-controls">
                <div class="tts-header">
                    <span class="tts-title">🔊 Audio Assistant</span>
                    <div class="tts-status" id="tts-status">
                        <span class="status-indicator" id="tts-indicator">●</span>
                        <span id="tts-status-text">Checking...</span>
                    </div>
                </div>
                
                <div class="tts-player" id="tts-player" style="display: none;">
                    <button id="tts-play-btn" class="tts-btn tts-play-btn" title="Play question audio">
                        <span class="play-icon">▶️</span>
                        <span class="btn-text">Play Question</span>
                    </button>
                    
                    <button id="tts-stop-btn" class="tts-btn tts-stop-btn" title="Stop audio">
                        <span class="stop-icon">⏹️</span>
                    </button>
                    
                    <div class="tts-volume-control">
                        <span class="volume-icon">🔊</span>
                        <input type="range" id="tts-volume" min="0" max="100" value="80" class="volume-slider">
                    </div>
                </div>
                
                <div class="tts-settings">
                    <label class="tts-checkbox">
                        <input type="checkbox" id="tts-enabled" checked>
                        <span class="checkmark"></span>
                        Enable Audio Questions
                    </label>
                    
                    <label class="tts-checkbox">
                        <input type="checkbox" id="tts-autoplay">
                        <span class="checkmark"></span>
                        Auto-play Questions
                    </label>
                    
                    <div class="language-selector">
                        <label for="tts-language">Language:</label>
                        <select id="tts-language" class="language-select">
                            <option value="en">English</option>
                            <option value="ta">Tamil</option>
                        </select>
                    </div>
                </div>
                
                <div class="tts-loading" id="tts-loading" style="display: none;">
                    <div class="loading-spinner"></div>
                    <span>Generating audio...</span>
                </div>
            </div>
        `;

        // Add to chat container or create dedicated container
        const chatContainer = document.querySelector('.chat-container') || document.querySelector('.interview-container');
        if (chatContainer) {
            const controlsDiv = document.createElement('div');
            controlsDiv.innerHTML = controlsHTML;
            chatContainer.insertBefore(controlsDiv.firstElementChild, chatContainer.firstChild);
        }

        // Add CSS styles
        this.addTTSStyles();
    }

    /**
     * Add CSS styles for TTS controls
     */
    addTTSStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .tts-controls {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 20px;
                color: white;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                border: 1px solid rgba(255,255,255,0.1);
            }

            .tts-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }

            .tts-title {
                font-weight: 600;
                font-size: 16px;
            }

            .tts-status {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 12px;
            }

            .status-indicator {
                font-size: 8px;
                animation: pulse 2s infinite;
            }

            .status-indicator.healthy { color: #4ade80; }
            .status-indicator.unhealthy { color: #f87171; }
            .status-indicator.checking { color: #fbbf24; }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            .tts-player {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 12px;
                padding: 12px;
                background: rgba(255,255,255,0.1);
                border-radius: 8px;
            }

            .tts-btn {
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.3);
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 14px;
                transition: all 0.2s ease;
            }

            .tts-btn:hover {
                background: rgba(255,255,255,0.3);
                transform: translateY(-1px);
            }

            .tts-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }

            .tts-play-btn.playing {
                background: #4ade80;
                animation: pulse-green 1.5s infinite;
            }

            @keyframes pulse-green {
                0%, 100% { background: #4ade80; }
                50% { background: #22c55e; }
            }

            .tts-volume-control {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-left: auto;
            }

            .volume-slider {
                width: 80px;
                height: 4px;
                background: rgba(255,255,255,0.3);
                border-radius: 2px;
                outline: none;
                cursor: pointer;
            }

            .volume-slider::-webkit-slider-thumb {
                appearance: none;
                width: 16px;
                height: 16px;
                background: white;
                border-radius: 50%;
                cursor: pointer;
            }

            .tts-settings {
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                align-items: center;
                font-size: 13px;
            }

            .tts-checkbox {
                display: flex;
                align-items: center;
                gap: 6px;
                cursor: pointer;
            }

            .tts-checkbox input[type="checkbox"] {
                display: none;
            }

            .checkmark {
                width: 16px;
                height: 16px;
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.4);
                border-radius: 3px;
                position: relative;
            }

            .tts-checkbox input[type="checkbox"]:checked + .checkmark {
                background: #4ade80;
                border-color: #4ade80;
            }

            .tts-checkbox input[type="checkbox"]:checked + .checkmark::after {
                content: "✓";
                position: absolute;
                top: -2px;
                left: 2px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }

            .language-selector {
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .language-select {
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.3);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }

            .language-select option {
                background: #4a5568;
                color: white;
            }

            .tts-loading {
                display: flex;
                align-items: center;
                gap: 8px;
                justify-content: center;
                padding: 8px;
                background: rgba(255,255,255,0.1);
                border-radius: 6px;
                font-size: 13px;
            }

            .loading-spinner {
                width: 16px;
                height: 16px;
                border: 2px solid rgba(255,255,255,0.3);
                border-top: 2px solid white;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            /* Responsive design */
            @media (max-width: 768px) {
                .tts-controls {
                    padding: 12px;
                }
                
                .tts-settings {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 8px;
                }
                
                .tts-player {
                    flex-wrap: wrap;
                    gap: 8px;
                }
                
                .tts-volume-control {
                    margin-left: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Bind event listeners for TTS controls
     */
    bindEventListeners() {
        // Play button
        document.addEventListener('click', (e) => {
            if (e.target.closest('#tts-play-btn')) {
                this.playCurrentQuestion();
            }
        });

        // Stop button
        document.addEventListener('click', (e) => {
            if (e.target.closest('#tts-stop-btn')) {
                this.stopAudio();
            }
        });

        // Volume control
        document.addEventListener('input', (e) => {
            if (e.target.id === 'tts-volume') {
                this.setVolume(e.target.value / 100);
            }
        });

        // Settings checkboxes
        document.addEventListener('change', (e) => {
            if (e.target.id === 'tts-enabled') {
                this.ttsEnabled = e.target.checked;
                this.togglePlayerVisibility();
            }
            if (e.target.id === 'tts-autoplay') {
                this.autoPlay = e.target.checked;
            }
            if (e.target.id === 'tts-language') {
                this.currentLanguage = e.target.value;
            }
        });
    }

    /**
     * Check TTS service health
     */
    async checkTTSHealth() {
        try {
            const response = await fetch('/api/medical/tts-health');
            const result = await response.json();
            
            this.updateHealthStatus(result.tts_available, result.tts_available ? 'Ready' : 'Unavailable');
            
            if (result.tts_available) {
                this.togglePlayerVisibility();
            }
        } catch (error) {
            console.error('TTS health check failed:', error);
            this.updateHealthStatus(false, 'Error');
        }
    }

    /**
     * Update health status indicator
     */
    updateHealthStatus(isHealthy, statusText) {
        const indicator = document.getElementById('tts-indicator');
        const statusTextEl = document.getElementById('tts-status-text');
        
        if (indicator && statusTextEl) {
            indicator.className = `status-indicator ${isHealthy ? 'healthy' : 'unhealthy'}`;
            statusTextEl.textContent = statusText;
        }
    }

    /**
     * Toggle player visibility based on TTS enabled state
     */
    togglePlayerVisibility() {
        const player = document.getElementById('tts-player');
        if (player) {
            player.style.display = this.ttsEnabled ? 'flex' : 'none';
        }
    }

    /**
     * Convert question text to speech and play
     */
    async convertQuestionToSpeech(questionText, sessionId) {
        if (!this.ttsEnabled || !questionText) return null;

        this.showLoading(true);
        
        try {
            const response = await fetch('/api/medical/question-tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    question: questionText,
                    language: this.currentLanguage
                })
            });

            const result = await response.json();
            
            if (result.success) {
                console.log('TTS conversion successful');
                return result.audio_base64;
            } else {
                console.error('TTS conversion failed:', result);
                return null;
            }
        } catch (error) {
            console.error('TTS conversion error:', error);
            return null;
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Play audio from base64 data
     */
    async playAudio(audioBase64) {
        if (!audioBase64) return;

        try {
            // Stop current audio if playing
            this.stopAudio();

            // Create audio blob from base64
            const audioData = atob(audioBase64);
            const arrayBuffer = new ArrayBuffer(audioData.length);
            const uint8Array = new Uint8Array(arrayBuffer);
            
            for (let i = 0; i < audioData.length; i++) {
                uint8Array[i] = audioData.charCodeAt(i);
            }

            const audioBlob = new Blob([arrayBuffer], { type: 'audio/mpeg' });
            const audioUrl = URL.createObjectURL(audioBlob);

            // Create and play audio
            this.currentAudio = new Audio(audioUrl);
            this.currentAudio.volume = this.volume;

            this.currentAudio.addEventListener('loadstart', () => {
                this.updatePlayButton(true);
            });

            this.currentAudio.addEventListener('ended', () => {
                this.updatePlayButton(false);
                this.cleanup();
            });

            this.currentAudio.addEventListener('error', (e) => {
                console.error('Audio playback error:', e);
                this.updatePlayButton(false);
                this.cleanup();
            });

            await this.currentAudio.play();
            this.isPlaying = true;

        } catch (error) {
            console.error('Audio playback failed:', error);
            this.updatePlayButton(false);
        }
    }

    /**
     * Stop current audio playback
     */
    stopAudio() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.cleanup();
        }
        this.updatePlayButton(false);
        this.isPlaying = false;
    }

    /**
     * Clean up audio resources
     */
    cleanup() {
        if (this.currentAudio) {
            URL.revokeObjectURL(this.currentAudio.src);
            this.currentAudio = null;
        }
    }

    /**
     * Update play button state
     */
    updatePlayButton(isPlaying) {
        const playBtn = document.getElementById('tts-play-btn');
        if (playBtn) {
            if (isPlaying) {
                playBtn.classList.add('playing');
                playBtn.querySelector('.btn-text').textContent = 'Playing...';
                playBtn.disabled = true;
            } else {
                playBtn.classList.remove('playing');
                playBtn.querySelector('.btn-text').textContent = 'Play Question';
                playBtn.disabled = false;
            }
        }
    }

    /**
     * Set audio volume
     */
    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
        if (this.currentAudio) {
            this.currentAudio.volume = this.volume;
        }
    }

    /**
     * Show/hide loading indicator
     */
    showLoading(show) {
        const loading = document.getElementById('tts-loading');
        if (loading) {
            loading.style.display = show ? 'flex' : 'none';
        }
    }

    /**
     * Play current question (called by play button)
     */
    async playCurrentQuestion() {
        const currentQuestionEl = document.querySelector('.ai-message:last-child .message-text') || 
                                  document.querySelector('.question-text') ||
                                  document.querySelector('#current-question');
        
        if (!currentQuestionEl) {
            console.warn('No current question found to play');
            return;
        }

        const questionText = currentQuestionEl.textContent.trim();
        const sessionId = window.currentSessionId || sessionStorage.getItem('session_id');

        if (!sessionId) {
            console.warn('No session ID found for TTS');
            return;
        }

        const audioBase64 = await this.convertQuestionToSpeech(questionText, sessionId);
        if (audioBase64) {
            await this.playAudio(audioBase64);
        }
    }

    /**
     * Handle new question (called when new question is displayed)
     */
    async handleNewQuestion(questionText, sessionId) {
        if (!this.ttsEnabled) return;

        // Store current question for manual play
        this.currentQuestionText = questionText;
        this.currentSessionId = sessionId;

        // Auto-play if enabled
        if (this.autoPlay) {
            const audioBase64 = await this.convertQuestionToSpeech(questionText, sessionId);
            if (audioBase64) {
                // Small delay to let the question appear in UI
                setTimeout(() => {
                    this.playAudio(audioBase64);
                }, 500);
            }
        }
    }
}

// Initialize TTS Player when DOM is ready
let ttsPlayer;

document.addEventListener('DOMContentLoaded', () => {
    ttsPlayer = new TTSPlayer();
});

// Export for use in other scripts
window.TTSPlayer = TTSPlayer;
window.ttsPlayer = ttsPlayer;
