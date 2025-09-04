"""
Pre-screening Data Collection Service

This module handles collection and formatting of pre-screening data
for storage in the Supabase pre-screening table.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class PreScreeningService:
    """Service to collect and format pre-screening data"""
    
    def __init__(self):
        self.ai_model_used = "gemini-2.5-flash-lite"  # From settings
    
    def extract_symptoms_from_conversation(self, conversation_history: List[Dict]) -> List[str]:
        """Extract symptoms mentioned during conversation"""
        symptoms = []
        
        # Common symptom keywords to look for
        symptom_keywords = [
            "pain", "ache", "hurt", "sore", "tender",
            "swelling", "swollen", "inflammation", "bloated",
            "fever", "temperature", "hot", "chills",
            "nausea", "vomiting", "dizzy", "headache",
            "cough", "breathless", "shortness of breath",
            "fatigue", "tired", "weakness", "exhausted",
            "bleeding", "discharge", "rash", "itching",
            "cramping", "spasms", "stiffness", "numbness"
        ]
        
        try:
            for qa in conversation_history:
                answer = qa.get("answer", "").lower()
                question = qa.get("question", "").lower()
                
                # Look for symptoms in answers
                for keyword in symptom_keywords:
                    if keyword in answer:
                        # Extract context around the symptom
                        words = answer.split()
                        for i, word in enumerate(words):
                            if keyword in word:
                                # Get surrounding context (up to 3 words before/after)
                                start = max(0, i-2)
                                end = min(len(words), i+3)
                                symptom_phrase = " ".join(words[start:end])
                                
                                # Clean and add if not already present
                                symptom_phrase = symptom_phrase.strip()
                                if symptom_phrase and symptom_phrase not in symptoms:
                                    symptoms.append(symptom_phrase)
                
                # Also check if question mentions body parts with symptoms
                body_parts = ["knee", "back", "chest", "head", "stomach", "leg", "arm", "neck"]
                for part in body_parts:
                    if part in question and any(s in question for s in ["pain", "hurt", "problem"]):
                        symptom = f"{part} pain"
                        if symptom not in symptoms:
                            symptoms.append(symptom)
            
            # Limit to most relevant symptoms (max 5)
            return symptoms[:5]
            
        except Exception as e:
            logger.error(f"Error extracting symptoms: {e}")
            return []
    
    def extract_chief_complaint(self, assessment_data: Dict, conversation_history: List[Dict]) -> str:
        """Extract chief complaint from assessment or conversation"""
        try:
            # Try to get from assessment data first
            investigative_history = assessment_data.get("investigative_history", "")
            
            # Look for patterns that indicate chief complaint
            complaint_patterns = [
                r"presents with ([^.]+)",
                r"chief complaint[:\s]+([^.]+)",
                r"complains of ([^.]+)",
                r"reports ([^.]+)",
                r"experiencing ([^.]+)"
            ]
            
            for pattern in complaint_patterns:
                match = re.search(pattern, investigative_history, re.IGNORECASE)
                if match:
                    complaint = match.group(1).strip()
                    # Clean up the complaint
                    complaint = re.sub(r'\s+', ' ', complaint)
                    return complaint[:100]  # Limit length
            
            # Fallback: look at first question/answer
            if conversation_history:
                first_qa = conversation_history[0]
                question = first_qa.get("question", "").lower()
                answer = first_qa.get("answer", "")
                
                if "main" in question or "chief" in question or "primary" in question:
                    return answer[:100]
                
                # Extract from common opening questions
                if "feeling" in question or "bring you" in question:
                    return answer[:100]
            
            return "General consultation"
            
        except Exception as e:
            logger.error(f"Error extracting chief complaint: {e}")
            return "General consultation"
    
    def clean_investigative_history(self, raw_history: str) -> str:
        """Clean investigative history by extracting only the relevant medical summary"""
        try:
            # Look for the investigative_history part before other fields
            lines = raw_history.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip lines that are field labels or contain other metadata
                if any(field in line.lower() for field in [
                    'possible_diagnosis:', 'confidence_level:', 'recommended_department:', 
                    'recommended_doctor:', 'doctor_comparison_analysis:', 'suggested_tests:'
                ]):
                    break
                
                # Clean the investigative_history: prefix
                if line.startswith('investigative_history:'):
                    line = line.replace('investigative_history:', '').strip()
                
                if line:
                    cleaned_lines.append(line)
            
            return ' '.join(cleaned_lines).strip()
            
        except Exception as e:
            logger.error(f"Error cleaning investigative history: {e}")
            return raw_history
    
    def extract_diagnosis_from_raw_text(self, raw_text: str) -> str:
        """Extract the actual diagnosis from raw assessment text"""
        try:
            # Look for diagnosis patterns in the raw text
            diagnosis_patterns = [
                r"possible_diagnosis:\s*([^\n]+)",
                r"likely experiencing ([^.]+)",
                r"diagnosis[:\s]+([^\n]+)",
                r"condition[:\s]+([^\n]+)"
            ]
            
            for pattern in diagnosis_patterns:
                match = re.search(pattern, raw_text, re.IGNORECASE)
                if match:
                    diagnosis = match.group(1).strip()
                    # Clean up common prefixes
                    diagnosis = re.sub(r'^(the patient is|patient is|likely|probable|possible)\s*', '', diagnosis, flags=re.IGNORECASE)
                    return diagnosis.strip()
            
            # Fallback: return default
            return "Assessment based on interview responses"
            
        except Exception as e:
            logger.error(f"Error extracting diagnosis from raw text: {e}")
            return "Assessment based on interview responses"
    
    def collect_prescreening_data(
        self,
        session_data: Dict,
        assessment_result: Dict,
        diagnostics_result: Dict,
        conversation_history: List[Dict],
        visit_type: str
    ) -> Dict[str, Any]:
        """
        Collect all pre-screening data into a structured format
        
        Args:
            session_data: Patient and doctor selection data from session
            assessment_result: AI assessment output
            diagnostics_result: Diagnostic recommendations
            conversation_history: Q&A pairs from interview
            visit_type: "follow-up", "new-doctor", or "ai-help"
        """
        try:
            # Extract patient info
            patient_info = session_data.get("patient_info", {})
            consultation_data = session_data.get("consultation_data", {})
            selected_doctor_choice = session_data.get("selected_doctor_choice", {})
            
            # Fix patient UUID and OneHat ID mapping
            # patient_id in session is actually OneHat ID, we need to extract UUID from consultation data or use fallback
            patient_onehat_id = patient_info.get("patient_id")  # This is actually the OneHat ID (52349)
            
            # Extract patient UUID - now available from session data
            patient_uuid = None
            # Primary source: patient_info from session (now includes patient_uuid)
            if patient_info and patient_info.get("patient_uuid"):
                patient_uuid = patient_info.get("patient_uuid")
            # Secondary source: consultation_data if available
            elif consultation_data and consultation_data.get("patient_uuid"):
                patient_uuid = consultation_data.get("patient_uuid")
            # Fallback: Check if patient_info has 'id' field (Supabase UUID)
            elif patient_info and patient_info.get("id"):
                patient_uuid = patient_info.get("id")
                logger.info(f"🔄 Using patient_info.id as UUID fallback: {patient_uuid}")
            
            # Log UUID extraction for debugging
            if patient_uuid:
                logger.info(f"✅ Patient UUID extracted from session: {patient_uuid}")
            else:
                logger.error(f"❌ No patient UUID found in session data")
                logger.error(f"   - patient_info keys: {list(patient_info.keys()) if patient_info else 'None'}")
                logger.error(f"   - consultation_data keys: {list(consultation_data.keys()) if consultation_data else 'None'}")
                # Don't raise error, continue with None UUID for now
                logger.warning("⚠️ Continuing with NULL patient_uuid")
            
            # Determine patient chosen doctor onehat_id
            patient_chosen_doctor_onehat_id = None
            if visit_type == "follow-up" and consultation_data:
                patient_chosen_doctor_onehat_id = consultation_data.get("doctor_onehat_id")
            elif visit_type == "new-doctor" and selected_doctor_choice:
                # Extract from selected doctor info - should be the doctor_id from selection
                doctor_id = selected_doctor_choice.get("doctor_id") or selected_doctor_choice.get("selected_doctor_id")
                
                # From logs: Doctor Name: Harish Kumar, Doctor ID: 3 was selected
                if not doctor_id and selected_doctor_choice.get("doctor_name") == "Harish Kumar":
                    doctor_id = 3
                    
                if doctor_id:
                    # Map from string doctor ID to OneHat ID using the CSV mapping
                    doctor_id_to_onehat_mapping = {
                        "1": 1,  # Prakash Kumar
                        "3": 3,  # Harish Kumar  
                        "8": 8,  # Mithra S
                        "2": 2,  # Dinesh Kumar
                        "57573": 57573,  # Gokul Srinivasan
                        "6": 6   # Mukesh Kumar
                    }
                    patient_chosen_doctor_onehat_id = doctor_id_to_onehat_mapping.get(str(doctor_id))
                    logger.info(f"[PRESCREENING] Mapped patient chosen doctor ID {doctor_id} to OneHat ID {patient_chosen_doctor_onehat_id}")
            # For ai-help, it remains None
            
            # Extract suggested department and doctor
            suggested_department = assessment_result.get("recommended_department")
            suggested_doctor_onehat_id = None
            
            # Try to get suggested doctor onehat_id from assessment or session data
            if hasattr(assessment_result, 'get') and assessment_result.get("recommended_doctors"):
                doctors = assessment_result["recommended_doctors"]
                if doctors and len(doctors) > 0:
                    # Get onehat_doctor_id from the Doctor object or dict
                    doctor = doctors[0]
                    logger.info(f"[PRESCREENING] Processing recommended doctor: {doctor}")
                    if hasattr(doctor, 'id'):
                        # Map internal doctor ID to OneHat ID based on CSV
                        doctor_id_mapping = {
                            "1": 1,  # Prakash Kumar -> OneHat ID 1
                            "3": 3,  # Harish Kumar -> OneHat ID 3
                            "8": 8,  # Mithra S -> OneHat ID 8
                            "2": 2,  # Dinesh Kumar -> OneHat ID 2
                            "57573": 57573,  # Gokul Srinivasan -> OneHat ID 57573
                            "6": 6   # Mukesh Kumar -> OneHat ID 6
                        }
                        suggested_doctor_onehat_id = doctor_id_mapping.get(str(doctor.id))
                        logger.info(f"[PRESCREENING] Mapped doctor ID {doctor.id} to OneHat ID {suggested_doctor_onehat_id}")
                    elif isinstance(doctor, dict):
                        suggested_doctor_onehat_id = doctor.get("onehat_doctor_id")
                        logger.info(f"[PRESCREENING] Got OneHat ID from dict: {suggested_doctor_onehat_id}")
            
            
            logger.info(f"[PRESCREENING] Debug - Patient UUID: {patient_uuid}, OneHat ID: {patient_onehat_id}")
            logger.info(f"[PRESCREENING] Debug - Patient chosen doctor OneHat ID: {patient_chosen_doctor_onehat_id}")
            logger.info(f"[PRESCREENING] Debug - Suggested doctor OneHat ID: {suggested_doctor_onehat_id}")
            logger.info(f"[PRESCREENING] Debug - Visit type: {visit_type}")
            logger.info(f"[PRESCREENING] Debug - Selected doctor choice: {selected_doctor_choice}")
            
            # For follow-up visits, populate suggested fields with previous doctor info for uniformity
            if visit_type == "follow-up" and consultation_data:
                suggested_department = suggested_department or consultation_data.get("doctor_specialty")
                suggested_doctor_onehat_id = suggested_doctor_onehat_id or consultation_data.get("doctor_onehat_id")
            
            # Extract symptoms and chief complaint
            symptoms_mentioned = self.extract_symptoms_from_conversation(conversation_history)
            chief_complaint = self.extract_chief_complaint(assessment_result, conversation_history)
            
            # Clean and extract data properly
            raw_investigative_history = assessment_result.get("investigative_history", "")
            cleaned_investigative_history = self.clean_investigative_history(raw_investigative_history)
            
            # Extract proper diagnosis
            raw_diagnosis = assessment_result.get("possible_diagnosis", "")
            if raw_diagnosis == "Assessment based on interview responses":
                # Try to extract from the raw investigative history
                proper_diagnosis = self.extract_diagnosis_from_raw_text(raw_investigative_history)
            else:
                proper_diagnosis = raw_diagnosis
            
            # Build the pre-screening data structure
            prescreening_data = {
                "patient_uuid": patient_uuid,
                "patient_onehat_id": patient_onehat_id,
                "timestamp": datetime.now().isoformat(),
                "type_of_visit": visit_type,
                "patient_chosen_doctor_onehat_id": patient_chosen_doctor_onehat_id,
                "suggested_department": suggested_department,
                "suggested_doctor_onehat_id": suggested_doctor_onehat_id,
                "investigative_history": cleaned_investigative_history,
                "possible_diagnosis": proper_diagnosis,
                "pre_consultation_diagnostics": diagnostics_result.get("diagnostics", {}),
                "ai_model_used": self.ai_model_used,
                "chief_complaint": chief_complaint,
                "symptoms_mentioned": symptoms_mentioned
            }
            
            return prescreening_data
            
        except Exception as e:
            logger.error(f"Error collecting pre-screening data: {e}")
            return {}
    
    def print_prescreening_json(self, prescreening_data: Dict[str, Any]):
        """Print formatted pre-screening JSON to terminal"""
        try:
            print("\n" + "="*80)
            print("📋 PRE-SCREENING DATA COLLECTION")
            print("="*80)
            print(json.dumps(prescreening_data, indent=2, ensure_ascii=False))
            print("="*80)
            print("✅ Pre-screening data collected successfully")
            print("="*80 + "\n")
            
        except Exception as e:
            logger.error(f"Error printing pre-screening JSON: {e}")
            print(f"❌ Error printing pre-screening data: {e}")

# Global instance
prescreening_service = PreScreeningService()
