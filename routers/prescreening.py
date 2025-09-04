"""
Pre-Screening Router for Medical Pre-Screening Tool
Handles storing pre-screening data in Supabase
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from services.supabase_service import supabase_service
from services.session_service import get_session
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class AcceptPrescreeningRequest(BaseModel):
    session_id: str

@router.post("/api/prescreening/accept")
async def accept_prescreening(request: AcceptPrescreeningRequest):
    """
    Accept and store pre-screening data in Supabase
    Gets pre-screening data from session and stores it in database
    """
    try:
        logger.info(f"📋 Processing pre-screening acceptance for session: {request.session_id}")
        
        # Get session data using custom session service
        session = await get_session(request.session_id)
        if not session:
            logger.error(f"❌ Session not found: {request.session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get pre-screening data from session
        prescreening_data = session.get("prescreening_data")
        if not prescreening_data:
            logger.error("❌ No pre-screening data found in session")
            raise HTTPException(
                status_code=400, 
                detail="No pre-screening data found. Please complete the medical interview first."
            )
        
        logger.info(f"💾 Storing pre-screening data: {prescreening_data.get('patient_uuid', 'Unknown')}")
        
        # Store in Supabase
        created_record = await supabase_service.create_prescreening_record(prescreening_data)
        
        if not created_record:
            logger.error("❌ Failed to create pre-screening record")
            raise HTTPException(
                status_code=500, 
                detail="Failed to store pre-screening data. Please try again."
            )
        
        # Clear the session data after successful storage
        if "prescreening_data" in session:
            del session["prescreening_data"]
        
        logger.info(f"✅ Pre-screening record accepted and stored with ID: {created_record['id']}")
        
        return {
            "success": True,
            "message": "Pre-screening data accepted and stored successfully",
            "record_id": created_record["id"],
            "patient_uuid": created_record.get("patient_uuid"),
            "visit_type": created_record.get("visit_type"),
            "created_at": created_record.get("created_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in accept_prescreening: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
