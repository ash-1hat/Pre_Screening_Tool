"""
Supabase Router for Medical Pre-Screening Tool API

This router handles all Supabase-related API endpoints including:
- Patient data retrieval
- Database health checks
- Patient management operations
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

from services.supabase_service import supabase_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/supabase", tags=["supabase"])

class PatientResponse(BaseModel):
    """Response model for patient data"""
    id: str
    onehat_patient_id: int
    full_name: str
    phone_number: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None

class PatientCreateRequest(BaseModel):
    """Request model for creating a new patient"""
    onehat_patient_id: int
    full_name: str
    phone_number: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None

@router.get("/health")
async def check_supabase_health():
    """Check Supabase connection health"""
    try:
        is_healthy = supabase_service.test_connection()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "message": "Supabase connection is working" if is_healthy else "Supabase connection failed"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/patient/{onehat_patient_id}")
async def get_patient_by_onehat_id(onehat_patient_id: int):
    """
    Get patient details by OneHat Patient ID
    
    Args:
        onehat_patient_id (int): The OneHat patient ID
        
    Returns:
        PatientResponse: Patient details
    """
    try:
        logger.info(f"API request to fetch patient with onehat_patient_id: {onehat_patient_id}")
        
        patient = await supabase_service.get_patient_by_onehat_id(onehat_patient_id)
        
        if not patient:
            raise HTTPException(
                status_code=404, 
                detail=f"Patient not found with onehat_patient_id: {onehat_patient_id}"
            )
        
        return {
            "success": True,
            "data": patient,
            "message": f"Patient found: {patient.get('full_name', 'Unknown')}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching patient {onehat_patient_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patients")
async def get_all_patients():
    """
    Get all patients from the database
    
    Returns:
        List[PatientResponse]: List of all patients
    """
    try:
        logger.info("API request to fetch all patients")
        
        patients = await supabase_service.get_all_patients()
        
        return {
            "success": True,
            "data": patients,
            "count": len(patients),
            "message": f"Found {len(patients)} patients"
        }
        
    except Exception as e:
        logger.error(f"Error fetching all patients: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/patient")
async def create_patient(patient_data: PatientCreateRequest):
    """
    Create a new patient record
    
    Args:
        patient_data (PatientCreateRequest): Patient information
        
    Returns:
        PatientResponse: Created patient details
    """
    try:
        logger.info(f"API request to create patient: {patient_data.full_name}")
        
        # Convert Pydantic model to dict
        patient_dict = patient_data.model_dump(exclude_unset=True)
        
        created_patient = await supabase_service.create_patient(patient_dict)
        
        if not created_patient:
            raise HTTPException(status_code=400, detail="Failed to create patient")
        
        return {
            "success": True,
            "data": created_patient,
            "message": f"Patient created successfully: {created_patient.get('full_name', 'Unknown')}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating patient: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/doctors")
async def get_all_doctors():
    """
    Get all doctors from the database
    
    Returns:
        List[Dict]: List of all doctors
    """
    try:
        logger.info("API request to fetch all doctors")
        
        doctors = await supabase_service.get_doctors()
        
        return {
            "success": True,
            "data": doctors,
            "count": len(doctors),
            "message": f"Found {len(doctors)} doctors"
        }
        
    except Exception as e:
        logger.error(f"Error fetching doctors: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/hospitals")
async def get_all_hospitals():
    """
    Get all hospitals from the database
    
    Returns:
        List[Dict]: List of all hospitals
    """
    try:
        logger.info("API request to fetch all hospitals")
        
        hospitals = await supabase_service.get_hospitals()
        
        return {
            "success": True,
            "data": hospitals,
            "count": len(hospitals),
            "message": f"Found {len(hospitals)} hospitals"
        }
        
    except Exception as e:
        logger.error(f"Error fetching hospitals: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Legacy test endpoint removed - use general patient endpoints instead
