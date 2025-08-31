"""
Voice Router - Handles all voice-related endpoints (DISABLED)
"""

from fastapi import APIRouter, HTTPException
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/voice-health")
async def check_voice_health():
    """Voice service disabled"""
    return {
        "success": True,
        "voice_available": False,
        "voice_modal_status": "disabled",
        "message": "Voice service disabled"
    }

@router.post("/voice-input")
async def submit_voice_input():
    """Voice input disabled"""
    raise HTTPException(status_code=503, detail="Voice input disabled")

@router.post("/voice-answer")
async def submit_voice_answer():
    """Voice answer disabled"""
    raise HTTPException(status_code=503, detail="Voice answer disabled")
