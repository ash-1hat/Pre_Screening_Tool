"""
Session management API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any
from services.session_service import sessions, get_session
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class SessionDataRequest(BaseModel):
    session_id: str
    patient_info: Dict[str, Any]
    consultation_data: Optional[Dict[str, Any]] = None

@router.post("/store-session-data")
async def store_session_data(request: SessionDataRequest):
    """Store patient and consultation data in session for interview endpoints"""
    
    try:
        logger.info(f"📋 [SESSION] Storing session data for session: {request.session_id}")
        
        # Get or create session
        session = get_session(request.session_id)
        if not session:
            # Create new session if it doesn't exist
            session = {
                "session_id": request.session_id,
                "patient_info": request.patient_info,
                "consultation_data": request.consultation_data,
                "selected_doctor_choice": {}
            }
            sessions[request.session_id] = session
            logger.info(f"✅ [SESSION] Created new session: {request.session_id}")
        else:
            # Update existing session
            session["patient_info"] = request.patient_info
            session["consultation_data"] = request.consultation_data
            logger.info(f"✅ [SESSION] Updated existing session: {request.session_id}")
        
        logger.info(f"📊 [SESSION] Session data keys: {list(session.keys())}")
        
        return {
            "success": True,
            "message": "Session data stored successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ [SESSION] Error storing session data: {e}")
        raise HTTPException(status_code=500, detail="Failed to store session data")

@router.post("/log-doctor-selection")
async def log_doctor_selection(request: Dict[str, Any]):
    """Log doctor selection for debugging purposes"""
    
    try:
        session_id = request.get("session_id")
        logger.info(f"🩺 [DOCTOR_SELECTION] {request.get('message', 'Doctor selection logged')}")
        logger.info(f"   - Session ID: {session_id}")
        logger.info(f"   - Doctor Name: {request.get('doctor_name')}")
        logger.info(f"   - Doctor ID: {request.get('doctor_id')}")
        logger.info(f"   - Selection Type: {request.get('selection_type')}")
        
        # Update session with doctor selection if session_id provided
        if session_id:
            session = get_session(session_id)
            if session:
                session["selected_doctor_choice"] = {
                    "type": request.get('selection_type'),
                    "doctor_name": request.get('doctor_name'),
                    "doctor_id": request.get('doctor_id')
                }
                logger.info(f"✅ [SESSION] Updated doctor selection in session")
        
        return {
            "success": True,
            "message": "Doctor selection logged successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ [DOCTOR_SELECTION] Error logging selection: {e}")
        raise HTTPException(status_code=500, detail="Failed to log doctor selection")
