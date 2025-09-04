"""
ElevenLabs Text-to-Speech Service
Handles text-to-speech conversion using ElevenLabs API
"""

import httpx
import logging
import os
from typing import Optional, Dict, Any, Union
import base64
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
        self.timeout = 30.0
        
        # Voice configuration from environment
        self.voice_id_tamil = os.getenv("ELEVENLABS_VOICE_ID_TA", "JBFqnCBsd6RMkjVDRZzb")  # Default voice
        self.voice_id_english = os.getenv("ELEVENLABS_VOICE_ID_EN", "JBFqnCBsd6RMkjVDRZzb")  # Default voice
        self.tts_model = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")
        
        if not self.api_key:
            logger.warning("ElevenLabs API key not found in environment variables")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for ElevenLabs API requests"""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def health_check(self) -> bool:
        """
        Check if ElevenLabs API is available
        Returns True if healthy, False otherwise
        """
        if not self.api_key:
            logger.warning("ElevenLabs API key not configured")
            return False
            
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers()
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"ElevenLabs health check failed: {e}")
            return False
    
    async def text_to_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_settings: Optional[Dict[str, float]] = None,
        output_format: str = "mp3_44100_128"
    ) -> Dict[str, Any]:
        """
        Convert text to speech using ElevenLabs API
        
        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID (defaults to English voice)
            model_id: Model to use (defaults to eleven_multilingual_v2)
            voice_settings: Voice settings (stability, similarity_boost, style, use_speaker_boost)
            output_format: Audio output format
            
        Returns:
            Dict with audio data or error information
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "api_key_missing",
                "message": "ElevenLabs API key not configured"
            }
        
        if not text or not text.strip():
            return {
                "success": False,
                "error": "empty_text",
                "message": "Text cannot be empty"
            }
        
        # Use provided voice_id or default to English voice
        selected_voice_id = voice_id or self.voice_id_english
        selected_model_id = model_id or self.tts_model
        
        # Default voice settings optimized for medical conversations
        default_voice_settings = {
            "stability": 0.0,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": False
        }
        
        if voice_settings:
            default_voice_settings.update(voice_settings)
        
        try:
            payload = {
                "text": text.strip(),
                "model_id": selected_model_id,
                "voice_settings": default_voice_settings
            }
            
            url = f"{self.base_url}/text-to-speech/{selected_voice_id}"
            if output_format:
                url += f"?output_format={output_format}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    # Convert audio bytes to base64 for JSON transport
                    audio_base64 = base64.b64encode(response.content).decode('utf-8')
                    
                    logger.info(f"TTS successful: {len(text)} chars -> {len(response.content)} bytes")
                    
                    return {
                        "success": True,
                        "audio_base64": audio_base64,
                        "audio_format": output_format,
                        "voice_id": selected_voice_id,
                        "model_id": selected_model_id,
                        "text_length": len(text),
                        "audio_size": len(response.content),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    error_detail = response.text
                    logger.error(f"ElevenLabs API error: {response.status_code} - {error_detail}")
                    
                    return {
                        "success": False,
                        "error": f"api_error_{response.status_code}",
                        "message": f"TTS conversion failed: {error_detail}",
                        "status_code": response.status_code
                    }
                    
        except httpx.TimeoutException:
            logger.error("ElevenLabs API timeout")
            return {
                "success": False,
                "error": "timeout",
                "message": "TTS conversion timed out"
            }
        except Exception as e:
            logger.error(f"TTS conversion error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "TTS conversion failed"
            }
    
    async def text_to_speech_stream(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_settings: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Convert text to speech with streaming response
        
        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID
            model_id: Model to use
            voice_settings: Voice settings
            
        Returns:
            Dict with streaming audio data or error information
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "api_key_missing",
                "message": "ElevenLabs API key not configured"
            }
        
        selected_voice_id = voice_id or self.voice_id_english
        selected_model_id = model_id or self.tts_model
        
        default_voice_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        if voice_settings:
            default_voice_settings.update(voice_settings)
        
        try:
            payload = {
                "text": text.strip(),
                "model_id": selected_model_id,
                "voice_settings": default_voice_settings
            }
            
            url = f"{self.base_url}/text-to-speech/{selected_voice_id}/stream"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=self._get_headers()
                ) as response:
                    
                    if response.status_code == 200:
                        # Collect all chunks
                        audio_chunks = []
                        async for chunk in response.aiter_bytes():
                            audio_chunks.append(chunk)
                        
                        # Combine all chunks
                        audio_data = b''.join(audio_chunks)
                        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                        
                        logger.info(f"Streaming TTS successful: {len(text)} chars -> {len(audio_data)} bytes")
                        
                        return {
                            "success": True,
                            "audio_base64": audio_base64,
                            "audio_format": "mp3",
                            "voice_id": selected_voice_id,
                            "model_id": selected_model_id,
                            "text_length": len(text),
                            "audio_size": len(audio_data),
                            "timestamp": datetime.now().isoformat(),
                            "streaming": True
                        }
                    else:
                        error_detail = await response.aread()
                        logger.error(f"ElevenLabs streaming API error: {response.status_code} - {error_detail}")
                        
                        return {
                            "success": False,
                            "error": f"streaming_api_error_{response.status_code}",
                            "message": f"Streaming TTS conversion failed: {error_detail.decode()}",
                            "status_code": response.status_code
                        }
                        
        except Exception as e:
            logger.error(f"Streaming TTS conversion error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Streaming TTS conversion failed"
            }
    
    async def get_available_voices(self) -> Dict[str, Any]:
        """
        Get list of available voices from ElevenLabs
        
        Returns:
            Dict with voices list or error information
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "api_key_missing",
                "message": "ElevenLabs API key not configured"
            }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    voices_data = response.json()
                    
                    return {
                        "success": True,
                        "voices": voices_data.get("voices", []),
                        "total_voices": len(voices_data.get("voices", [])),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Failed to get voices: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"api_error_{response.status_code}",
                        "message": "Failed to retrieve voices"
                    }
                    
        except Exception as e:
            logger.error(f"Error getting voices: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve voices"
            }
    
    def get_voice_for_language(self, language: str = "en") -> str:
        """
        Get appropriate voice ID for given language
        
        Args:
            language: Language code (en, ta, etc.)
            
        Returns:
            Voice ID string
        """
        if language.lower() in ["ta", "tamil"]:
            return self.voice_id_tamil
        else:
            return self.voice_id_english

# Global TTS service instance
tts_service = TTSService()
