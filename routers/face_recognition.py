"""
Face Recognition API Routes
Handles patient identification through facial recognition
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from services.face_recognition_service import FaceRecognitionService
from services.luxand_face_recognition_service import LuxandFaceRecognitionService
from models.patient import FaceRecognitionResult
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Face Recognition"])

# Dependency to get CompreFace recognition service
def get_face_recognition_service():
    return FaceRecognitionService()

# Dependency to get Luxand recognition service
def get_luxand_face_recognition_service():
    return LuxandFaceRecognitionService()

@router.post("/patients/face-recognition", response_model=FaceRecognitionResult)
async def recognize_patient(
    image: UploadFile = File(..., description="Patient's face image"),
    face_service: FaceRecognitionService = Depends(get_face_recognition_service)
):
    """
    Recognize patient from uploaded face image using CompreFace and return patient details
    """
    try:
        logger.info(f"🎯 Face recognition request received - File: {image.filename}")
        logger.info("🔍 DEBUG: Using COMPREFACE service for face recognition")
        
        # Validate image file
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Perform face recognition and get patient details
        result = await face_service.recognize_and_get_patient_details(image)
        
        if result["success"]:
            logger.info(f"✅ Patient recognized successfully via CompreFace")
            return JSONResponse(
                status_code=200,
                content=result
            )
        else:
            logger.warning(f"❌ Face recognition failed via CompreFace: {result['message']}")
            return JSONResponse(
                status_code=404,
                content=result
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in face recognition: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during face recognition")

@router.post("/patients/luxand-face-recognition", response_model=FaceRecognitionResult)
async def recognize_patient_luxand(
    image: UploadFile = File(..., description="Patient's face image"),
    luxand_service: LuxandFaceRecognitionService = Depends(get_luxand_face_recognition_service)
):
    """
    Recognize patient from uploaded face image using Luxand Cloud API and return patient details
    """
    try:
        logger.info(f"🎯 Luxand face recognition request received - File: {image.filename}")
        logger.info("🔍 DEBUG: Using LUXAND service for face recognition")
        
        # Validate image file
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Perform face recognition and get patient details using Luxand
        result = await luxand_service.recognize_and_get_patient_details(image)
        
        if result["success"]:
            logger.info(f"✅ Patient recognized successfully via Luxand")
            return JSONResponse(
                status_code=200,
                content=result
            )
        else:
            logger.warning(f"❌ Luxand face recognition failed: {result['message']}")
            return JSONResponse(
                status_code=404,
                content=result
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in Luxand face recognition: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during Luxand face recognition")

@router.post("/patients/luxand-add-face")
async def add_patient_face_luxand(
    onehat_patient_id: int,
    image: UploadFile = File(..., description="Patient's face image for enrollment"),
    collections: str = "VHR",
    luxand_service: LuxandFaceRecognitionService = Depends(get_luxand_face_recognition_service)
):
    """
    Add patient face to Luxand database for future recognition
    """
    try:
        logger.info(f"🎯 Adding patient face to Luxand - OneHat ID: {onehat_patient_id}")
        
        # Validate image file
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Add patient face to Luxand
        result = await luxand_service.add_patient_face(onehat_patient_id, image, collections)
        
        if result["success"]:
            logger.info(f"✅ Patient face added to Luxand successfully")
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Face added successfully for patient {onehat_patient_id}",
                    "luxand_uuid": result["uuid"]
                }
            )
        else:
            logger.error(f"❌ Failed to add patient face to Luxand: {result['message']}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": f"Failed to add face: {result['message']}"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error adding face to Luxand: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during face enrollment")

# Legacy test endpoint removed - functionality integrated into main face recognition endpoint

@router.get("/patient-details/{patient_id}")
async def get_patient_details(
    patient_id: str,
    face_service: FaceRecognitionService = Depends(get_face_recognition_service)
):
    """
    Get patient details by patient ID (for testing)
    """
    patient_details = face_service.get_patient_details(patient_id)
    
    if not patient_details:
        raise HTTPException(status_code=404, detail=f"Patient with ID {patient_id} not found")
    
    return {
        "success": True,
        "patient": patient_details
    }
