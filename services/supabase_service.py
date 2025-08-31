"""
Supabase Service Module for Medical Pre-Screening Tool

This module handles all Supabase database operations including:
- Connection management
- Patient data retrieval
- Database queries and operations
"""

import os
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseService:
    """Service class to handle Supabase database operations"""
    
    def __init__(self):
        """Initialize Supabase client with service role key"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_service_key:
            raise ValueError("Missing Supabase credentials. Please check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env file")
        
        try:
            # Use the simpler client creation method compatible with v1.0.4
            self.client: Client = create_client(
                supabase_url=self.supabase_url,
                supabase_key=self.supabase_service_key
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    async def get_patient_by_onehat_id(self, onehat_patient_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch patient details by onehat_patient_id
        
        Args:
            onehat_patient_id (int): The OneHat patient ID
            
        Returns:
            Optional[Dict[str, Any]]: Patient data or None if not found
        """
        try:
            logger.info(f"Fetching patient with onehat_patient_id: {onehat_patient_id}")
            
            response = self.client.table("patients").select("*").eq("onehat_patient_id", onehat_patient_id).execute()
            
            if response.data and len(response.data) > 0:
                patient = response.data[0]
                logger.info(f"Patient found: {patient.get('full_name', 'Unknown')}")
                return patient
            else:
                logger.warning(f"No patient found with onehat_patient_id: {onehat_patient_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching patient {onehat_patient_id}: {e}")
            raise

    async def get_patient_with_consultation_details(self, onehat_patient_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive patient details including last consultation information
        
        Args:
            onehat_patient_id (int): The OneHat patient ID
            
        Returns:
            Optional[Dict[str, Any]]: Complete patient data with consultation details or None if not found
        """
        try:
            logger.info(f"Fetching comprehensive patient data for onehat_patient_id: {onehat_patient_id}")
            
            # Step 1: Get patient basic details
            patient_response = self.client.table("patients").select("*").eq("onehat_patient_id", onehat_patient_id).execute()
            
            if not patient_response.data or len(patient_response.data) == 0:
                logger.warning(f"No patient found with onehat_patient_id: {onehat_patient_id}")
                return None
            
            patient = patient_response.data[0]
            patient_uuid = patient["id"]
            
            logger.info(f"📋 Patient Details:")
            logger.info(f"   - UUID: {patient_uuid}")
            logger.info(f"   - Name: {patient.get('full_name', 'Unknown')}")
            logger.info(f"   - Mobile: {patient.get('phone_number', 'N/A')}")
            logger.info(f"   - Age: {patient.get('age', 'N/A')}")
            logger.info(f"   - Gender: {patient.get('gender', 'N/A')}")
            logger.info(f"   - OneHat Patient ID: {patient.get('onehat_patient_id')}")
            
            # Step 2: Get last consultation with doctor details (using left join in case doctor is missing)
            consultation_response = self.client.table("consultations").select(
                "id,consultation_time,raw_pradhi_response,doctor_id,doctors(id,onehat_doctor_id,full_name,specialty)"
            ).eq("patient_id", patient_uuid).order("consultation_time", desc=True).limit(1).execute()
            
            last_consultation = None
            if consultation_response.data and len(consultation_response.data) > 0:
                consultation = consultation_response.data[0]
                doctor_info = consultation.get("doctors", {})
                
                # Debug: Log the raw consultation data to understand the structure
                logger.info(f"🔍 Raw consultation data: {consultation}")
                logger.info(f"🔍 Doctor info structure: {doctor_info}")
                
                last_consultation = {
                    "consultation_id": consultation["id"],
                    "consultation_date": consultation["consultation_time"],
                    "raw_pradhi_response": consultation.get("raw_pradhi_response"),
                    "doctor_uuid": consultation["doctor_id"],
                    "doctor_onehat_id": doctor_info.get("onehat_doctor_id") if doctor_info else None,
                    "doctor_name": doctor_info.get("full_name") if doctor_info else None,
                    "doctor_specialty": doctor_info.get("specialty") if doctor_info else None
                }
                
                logger.info(f"🩺 Last Consultation Details:")
                logger.info(f"   - Consultation ID: {last_consultation['consultation_id']}")
                logger.info(f"   - Date: {last_consultation['consultation_date']}")
                logger.info(f"   - Doctor UUID: {last_consultation['doctor_uuid']}")
                logger.info(f"   - Doctor OneHat ID: {last_consultation['doctor_onehat_id']}")
                logger.info(f"   - Doctor Name: {last_consultation['doctor_name']}")
                logger.info(f"   - Doctor Specialty: {last_consultation['doctor_specialty']}")
                logger.info(f"   - Raw Pradhi Response: {last_consultation['raw_pradhi_response']}")
            else:
                logger.info(f"🔍 No previous consultations found for patient {onehat_patient_id}")
            
            # Combine all data
            comprehensive_data = {
                "patient": {
                    "uuid": patient_uuid,
                    "onehat_patient_id": patient.get("onehat_patient_id"),
                    "full_name": patient.get("full_name"),
                    "phone_number": patient.get("phone_number"),
                    "age": patient.get("age"),
                    "gender": patient.get("gender"),
                    "date_of_birth": patient.get("date_of_birth")
                },
                "last_consultation": last_consultation,
                "has_previous_consultations": last_consultation is not None
            }
            
            return comprehensive_data
                
        except Exception as e:
            logger.error(f"Error fetching comprehensive patient data for {onehat_patient_id}: {e}")
            raise
    
    async def get_all_patients(self) -> List[Dict[str, Any]]:
        """
        Fetch all patients from the database
        
        Returns:
            List[Dict[str, Any]]: List of all patients
        """
        try:
            logger.info("Fetching all patients")
            
            response = self.client.table("patients").select("*").execute()
            
            if response.data:
                logger.info(f"Found {len(response.data)} patients")
                return response.data
            else:
                logger.info("No patients found")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching all patients: {e}")
            raise
    
    async def create_patient(self, patient_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new patient record
        
        Args:
            patient_data (Dict[str, Any]): Patient information
            
        Returns:
            Optional[Dict[str, Any]]: Created patient data
        """
        try:
            logger.info(f"Creating new patient: {patient_data.get('full_name', 'Unknown')}")
            
            response = self.client.table("patients").insert(patient_data).execute()
            
            if response.data and len(response.data) > 0:
                created_patient = response.data[0]
                logger.info(f"Patient created successfully with ID: {created_patient.get('id')}")
                return created_patient
            else:
                logger.error("Failed to create patient")
                return None
                
        except Exception as e:
            logger.error(f"Error creating patient: {e}")
            raise
    
    async def update_patient(self, patient_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing patient record
        
        Args:
            patient_id (str): UUID of the patient
            update_data (Dict[str, Any]): Data to update
            
        Returns:
            Optional[Dict[str, Any]]: Updated patient data
        """
        try:
            logger.info(f"Updating patient: {patient_id}")
            
            response = self.client.table("patients").update(update_data).eq("id", patient_id).execute()
            
            if response.data and len(response.data) > 0:
                updated_patient = response.data[0]
                logger.info(f"Patient updated successfully")
                return updated_patient
            else:
                logger.error("Failed to update patient")
                return None
                
        except Exception as e:
            logger.error(f"Error updating patient {patient_id}: {e}")
            raise
    
    async def get_doctors(self) -> List[Dict[str, Any]]:
        """
        Fetch all doctors from the database
        
        Returns:
            List[Dict[str, Any]]: List of all doctors
        """
        try:
            logger.info("Fetching all doctors")
            
            response = self.client.table("doctors").select("*").execute()
            
            if response.data:
                logger.info(f"Found {len(response.data)} doctors")
                return response.data
            else:
                logger.info("No doctors found")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching doctors: {e}")
            raise
    
    async def get_hospitals(self) -> List[Dict[str, Any]]:
        """
        Fetch all hospitals from the database
        
        Returns:
            List[Dict[str, Any]]: List of all hospitals
        """
        try:
            logger.info("Fetching all hospitals")
            
            response = self.client.table("hospitals").select("*").execute()
            
            if response.data:
                logger.info(f"Found {len(response.data)} hospitals")
                return response.data
            else:
                logger.info("No hospitals found")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching hospitals: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test the Supabase connection
        
        Returns:
            bool: True if connection is successful
        """
        try:
            # Simple query to test connection - use basic select for v1.0.4 compatibility
            response = self.client.table("patients").select("id").limit(1).execute()
            logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            logger.error(f"Error in test_connection: {e}")
            return False

    async def find_patient_by_name_mobile(self, name: str, mobile: str) -> Optional[Dict[str, Any]]:
        """
        Find patient by exact name (case-insensitive) and mobile number
        Returns patient with consultation details if found
        """
        try:
            logger.info(f"🔍 Searching for patient: {name}, Mobile: {mobile}")
            
            # Search for patients with matching name (case-insensitive) and mobile
            response = self.client.table("patients").select("*").ilike("full_name", name).eq("phone_number", mobile).execute()
            
            if not response.data or len(response.data) == 0:
                logger.info(f"❌ No patient found with name: {name}, mobile: {mobile}")
                return None
            
            # Handle multiple matches - prefer onehat_patient_id, then latest
            patients = response.data
            selected_patient = None
            
            if len(patients) == 1:
                selected_patient = patients[0]
            else:
                # Multiple patients found - apply priority logic
                patients_with_onehat = [p for p in patients if p.get('onehat_patient_id') is not None]
                if patients_with_onehat:
                    selected_patient = patients_with_onehat[0]  # Take first with onehat_patient_id
                else:
                    # No onehat_patient_id, take latest by created_at
                    selected_patient = sorted(patients, key=lambda x: x.get('created_at', ''), reverse=True)[0]
                
                logger.info(f"📋 Multiple patients found, selected: {selected_patient.get('id')}")
            
            # Get comprehensive data for selected patient
            if selected_patient.get('onehat_patient_id'):
                return await self.get_patient_with_consultation_details(selected_patient['onehat_patient_id'])
            else:
                # For patients without onehat_patient_id, return basic patient data
                return {
                    "patient": selected_patient,
                    "last_consultation": None,
                    "has_previous_consultations": False
                }
                
        except Exception as e:
            logger.error(f"Error in find_patient_by_name_mobile: {e}")
            return None
    
    async def create_new_patient(self, name: str, mobile: str, age: int, gender: str) -> Optional[Dict[str, Any]]:
        """
        Create a new patient entry in Supabase
        onehat_patient_id will be null, other fields default to null
        """
        try:
            logger.info(f"🆕 Creating new patient: {name}, Mobile: {mobile}")
            
            patient_data = {
                "full_name": name,
                "phone_number": mobile,
                "age": age,
                "gender": gender,
                "onehat_patient_id": None,
                "email": None,
                "address": None,
                "emergency_contact": None
            }
            
            response = self.client.table("patients").insert(patient_data).execute()
            
            if response.data and len(response.data) > 0:
                new_patient = response.data[0]
                logger.info(f"✅ New patient created with UUID: {new_patient['id']}")
                
                return {
                    "patient": new_patient,
                    "last_consultation": None,
                    "has_previous_consultations": False
                }
            else:
                logger.error("❌ Failed to create new patient - no data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error in create_new_patient: {e}")
            return None

    async def create_prescreening_record(self, prescreening_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new pre-screening record in Supabase
        
        Args:
            prescreening_data (Dict[str, Any]): Pre-screening data to store
            
        Returns:
            Optional[Dict[str, Any]]: Created pre-screening record or None if failed
        """
        try:
            logger.info(f"💾 Creating pre-screening record for patient UUID: {prescreening_data.get('patient_uuid')}")
            
            # Prepare data for database insertion
            db_data = {
                "patient_uuid": prescreening_data.get("patient_uuid"),
                "patient_onehat_id": prescreening_data.get("patient_onehat_id"),
                "patient_chosen_doctor_onehat_id": prescreening_data.get("patient_chosen_doctor_onehat_id"),
                "suggested_department": prescreening_data.get("suggested_department"),
                "suggested_doctor_onehat_id": prescreening_data.get("suggested_doctor_onehat_id"),
                "visit_type": prescreening_data.get("type_of_visit"),
                "investigative_history": prescreening_data.get("investigative_history"),
                "possible_diagnosis": prescreening_data.get("possible_diagnosis"),
                "chief_complaint": prescreening_data.get("chief_complaint"),
                "symptoms_mentioned": prescreening_data.get("symptoms_mentioned", []),
                "diagnostics": prescreening_data.get("pre_consultation_diagnostics", {})
            }
            
            response = self.client.table("pre_screening_records").insert(db_data).execute()
            
            if response.data and len(response.data) > 0:
                created_record = response.data[0]
                logger.info(f"✅ Pre-screening record created with ID: {created_record['id']}")
                return created_record
            else:
                logger.error("❌ Failed to create pre-screening record - no data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error in create_prescreening_record: {e}")
            return None

# Global instance
supabase_service = SupabaseService()
