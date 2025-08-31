"""
Luxand Face Recognition Service for Patient Identification
Integrates with Luxand Cloud API for face recognition and Supabase patient lookup
"""

import os
import tempfile
import requests
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv
from services.supabase_service import supabase_service
import logging

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class LuxandFaceRecognitionService:
    def __init__(self):
        self.base_url = 'https://api.luxand.cloud'
        self.api_key = os.getenv('LUXAND_API_KEY')
        
        if not self.api_key:
            raise ValueError("LUXAND_API_KEY not found in environment variables")
        
        self.headers = {'token': self.api_key}
        logger.info("✅ Luxand Face Recognition Service initialized")
    
    async def add_patient_face(self, onehat_patient_id: int, image_file: UploadFile, collections: str = "VHR") -> Dict[str, Any]:
        """
        Add patient face to Luxand database using onehat_patient_id as name
        """
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                content = await image_file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                url = f"{self.base_url}/v2/person"
                
                # Use onehat_patient_id as name for Luxand
                data = {
                    "name": str(onehat_patient_id),
                    "store": "1",
                    "collections": collections
                }
                
                files = {"photos": open(tmp_file_path, "rb")}
                
                response = requests.post(url, headers=self.headers, data=data, files=files, timeout=30)
                files["photos"].close()
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Added patient face to Luxand - OneHat ID: {onehat_patient_id}, UUID: {result['uuid']}")
                    return {"success": True, "uuid": result["uuid"], "data": result}
                else:
                    logger.error(f"❌ Failed to add patient face to Luxand: {response.text}")
                    return {"success": False, "message": response.text}
                    
            finally:
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"❌ Error adding patient face to Luxand: {e}")
            return {"success": False, "message": str(e)}
    
    async def recognize_patient_from_image(self, image_file: UploadFile, confidence_threshold: float = 0.9) -> Optional[Dict[str, Any]]:
        """
        Recognize patient from uploaded image file using Luxand API
        Returns onehat_patient_id and confidence if recognized, None otherwise
        """
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                content = await image_file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                url = f"{self.base_url}/photo/search/v2"
                files = {"photo": open(tmp_file_path, "rb")}
                
                response = requests.post(url, headers=self.headers, files=files, timeout=30)
                files["photo"].close()
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Parse Luxand response - it returns a list of matches
                    if not result or len(result) == 0:
                        logger.info("❌ No face matches found in Luxand database")
                        return None
                    
                    # Get the best match (first result is highest confidence)
                    best_match = result[0]
                    onehat_patient_id = best_match['name']  # onehat_id stored as name
                    probability = best_match['probability']
                    
                    logger.info(f"🎯 Luxand recognition result - OneHat ID: {onehat_patient_id}, Probability: {probability:.4f}")
                    
                    if probability >= confidence_threshold:
                        return {
                            'onehat_patient_id': int(onehat_patient_id),  # Convert to int for Supabase lookup
                            'confidence': probability,
                            'face_info': {
                                'uuid': best_match.get('uuid'),
                                'rectangle': best_match.get('rectangle'),
                                'collections': best_match.get('collections', [])
                            }
                        }
                    else:
                        logger.info(f"❌ Recognition confidence {probability:.4f} below threshold {confidence_threshold}")
                        return None
                        
                else:
                    logger.error(f"❌ Luxand recognition failed: {response.text}")
                    return None
                    
            finally:
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"❌ Face recognition failed: {e}")
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
            
            # Format for frontend consumption (only required fields)
            frontend_patient_data = {
                "patient_id": str(onehat_patient_id),
                "name": patient_info.get("full_name", "Unknown"),
                "mobile": patient_info.get("phone_number", "N/A"),
                "age": patient_info.get("age", "N/A"),
                "gender": patient_info.get("gender", "Not Specified")
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
        Complete workflow: recognize face using Luxand and return patient details from Supabase
        """
        try:
            logger.info("🎯 Starting Luxand face recognition and patient lookup workflow")
            
            # Step 1: Recognize patient from image using Luxand
            recognition_result = await self.recognize_patient_from_image(image_file)
            
            if not recognition_result:
                logger.warning("❌ Luxand face recognition failed - no match found")
                return {
                    "success": False,
                    "message": "Photo Not Present in Database, please enter your details manually",
                    "patient_data": None,
                    "consultation_data": None
                }
            
            onehat_patient_id = recognition_result['onehat_patient_id']
            confidence = recognition_result['confidence']
            
            logger.info(f"✅ Face recognized via Luxand - OneHat Patient ID: {onehat_patient_id}, Confidence: {confidence:.2%}")
            
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
            logger.info("🎉 PATIENT SUCCESSFULLY RECOGNIZED VIA LUXAND AND DATA FETCHED")
            logger.info("=" * 80)
            logger.info(f"📸 Luxand Face Recognition Results:")
            logger.info(f"   - OneHat Patient ID: {onehat_patient_id}")
            logger.info(f"   - Recognition Confidence: {confidence:.2%}")
            logger.info(f"   - Luxand UUID: {recognition_result['face_info'].get('uuid', 'N/A')}")
            logger.info(f"   - Collections: {recognition_result['face_info'].get('collections', 'N/A')}")
            
            logger.info("=" * 80)
            logger.info("🚀 Ready to start medical interview with patient data")
            logger.info("=" * 80)
            
            # Add has_previous_consultations to patient_data for frontend
            patient_data_with_flag = patient_data["frontend_data"].copy()
            patient_data_with_flag["has_previous_consultations"] = full_data.get("has_previous_consultations", False)
            
            return {
                "success": True,
                "message": "Patient recognized successfully via Luxand",
                "patient_data": patient_data_with_flag,  # Frontend-required patient fields with consultation flag
                "consultation_data": full_data.get("last_consultation"),  # Consultation details
                "recognition_info": {
                    "confidence": confidence,
                    "face_info": recognition_result['face_info'],
                    "service": "luxand"
                },
                "onehat_patient_id": onehat_patient_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error in Luxand face recognition workflow: {e}")
            return {
                "success": False,
                "message": "Internal error during patient recognition",
                "patient_data": None,
                "consultation_data": None
            }
