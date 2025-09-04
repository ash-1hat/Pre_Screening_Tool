"""
Follow-up Service - Handles follow-up interviews and assessments for returning patients
"""

import os
import warnings
from google import genai
from google.genai import types
from typing import Dict, List, Optional
from datetime import datetime
import json
from pydantic import BaseModel

from models.patient import PatientInfo
from models.medical import QuestionAnswer, InterviewSession
from models.assessment import InvestigativeResult
from core.config import settings

# Suppress Pydantic field shadowing warnings from google-genai package
warnings.filterwarnings("ignore", message="Field name .* shadows an attribute in parent", category=UserWarning)

class FollowupQuestionResponse(BaseModel):
    question: str

class FollowupAssessmentResponse(BaseModel):
    investigative_history: str
    possible_diagnosis: str

class FollowupService:
    def __init__(self):
        # Initialize Gemini client
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        
        # Load follow-up prompts
        self.prompts = self._load_followup_prompts()
        
    def _load_followup_prompts(self) -> dict:
        """Load follow-up prompts from JSON file"""
        try:
            prompts_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'followup_service_prompts.json')
            with open(prompts_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading follow-up prompts: {e}")
            return {}
    
    def generate_followup_question(
        self,
        patient_age: int,
        patient_gender: str,
        doctor_department: str,
        last_consultation_date: str,
        previous_medical_record: str,
        question_number: int,
        conversation_history: str
    ) -> str:
        """
        Generate next follow-up question based on patient context and conversation history
        """
        try:
            print(f"[FOLLOWUP_DEBUG] Starting question generation for question {question_number}")
            print(f"[FOLLOWUP_DEBUG] Patient: {patient_age}y {patient_gender}, Dept: {doctor_department}")
            print(f"[FOLLOWUP_DEBUG] Conversation history length: {len(conversation_history)}")
            
            # Add timeout protection for Gemini API calls
            import asyncio
            import signal
            
            # Fallback question in case of API issues
            fallback_questions = [
                "How have you been feeling since your last visit?",
                "Are you taking your prescribed medications as directed?",
                "Have you noticed any changes in your condition?",
                "Are you experiencing any new symptoms?",
                "How has your treatment been working for you?",
                "Is there anything specific that's been bothering you?"
            ]
            
            # Determine current section based on question number (now 6 total)
            current_section = "Treatment Adherence" if question_number <= 3 else "Condition Assessment"
            
            # Get prompts
            system_prompt = self.prompts.get("System Instructions for Follow-up Interview", "")
            user_prompt = self.prompts.get("User Instructions for Follow-up Interview", "")
            
            # Format user prompt with patient data
            formatted_user_prompt = user_prompt.format(
                patient_age=patient_age,
                patient_gender=patient_gender,
                doctor_department=doctor_department,
                last_consultation_date=last_consultation_date,
                previous_medical_record=previous_medical_record,
                question_number=question_number,
                current_section=current_section,
                conversation_history=conversation_history
            )
            
            # Add language instruction based on question number
            if question_number == 1:
                formatted_user_prompt += "\n\nIMPORTANT: Respond in Tamil."
            else:
                formatted_user_prompt += "\n\nIMPORTANT: Look at the patient's most recent answer in the conversation history. Respond in the same language the patient used in their last answer."
            
            print(f"[FOLLOWUP_DEBUG] Calling Gemini API for question generation")
            
            # Generate question using Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=f"{system_prompt}\n\n{formatted_user_prompt}")
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                    response_schema=FollowupQuestionResponse,
                    response_mime_type="application/json"
                )
            )
            
            if response and response.text:
                try:
                    # Try direct JSON parsing
                    question_data = json.loads(response.text)
                    generated_question = question_data.get("question", "")
                    
                    # Check if AI wants to end interview early
                    if "INTERVIEW_COMPLETE" in generated_question:
                        return "INTERVIEW_COMPLETE"
                        
                    return generated_question or "Can you tell me more about your current condition?"
                    
                except json.JSONDecodeError as e:
                    print(f"[FOLLOWUP_DEBUG] JSON parse error: {e}, raw response: {response.text[:200]}")
                    # Try to extract question from markdown or plain text
                    import re
                    question_match = re.search(r'"question":\s*"([^"]+)"', response.text)
                    if question_match:
                        return question_match.group(1)
                    
                    # Use response as question if it seems reasonable
                    if response.text and len(response.text.strip()) < 200:
                        return response.text.strip()
            
            # Use fallback if no response
            print(f"[FOLLOWUP_DEBUG] No response from Gemini API, using fallback")
            return fallback_questions[min(question_number - 1, len(fallback_questions) - 1)]
            
        except Exception as e:
            print(f"[FOLLOWUP_DEBUG] Error generating follow-up question: {e}")
            import traceback
            traceback.print_exc()
            return fallback_questions[min(question_number - 1, len(fallback_questions) - 1)]
    
    def _generate_alternative_question(self, question_number: int, conversation_history: str) -> str:
        """Generate alternative questions when AI fails or repeats"""
        # Detect language from conversation history
        patient_using_english = False
        if conversation_history:
            # Look for patient answers (A1, A2, etc.)
            lines = conversation_history.split('\n')
            for line in lines:
                if line.strip().startswith('A') and ':' in line:
                    answer = line.split(':', 1)[1].strip()
                    # Simple check: if answer contains English alphabet without Tamil script
                    has_english = any(c.isascii() and c.isalpha() for c in answer)
                    has_tamil = any('\u0b80' <= c <= '\u0bff' for c in answer)
                    if has_english and not has_tamil:
                        patient_using_english = True
                        break
        
        # Analyze what has been asked already
        asked_about_medications = "medic" in conversation_history.lower()
        asked_about_feelings = "feel" in conversation_history.lower() or "how are" in conversation_history.lower()
        asked_about_symptoms = "symptom" in conversation_history.lower()
        asked_about_activities = "activit" in conversation_history.lower() or "exercise" in conversation_history.lower()
        
        # Generate unique questions based on what hasn't been covered and language preference
        if patient_using_english:
            alternative_questions = [
                "Have you been taking your prescribed medications as directed?",
                "Are you experiencing any pain or discomfort currently?", 
                "Have you noticed any changes in your condition since the last visit?",
                "Are you following any specific dietary or activity restrictions?",
                "Have you completed any recommended tests or follow-up procedures?",
                "Is there anything specific that's been bothering you lately?"
            ]
        else:
            alternative_questions = [
                "நீங்கள் பரிந்துரைக்கப்பட்ட மருந்துகளை தவறாமல் எடுத்துக்கொள்கிறீர்களா?",
                "தற்போது உங்களுக்கு ஏதேனும் வலி அல்லது அசௌகரியம் இருக்கிறதா?",
                "கடைசி வருகைக்குப் பிறகு உங்கள் நிலையில் ஏதேனும் மாற்றங்கள் கவனித்தீர்களா?",
                "நீங்கள் ஏதேனும் குறிப்பிட்ட உணவு அல்லது செயல்பாட்டு கட்டுப்பாடுகளை பின்பற்றுகிறீர்களா?",
                "பரிந்துரைக்கப்பட்ட பரிசோதனைகள் அல்லது பின்தொடர்தல் நடைமுறைகளை நீங்கள் முடித்துவிட்டீர்களா?",
                "உங்களை குறிப்பாக தொந்தரவு செய்யும் ஏதாவது இருக்கிறதா?"
            ]
        
        # Filter out questions similar to what's already been asked
        available_questions = []
        for q in alternative_questions:
            q_lower = q.lower()
            if (not asked_about_medications or "medic" not in q_lower) and \
               (not asked_about_feelings or ("feel" not in q_lower and "how are" not in q_lower)) and \
               (not asked_about_symptoms or "symptom" not in q_lower and "pain" not in q_lower) and \
               (not asked_about_activities or ("activit" not in q_lower and "exercise" not in q_lower)):
                available_questions.append(q)
        
        # Return the first available unique question or a generic one
        if available_questions:
            return available_questions[0]
        
        # Final fallback based on question number and language
        if patient_using_english:
            if question_number <= 3:
                return "Can you tell me about your current treatment plan?"
            else:
                return "Is there anything else you'd like to discuss about your condition?"
        else:
            if question_number <= 3:
                return "உங்கள் தற்போதைய சிகிச்சை திட்டத்தைப் பற்றி சொல்ல முடியுமா?"
            else:
                return "உங்கள் நிலையைப் பற்றி வேறு ஏதாவது விவாதிக்க விரும்புகிறீர்களா?"
    
    def generate_followup_assessment(
        self,
        patient_age: int,
        patient_gender: str,
        chief_complaint: str,
        previous_visit_summary: str,
        follow_up_interview: str
    ) -> Dict:
        """
        Generate comprehensive follow-up assessment based on interview data
        """
        try:
            # Get prompts
            system_prompt = self.prompts.get("System Instructions for Follow-up Assessment", "")
            user_prompt = self.prompts.get("User Instructions for Follow-up Assessment", "")
            
            # Format user prompt with patient data
            formatted_user_prompt = user_prompt.format(
                patient_age=patient_age,
                patient_gender=patient_gender,
                chief_complaint=chief_complaint,
                previous_visit_summary=previous_visit_summary,
                follow_up_interview=follow_up_interview
            )
            
            # Generate assessment using Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=f"{system_prompt}\n\n{formatted_user_prompt}")
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2000
                )
            )
            
            if response and response.text:
                try:
                    # Try to parse as JSON first
                    assessment_data = json.loads(response.text)
                    return {
                        "investigative_history": assessment_data.get("investigative_history", ""),
                        "possible_diagnosis": assessment_data.get("possible_diagnosis", "")
                    }
                except json.JSONDecodeError:
                    # If not JSON, treat as plain text and structure it
                    return {
                        "investigative_history": response.text,
                        "possible_diagnosis": "Assessment based on follow-up interview responses"
                    }
            
            return self._generate_fallback_assessment()
            
        except Exception as e:
            print(f"Error generating follow-up assessment: {e}")
            return self._generate_fallback_assessment()
    
    def _generate_fallback_assessment(self) -> Dict:
        """Generate a basic fallback assessment structure"""
        return {
            "investigative_history": "Follow-up interview completed. Patient provided responses regarding treatment adherence and symptom progression.",
            "possible_diagnosis": "Assessment based on follow-up interview responses"
        }
    
    def conduct_followup_interview(
        self,
        patient_age: int,
        patient_gender: str,
        doctor_department: str,
        last_consultation_date: str,
        previous_medical_record: str
    ) -> Dict:
        """
        Conduct a complete 6-question follow-up interview with early stopping capability
        """
        interview_data = {
            "questions_and_answers": [],
            "conversation_history": "",
            "completed": False
        }
        
        try:
            # Generate up to 6 questions with early stopping capability
            for question_num in range(1, 7):
                question = self.generate_followup_question(
                    patient_age=patient_age,
                    patient_gender=patient_gender,
                    doctor_department=doctor_department,
                    last_consultation_date=last_consultation_date,
                    previous_medical_record=previous_medical_record,
                    question_number=question_num,
                    conversation_history=interview_data["conversation_history"]
                )
                
                # Check if AI wants to stop early (indicated by specific response)
                if "INTERVIEW_COMPLETE" in question or question_num >= 6:
                    interview_data["early_completion"] = True
                    break
                    
                interview_data["questions_and_answers"].append({
                    "question_number": question_num,
                    "question": question,
                    "answer": "",  # To be filled by frontend
                    "section": "Treatment Adherence" if question_num <= 3 else "Condition Assessment"
                })
            
            interview_data["completed"] = True
            return interview_data
            
        except Exception as e:
            print(f"Error conducting follow-up interview: {e}")
            return interview_data

# Create service instance
followup_service = FollowupService()
