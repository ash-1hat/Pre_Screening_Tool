"""
Voice Service for integrating with Voice_Modal API
Handles speech-to-text functionality for patient voice input
"""

import httpx
import logging
from typing import Optional, Dict, Any
import base64
import asyncio

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        self.voice_modal_url = "http://localhost:8000"
        self.timeout = 30.0
        # JWT authentication is bypassed in Voice_Modal testing mode
        self.jwt_token = None  # Not needed since auth is bypassed
    
    async def health_check(self) -> bool:
        """
        Check if Voice_Modal API is available
        Returns True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.voice_modal_url}/health/")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Voice_Modal health check failed: {e}")
            # For testing without Voice_Modal service, return False gracefully
            return False
    
    async def transcribe_audio(self, audio_data: bytes, audio_format: str = "audio/webm", stt_provider: str = "sarvam", timestamps: bool = False) -> Dict[str, Any]:
        """
        Send audio to Voice_Modal /v1/listen endpoint for transcription
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio MIME type (default: audio/webm)
            stt_provider: STT provider to use (default: sarvam)
            timestamps: Whether to include timestamps (default: False)
            
        Returns:
            Dict with transcription result or error
        """
        try:
            headers = {}
            # JWT auth is bypassed in Voice_Modal testing mode
            
            # Prepare multipart form data
            files = {
                "audio": (audio_data)
            }
            
            data = {
                "stt_provider": stt_provider,
                "timestamps": timestamps
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.voice_modal_url}/v1/listen",
                    files=files,
                    data=data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Voice transcription successful: {result.get('original_language', 'unknown')} -> English")
                    return {
                        "success": True,
                        "english_transcript": result.get("english_transcript", ""),
                        "original_language": result.get("original_language", "auto"),
                        "original_text": result.get("original_text", ""),
                        "confidence": result.get("confidence", 0.0),
                        "processing_time": result.get("processing_time_sec", 0.0),
                        "provider": result.get("stt_provider", "unknown")
                    }
                else:
                    logger.error(f"Voice_Modal API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}",
                        "message": "Voice transcription failed"
                    }
                    
        except httpx.TimeoutException:
            logger.error("Voice_Modal API timeout")
            return {
                "success": False,
                "error": "timeout",
                "message": "Voice processing timed out"
            }
        except Exception as e:
            logger.error(f"Voice transcription error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Voice processing failed"
            }
    
    async def transcribe_base64_audio(self, audio_base64: str) -> Dict[str, Any]:
        """
        Send base64 encoded audio to Voice_Modal for transcription
        
        Args:
            audio_base64: Base64 encoded audio data
            
        Returns:
            Dict with transcription result or error
        """
        try:
            headers = {}
            # JWT auth is bypassed in Voice_Modal testing mode
            
            data = {
                "audio_base64": audio_base64,
                "stt_provider": "sarvam",
                "timestamps": False
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.voice_modal_url}/v1/listen",
                    data=data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Voice transcription successful: {result.get('original_language', 'unknown')} -> English")
                    return {
                        "success": True,
                        "english_transcript": result.get("english_transcript", ""),
                        "original_language": result.get("original_language", "auto"),
                        "original_text": result.get("original_text", ""),
                        "confidence": result.get("confidence", 0.0),
                        "processing_time": result.get("processing_time_sec", 0.0),
                        "provider": result.get("stt_provider", "unknown")
                    }
                else:
                    logger.error(f"Voice_Modal API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}",
                        "message": "Voice transcription failed"
                    }
                    
        except httpx.TimeoutException:
            logger.error("Voice_Modal API timeout")
            return {
                "success": False,
                "error": "timeout",
                "message": "Voice processing timed out"
            }
        except Exception as e:
            logger.error(f"Voice transcription error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Voice processing failed"
            }

# Global voice service instance
voice_service = VoiceService()
