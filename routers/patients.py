"""
Patient management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import uuid
from datetime import datetime

from models.patient import PatientCreate, PatientInfo, PatientResponse
from services.session_service import get_or_create_session, sessions

router = APIRouter()

@router.post("/patients/register", response_model=PatientResponse)
async def register_patient(patient_data: PatientCreate):
    """Register a new patient and create session"""
    
    try:
        # Generate unique patient ID
        patient_id = str(uuid.uuid4())
        
        # Create patient info
        patient_info = PatientInfo(
            id=patient_id,
            name=patient_data.name,
            mobile=patient_data.mobile,
            age=patient_data.age,
            gender=patient_data.gender,
            chosen_doctor=patient_data.chosen_doctor,
            chosen_department=patient_data.chosen_department,
            skip_doctor_selection=patient_data.skip_doctor_selection,
            created_at=datetime.now().isoformat()
        )
        
        # Create or get session
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "patient_info": patient_info.dict(),
            "current_page": "interview",
            "created_at": datetime.now().isoformat()
        }
        
        sessions[session_id] = session_data
        
        return PatientResponse(
            success=True,
            message="Patient registered successfully",
            patient=patient_info,
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str, session_id: str):
    """Get patient information by ID"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    patient_info = session_data.get("patient_info")
    
    if not patient_info or patient_info["id"] != patient_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return {
        "success": True,
        "patient": patient_info
    }

@router.get("/patients/{patient_id}/session")
async def get_patient_session(patient_id: str, session_id: str):
    """Get current session data for patient"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    
    return {
        "success": True,
        "session": session_data
    }
