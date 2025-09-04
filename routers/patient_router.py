"""
Patient Management API Router
Handles manual patient lookup, creation, and face recognition integration
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
from services.supabase_service import supabase_service
from services.luxand_face_recognition_service import LuxandFaceRecognitionService
from services.session_service import sessions, update_session, get_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["patients"])

# Initialize Luxand face recognition service
face_recognition_service = LuxandFaceRecognitionService()

class ManualPatientRequest(BaseModel):
    name: str
    mobile: str
    age: int
    gender: str
    
    @validator('mobile')
    def validate_mobile(cls, v):
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Mobile number must be exactly 10 digits')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Name is required')
        return v.strip()
    
    @validator('age')
    def validate_age(cls, v):
        if v < 1 or v > 150:
            raise ValueError('Age must be between 1 and 150')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v not in ['Male', 'Female', 'Other']:
            raise ValueError('Gender must be Male, Female, or Other')
        return v

@router.post("/manual-lookup")
async def manual_patient_lookup(request: ManualPatientRequest):
    """
    Handle manual patient entry - lookup existing or create new patient
    """
    try:
        logger.info(f"🔍 Manual patient lookup: {request.name}, {request.mobile}")
        
        # Step 1: Try to find existing patient
        existing_patient = await supabase_service.find_patient_by_name_mobile(
            request.name, request.mobile
        )
        
        if existing_patient:
            logger.info(f"✅ Found existing patient: {existing_patient['patient']['full_name']}")
            
            # Format for frontend
            patient_info = existing_patient["patient"]
            patient_data = {
                "patient_id": str(patient_info.get("onehat_patient_id") or patient_info["uuid"]),
                "patient_uuid": str(patient_info["uuid"]),  # Add UUID for session storage
                "name": patient_info["full_name"],
                "mobile": patient_info["phone_number"],
                "age": patient_info["age"],
                "gender": patient_info["gender"],
                "is_existing": True,
                "has_previous_consultations": existing_patient.get("has_previous_consultations", False),
                "recognition_confidence": None  # No face recognition for manual lookup
            }
            consultation_data = existing_patient.get("last_consultation")
            return {
                "success": True,
                "message": "Patient found in database",
                "patient_data": patient_data,
                "consultation_data": consultation_data
            }
        
        # Step 2: Create new patient if not found
        logger.info(f"🆕 Creating new patient: {request.name}")
        new_patient_data = await supabase_service.create_new_patient(
            request.name, request.mobile, request.age, request.gender
        )
        
        if not new_patient_data:
            raise HTTPException(status_code=500, detail="Failed to create new patient")
        
        patient_info = new_patient_data["patient"]
        
        # Use OneHat ID as patient_id if available, otherwise use UUID
        patient_id = str(patient_info.get("onehat_patient_id") or patient_info["id"])
        
        return {
            "success": True,
            "message": "New patient created successfully",
            "patient_data": {
                "patient_id": patient_id,  # OneHat ID if available, otherwise UUID
                "patient_uuid": str(patient_info["id"]),  # Always UUID for session storage
                "name": patient_info["full_name"],
                "mobile": patient_info["phone_number"],
                "age": patient_info["age"],
                "gender": patient_info["gender"],
                "is_existing": False,
                "has_previous_consultations": False
            },
            "consultation_data": None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error in manual patient lookup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/face-recognition")
async def face_recognition_lookup(image: UploadFile = File(...)):
    """
    Handle face recognition patient lookup using Luxand Cloud API with 0.9 similarity threshold
    """
    try:
        logger.info(f"📸 Luxand face recognition lookup for file: {image.filename}")
        logger.info("🔍 DEBUG: Using LUXAND service for face recognition (patient_router)")
        
        # Validate file type
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Process face recognition
        result = await face_recognition_service.recognize_and_get_patient_details(image)
        
        if not result["success"]:
            return {
                "success": False,
                "message": "User Not Registered. Try again or enter details manually",
                "patient_data": None,
                "consultation_data": None
            }
        
        # Face recognition successful
        return {
            "success": True,
            "message": "Patient recognized successfully",
            "patient_data": {
                "patient_id": str(result["patient_data"]["patient_id"]),
                "patient_uuid": str(result["patient_data"]["patient_uuid"]),  # Add UUID for session storage
                "name": result["patient_data"]["name"],
                "mobile": result["patient_data"]["mobile"],
                "age": result["patient_data"]["age"],
                "gender": result["patient_data"]["gender"],
                "is_existing": True,
                "has_previous_consultations": result.get("has_previous_consultations", False),
                "recognition_confidence": result["recognition_info"]["confidence"]
            },
            "consultation_data": result.get("consultation_data")
        }
        
    except Exception as e:
        logger.error(f"❌ Error in face recognition lookup: {e}")
        raise HTTPException(status_code=500, detail="Face recognition failed")

@router.post("/log-doctor-selection")
async def log_doctor_selection(request: dict):
    """
    Log doctor selection for pre-diagnostics and store in session
    """
    try:
        message = request.get("message", "")
        doctor_name = request.get("doctor_name")
        doctor_id = request.get("doctor_id")
        selection_type = request.get("selection_type", "")
        
        logger.info("=" * 60)
        logger.info(f"🩺 {message}")
        logger.info(f"   - Selection Type: {selection_type}")
        logger.info(f"   - Doctor Name: {doctor_name}")
        logger.info(f"   - Doctor ID: {doctor_id}")
        logger.info("=" * 60)
        
        # Store doctor selection in session for interview routing
        
        # Get session ID from request headers or body
        session_id = request.get("session_id")
        
        if session_id:
            # Get session from database
            session = await get_session(session_id)
            if session:
                # Update session with doctor selection
                session["selected_doctor_choice"] = {
                    "type": selection_type,
                    "doctor_name": doctor_name,
                    "doctor_id": doctor_id
                }
                
                # Update session in database to persist doctor selection
                await update_session(session_id, session)
                
                # Also update in-memory sessions for compatibility
                if session_id in sessions:
                    sessions[session_id]["selected_doctor_choice"] = session["selected_doctor_choice"]
                
                logger.info(f"✅ [SESSION] Stored doctor selection in session {session_id}")
            else:
                logger.warning(f"⚠️ [SESSION] Could not find session in database: {session_id}")
        else:
            logger.warning(f"⚠️ [SESSION] No session_id provided in request")
        
        return {"success": True, "message": "Doctor selection logged"}
        
    except Exception as e:
        logger.error(f"❌ Error logging doctor selection: {e}")
        return {"success": False, "message": "Logging failed"}
