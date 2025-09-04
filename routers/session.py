"""
Session management API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any
from services.session_service import (
    create_session,
    get_session,
    update_session,
    delete_session,
    cleanup_expired_sessions
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class SessionDataRequest(BaseModel):
    session_id: str
    patient_info: Dict[str, Any]
    consultation_data: Optional[Dict[str, Any]] = None

@router.post("/create-session")
async def create_new_session():
    """Create a new session"""
    session_id = await create_session()
    return {"session_id": session_id}

@router.post("/store-session-data")
async def store_session_data(request: SessionDataRequest):
    """Store patient and consultation data in session for interview endpoints"""
    
    try:
        logger.info(f"📋 [SESSION] Storing session data for session: {request.session_id}")
        
        # Get or create session
        session = await get_session(request.session_id)
        if not session:
            # Create new session if it doesn't exist
            session_id = await create_session()
            await update_session(session_id, {
                "patient_info": request.patient_info,
                "consultation_data": request.consultation_data,
                "selected_doctor_choice": {}
            })
            logger.info(f"✅ [SESSION] Created new session: {session_id}")
            return {
                "success": True,
                "message": "New session created and data stored",
                "session_id": session_id
            }
        else:
            # Update existing session
            await update_session(request.session_id, {
                "patient_info": request.patient_info,
                "consultation_data": request.consultation_data
            })
            logger.info(f"✅ [SESSION] Updated existing session: {request.session_id}")
        
        
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
            session = await get_session(session_id)
            if session:
                # Merge doctor selection into existing session data
                session["selected_doctor_choice"] = {
                    "type": request.get('selection_type'),
                    "doctor_name": request.get('doctor_name'),
                    "doctor_id": request.get('doctor_id')
                }
                await update_session(session_id, session)
                logger.info(f"✅ [SESSION] Updated doctor selection in session")
        
        return {
            "success": True,
            "message": "Doctor selection logged successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ [DOCTOR_SELECTION] Error logging selection: {e}")
        raise HTTPException(status_code=500, detail="Failed to log doctor selection")

class UpdateSessionRequest(BaseModel):
    session_id: str
    data: Dict[str, Any]

@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    """Get session data by session ID for interview page"""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return session

@router.post("/update-session")
async def update_session_data(request: UpdateSessionRequest):
    """Update session data"""
    success = await update_session(request.session_id, request.data)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": "Session updated successfully"}

@router.delete("/session/{session_id}")
async def delete_session_data(session_id: str):
    """Delete session data"""
    success = delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": "Session deleted successfully"}

@router.post("/cleanup-sessions")
async def cleanup_expired():
    """Cleanup expired sessions"""
    cleanup_expired_sessions()
    return {"success": True, "message": "Expired sessions cleaned up"}
