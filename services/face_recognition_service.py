"""
Face Recognition Service for Patient Identification
Integrates with CompreFace for face recognition and Supabase patient lookup
"""

import os
import tempfile
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from compreface import CompreFace
from compreface.service import RecognitionService
from dotenv import load_dotenv
from services.supabase_service import supabase_service
import logging

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class FaceRecognitionService:
    def __init__(self):
        self.domain = 'http://localhost'
        self.port = '8000'
        self.api_key = os.getenv('COMPREFACE_API_KEY')
        
        if not self.api_key:
            raise ValueError("COMPREFACE_API_KEY not found in environment variables")
        
        # Initialize CompreFace
        self.compre_face = CompreFace(self.domain, self.port)
        self.recognition = self.compre_face.init_face_recognition(self.api_key)
    
    async def recognize_patient_from_image(self, image_file: UploadFile, confidence_threshold: float = 0.9) -> Optional[Dict[str, Any]]:
        """
        Recognize patient from uploaded image file
        Returns patient_id and confidence if recognized, None otherwise
        """
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                content = await image_file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                # Perform face recognition
                result = self.recognition.recognize(
                    image_path=tmp_file_path,
                    options={
                        "limit": 1,  # Return top match only
                        "det_prob_threshold": 0.8,  # Face detection confidence
                        "prediction_count": 1,
                        "face_plugins": "age,gender",  # Additional info
                        "status": "true"
                    }
                )
                
                if not result.get('result'):
                    return None
                
                faces = result['result']
                if not faces:
                    return None
                
                # Get the first face
                face = faces[0]
                subjects = face.get('subjects', [])
                
                if not subjects:
                    return None
                
                # Get the best match
                best_match = subjects[0]
                onehat_patient_id = best_match['subject']
                similarity = best_match['similarity']
                
                if similarity >= confidence_threshold:
                    return {
                        'onehat_patient_id': int(onehat_patient_id),  # Convert to int for Supabase lookup
                        'confidence': similarity,
                        'face_info': {
                            'age': face.get('age'),
                            'gender': face.get('gender'),
                            'box': face.get('box')
                        }
                    }
                
                return None
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Face recognition failed: {str(e)}")
    
    async def get_patient_details_from_supabase(self, onehat_patient_id: int, face_recognition_result: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive patient details from Supabase based on onehat_patient_id
        Includes patient info and last consultation details
        """
        try:
            logger.info(f"🔍 Fetching patient details from Supabase for OneHat ID: {onehat_patient_id}")
            
            # Get comprehensive patient data including consultation history
            patient_data = await supabase_service.get_patient_with_consultation_details(onehat_patient_id)
            
            if not patient_data:
                logger.warning(f"❌ No patient found in Supabase for OneHat ID: {onehat_patient_id}")
                return None
            
            # Extract patient info for frontend display
            patient_info = patient_data["patient"]
            
            # Use face recognition gender as fallback if database gender is null
            db_gender = patient_info.get("gender")
            detected_gender = None
            
            # Extract gender from face recognition if available
            if face_recognition_result:
                face_gender = face_recognition_result.get('face_info', {}).get('gender', {})
                if face_gender and isinstance(face_gender, dict) and 'value' in face_gender:
                    gender_value = face_gender['value'].lower()
                    if gender_value == 'male':
                        detected_gender = "Male"
                    elif gender_value == 'female':
                        detected_gender = "Female"
            
            # Use database gender if available, otherwise use detected gender, otherwise "Not Specified"
            final_gender = db_gender or detected_gender or "Not Specified"
            
            # Format for frontend consumption (only required fields)
            frontend_patient_data = {
                "patient_id": str(onehat_patient_id),
                "patient_uuid": str(patient_info["id"]),  # Add UUID for session storage
                "name": patient_info.get("full_name", "Unknown"),
                "mobile": patient_info.get("phone_number", "N/A"),
                "age": patient_info.get("age", "N/A"),
                "gender": final_gender
            }
            
            logger.info(f"✅ Patient data prepared for frontend: {frontend_patient_data['name']}")
            
            return {
                "frontend_data": frontend_patient_data,
                "full_data": patient_data  # Complete data for logging/backend use
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching patient details from Supabase: {e}")
            return None
    
    async def recognize_and_get_patient_details(self, image_file: UploadFile) -> Dict[str, Any]:
        """
        Complete workflow: recognize face and return patient details from Supabase
        """
        try:
            logger.info("🎯 Starting face recognition and patient lookup workflow")
            
            # Step 1: Recognize patient from image
            recognition_result = await self.recognize_patient_from_image(image_file)
            
            if not recognition_result:
                logger.warning("❌ Face recognition failed - no match found")
                return {
                    "success": False,
                    "message": "Photo Not Present in Database, please enter your details manually",
                    "patient_data": None,
                    "consultation_data": None
                }
            
            onehat_patient_id = recognition_result['onehat_patient_id']
            confidence = recognition_result['confidence']
            
            logger.info(f"✅ Face recognized - OneHat Patient ID: {onehat_patient_id}, Confidence: {confidence:.2%}")
            
            # Step 2: Get comprehensive patient details from Supabase
            patient_data = await self.get_patient_details_from_supabase(onehat_patient_id, recognition_result)
            
            if not patient_data:
                logger.error(f"❌ Patient ID {onehat_patient_id} recognized but not found in Supabase")
                return {
                    "success": False,
                    "message": f"Patient recognized but details not available in database",
                    "patient_data": None,
                    "consultation_data": None
                }
            
            # Log comprehensive patient data to terminal
            full_data = patient_data["full_data"]
            logger.info("=" * 80)
            logger.info("🎉 PATIENT SUCCESSFULLY RECOGNIZED AND DATA FETCHED")
            logger.info("=" * 80)
            logger.info(f"📸 Face Recognition Results:")
            logger.info(f"   - OneHat Patient ID: {onehat_patient_id}")
            logger.info(f"   - Recognition Confidence: {confidence:.2%}")
            logger.info(f"   - Face Age Detection: {recognition_result['face_info'].get('age', 'N/A')}")
            logger.info(f"   - Face Gender Detection: {recognition_result['face_info'].get('gender', 'N/A')}")
            
            # Patient details are already logged in supabase_service
            # Consultation details are already logged in supabase_service
            
            logger.info("=" * 80)
            logger.info("🚀 Ready to start medical interview with patient data")
            logger.info("=" * 80)
            
            # Add has_previous_consultations to patient_data for frontend
            patient_data_with_flag = patient_data["frontend_data"].copy()
            patient_data_with_flag["has_previous_consultations"] = full_data.get("has_previous_consultations", False)
            
            return {
                "success": True,
                "message": "Patient recognized successfully",
                "patient_data": patient_data_with_flag,  # Frontend-required patient fields with consultation flag
                "consultation_data": full_data.get("last_consultation"),  # Consultation details
                "recognition_info": {
                    "confidence": confidence,
                    "face_info": recognition_result['face_info']
                },
                "onehat_patient_id": onehat_patient_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error in face recognition workflow: {e}")
            return {
                "success": False,
                "message": "Internal error during patient recognition",
                "patient_data": None,
                "consultation_data": None
            }
