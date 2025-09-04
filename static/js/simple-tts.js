/**
 * Simple TTS Integration for Medical Interview
 * Automatically converts AI questions to speech using ElevenLabs
 */

class SimpleTTS {
    constructor() {
        this.isEnabled = true; // TTS enabled by default
        this.currentAudio = null;
        this.sessionId = null;
        this.language = 'en'; // Default to English
        
        this.initializeUI();
        this.bindEvents();
    }

    initializeUI() {
        this.toggleButton = document.getElementById('toggle-audio');
        if (this.toggleButton) {
            this.updateButtonState();
        }
    }

    bindEvents() {
        if (this.toggleButton) {
            this.toggleButton.addEventListener('click', () => {
                this.toggleTTS();
            });
        }
    }

    toggleTTS() {
        this.isEnabled = !this.isEnabled;
        this.updateButtonState();
        
        // Stop current audio if disabling
        if (!this.isEnabled && this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
        
        console.log(`TTS ${this.isEnabled ? 'enabled' : 'disabled'}`);
    }

    updateButtonState() {
        if (!this.toggleButton) return;
        
        const icon = this.toggleButton.querySelector('i');
        
        if (this.isEnabled) {
            this.toggleButton.classList.remove('disabled');
            this.toggleButton.innerHTML = '<i class="fas fa-volume-up"></i> Disable Audio Questions';
        } else {
            this.toggleButton.classList.add('disabled');
            this.toggleButton.innerHTML = '<i class="fas fa-volume-mute"></i> Enable Audio Questions';
        }
    }

    setSessionId(sessionId) {
        this.sessionId = sessionId;
    }

    setLanguage(language) {
        this.language = language || 'en';
    }

    async convertQuestionToSpeech(question) {
        if (!this.isEnabled || !question) {
            console.log('TTS skipped:', { enabled: this.isEnabled, hasQuestion: !!question });
            return null;
        }

        try {
            const requestStart = performance.now();
            console.log('[TTS_TIMING] Starting TTS request at:', requestStart);
            console.log('TTS: Converting question to speech:', question.substring(0, 50) + '...');
            
            const response = await fetch('/api/medical/question-tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: question,
                    language: this.language
                })
            });

            const responseReceived = performance.now();
            const apiCallDuration = responseReceived - requestStart;
            console.log(`[TTS_TIMING] API response received in ${apiCallDuration.toFixed(1)}ms`);

            if (!response.ok) {
                const errorText = await response.text();
                console.warn('TTS conversion failed:', response.status, errorText);
                return null;
            }

            const data = await response.json();
            const parseComplete = performance.now();
            const parseDuration = parseComplete - responseReceived;
            
            console.log(`[TTS_TIMING] Response parsed in ${parseDuration.toFixed(1)}ms`);
            console.log('[TTS_TIMING] Server reported API duration:', data.api_duration ? `${(data.api_duration * 1000).toFixed(1)}ms` : 'N/A');
            console.log('[TTS_TIMING] Audio size:', data.audio_size_kb ? `${data.audio_size_kb.toFixed(1)}KB` : 'N/A');
            
            if (data.success && data.audio_base64) {
                return { 
                    audio: data.audio_base64, 
                    timing: {
                        totalRequest: apiCallDuration,
                        serverApi: data.api_duration * 1000,
                        parsing: parseDuration
                    }
                };
            }
            
            return null;
        } catch (error) {
            console.warn('TTS conversion error:', error);
            return null;
        }
    }

    async playQuestion(question) {
        if (!this.isEnabled) return;

        try {
            const playbackStart = performance.now();
            console.log('[TTS_TIMING] Starting playQuestion at:', playbackStart);

            // Stop any currently playing audio
            if (this.currentAudio) {
                this.currentAudio.pause();
                this.currentAudio = null;
            }

            const ttsResult = await this.convertQuestionToSpeech(question);
            if (!ttsResult) return;

            const conversionComplete = performance.now();
            console.log(`[TTS_TIMING] TTS conversion completed in ${(conversionComplete - playbackStart).toFixed(1)}ms`);

            // Create and play audio
            const blobStart = performance.now();
            const audioBlob = this.base64ToBlob(ttsResult.audio, 'audio/mpeg');
            const audioUrl = URL.createObjectURL(audioBlob);
            const blobComplete = performance.now();
            console.log(`[TTS_TIMING] Audio blob created in ${(blobComplete - blobStart).toFixed(1)}ms`);
            
            this.currentAudio = new Audio(audioUrl);
            
            // Clean up URL when audio ends
            this.currentAudio.addEventListener('ended', () => {
                const playbackEnd = performance.now();
                const totalPlaybackTime = playbackEnd - playbackStart;
                console.log(`[TTS_TIMING] Audio playback ended. Total time from request to playback end: ${totalPlaybackTime.toFixed(1)}ms`);
                URL.revokeObjectURL(audioUrl);
                this.currentAudio = null;
            });

            // Track when audio actually starts playing
            this.currentAudio.addEventListener('loadeddata', () => {
                const audioLoaded = performance.now();
                console.log(`[TTS_TIMING] Audio loaded and ready to play in ${(audioLoaded - blobComplete).toFixed(1)}ms`);
            });

            this.currentAudio.addEventListener('play', () => {
                const playStart = performance.now();
                const totalToPlay = playStart - playbackStart;
                console.log(`[TTS_TIMING] Audio playback started. Total time from request to play: ${totalToPlay.toFixed(1)}ms`);
                console.log('[TTS_TIMING] Breakdown:', {
                    'API Request': `${ttsResult.timing.totalRequest.toFixed(1)}ms`,
                    'ElevenLabs API': `${ttsResult.timing.serverApi.toFixed(1)}ms`,
                    'Response Parse': `${ttsResult.timing.parsing.toFixed(1)}ms`,
                    'Blob Creation': `${(blobComplete - blobStart).toFixed(1)}ms`,
                    'Audio Load': `${(playStart - blobComplete).toFixed(1)}ms`,
                    'Total to Play': `${totalToPlay.toFixed(1)}ms`
                });
            });

            // Play the audio
            await this.currentAudio.play();
            
        } catch (error) {
            console.warn('Audio playback error:', error);
        }
    }

    base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64);
        const byteNumbers = new Array(byteCharacters.length);
        
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: mimeType });
    }

    // Clean up resources
    destroy() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
    }
}

// Initialize TTS when DOM is loaded
let simpleTTS = null;

document.addEventListener('DOMContentLoaded', () => {
    simpleTTS = new SimpleTTS();
    
    // Make it globally available
    window.simpleTTS = simpleTTS;
});
