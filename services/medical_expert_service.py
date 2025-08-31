"""
Medical Expert AI Service - Core logic for medical interviews
"""

import os
import warnings
from google import genai
from google.genai import types
from typing import Dict, List, Optional
from datetime import datetime

from models.patient import PatientInfo
from models.medical import QuestionAnswer, InterviewSession
from models.assessment import InvestigativeResult
from core.config import settings
from services.department_service import department_service
from services.diagnostics_service import diagnostics_service
import json
from pydantic import BaseModel

# Suppress Pydantic field shadowing warnings from google-genai package
warnings.filterwarnings("ignore", message="Field name .* shadows an attribute in parent", category=UserWarning)

class QuestionResponse(BaseModel):
    question: str

class AssessmentResponse(BaseModel):
    summary: str
    severity_level: str
    recommended_department: str
    recommended_doctor: str
    key_findings: List[str]
    next_steps: List[str]

class MedicalExpertService:
    def __init__(self):
        # Initialize Gemini client
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        
        # Load optimized prompts
        self.prompts = self._load_optimized_prompts()
        
    def _load_optimized_prompts(self) -> dict:
        """Load optimized prompts from JSON file"""
        try:
            prompts_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'optimized_prompts_fixed.json')
            with open(prompts_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading optimized prompts: {e}")
            return {}
    
    def get_medical_expert_system_instruction(self, patient: dict) -> str:
        """Generate system instruction for Medical Expert LLM using optimized prompts"""
        system_prompt = self.prompts.get('System Instructions for Interview', '')
        return system_prompt

    async def generate_next_question(self, patient: dict, conversation_history: List[Dict], 
                                   question_number: int, unknown_count: int, previous_response_id: str = None) -> Dict:
        """Generate next medical question based on conversation context"""
        
        print(f"[AI_DEBUG] Generating question {question_number} for patient {patient.get('name', 'Unknown')}")
        print(f"[AI_DEBUG] Conversation history length: {len(conversation_history)}")
        print(f"[AI_DEBUG] Unknown count: {unknown_count}")
        print(f"[AI_DEBUG] Previous response ID: {previous_response_id}")
        
        try:
            # Format conversation history
            history_text = ""
            for i, exchange in enumerate(conversation_history, 1):
                history_text += f"Q{i}: {exchange['question']}\nA{i}: {exchange['answer']}\n\n"
            
            # Use optimized user prompt template
            user_prompt_template = self.prompts.get('user instructions for interview', '')
            
            # Debug: Check if prompts are loaded correctly
            print(f"[AI_DEBUG] System prompt loaded: {len(self.prompts.get('System Instructions for Interview', ''))}")
            print(f"[AI_DEBUG] User prompt loaded: {len(user_prompt_template)}")
            
            if not user_prompt_template:
                # Fallback if prompt loading fails
                question_input = f"""Generate the next medical question for patient (Question {question_number}/6).
                
Patient Context: {patient['age']}y, {patient['gender']}
Conversation History: {history_text if history_text else "No previous questions - start with chief complaint"}

Instructions: Ask ONE focused medical question. If this is question 1, ask about their main complaint."""
            else:
                question_input = user_prompt_template.format(
                    patient_name=patient['name'],
                    patient_age=patient['age'],
                    patient_gender=patient['gender'],
                    chosen_doctor=patient.get('chosen_doctor', 'Not specified'),
                    chosen_department=patient.get('chosen_department', 'Not specified'),
                    question_number=question_number,
                    unknown_count=unknown_count,
                    conversation_history=history_text if history_text else "No previous questions - start with chief complaint"
                )
            
            # Get system instruction and debug it
            system_instruction = self.get_medical_expert_system_instruction(patient)
            print(f"[AI_DEBUG] System instruction length: {len(system_instruction)}")
            print(f"[AI_DEBUG] System instruction preview: {system_instruction[:200]}...")
            print(f"[AI_DEBUG] User prompt: {question_input}")
            print(f"[AI_DEBUG] Making Gemini API call with model: {self.model}")
            
            # Use Gemini with system instruction and user prompt
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=question_input)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=500,  # Increased to accommodate reasoning tokens
                    temperature=0.7
                )
            )
            
            # Check if response and response.text are valid
            if not response or not response.text:
                print(f"[AI_DEBUG] Empty or invalid response from Gemini API")
                print(f"[AI_DEBUG] Response object: {response}")
                if response:
                    print(f"[AI_DEBUG] Response text: {response.text}")
                raise Exception("Empty response from Gemini API")
            
            question_text = response.text.strip()
            print(f"[AI_DEBUG] Generated question: {question_text}")
            
            # Parse JSON response if it contains structured data
            try:
                if question_text.startswith('```json'):
                    # Extract JSON from code block
                    json_start = question_text.find('{')
                    json_end = question_text.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = question_text[json_start:json_end]
                        parsed_response = json.loads(json_str)
                        if 'question' in parsed_response:
                            question_text = parsed_response['question']
                            print(f"[AI_DEBUG] Extracted question: {question_text}")
                elif question_text.startswith('{') and question_text.endswith('}'):
                    # Direct JSON response
                    parsed_response = json.loads(question_text)
                    if 'question' in parsed_response:
                        question_text = parsed_response['question']
                        print(f"[AI_DEBUG] Extracted question: {question_text}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[AI_DEBUG] Could not parse JSON response, using raw text: {e}")
                # Keep the original response if parsing fails
            
            return {
                "question": question_text,
                "response_id": None,  # Gemini doesn't use response IDs like OpenAI
                "reasoning_tokens": 0  # Not available in Gemini API
            }
            
        except Exception as e:
            print(f"[AI_DEBUG] Error generating question: {e}")
            import traceback
            traceback.print_exc()
            return {
                "question": "Could you please tell me about your main health concern today?",
                "response_id": None,
                "reasoning_tokens": 0
            }

    async def generate_final_assessment(self, patient: dict, conversation_history: List[Dict], 
                                      previous_response_id: str = None) -> Optional[Dict]:
        """Generate final medical assessment using Responses API with structured outputs"""
        
        try:
            # Format complete conversation
            history_text = ""
            for i, exchange in enumerate(conversation_history, 1):
                history_text += f"Q{i}: {exchange['question']}\nA{i}: {exchange['answer']}\n\n"
            
            # Use optimized user prompt template for assessment
            user_assessment_template = self.prompts.get('user instructions for assessment', '')
            assessment_input = user_assessment_template.format(
                patient_name=patient['name'],
                patient_age=patient['age'],
                patient_gender=patient['gender'],
                chosen_doctor=patient.get('chosen_doctor', 'Not specified'),
                chosen_department=patient.get('chosen_department', 'Not specified'),
                conversation_history=history_text,
                doctors_list="Available doctors list not provided"  # This would need to be passed from the calling function
            )
            
            # Define the assessment schema for structured output
            class MedicalAssessment(BaseModel):
                investigative_history: str
                possible_diagnosis: str
                confidence_level: int
                recommended_department: str
                recommended_doctor: str
                doctor_comparison_analysis: str
            
            # Get system instruction for assessment
            assessment_system_prompt = self.prompts.get('sytem instructions for assessment', '')
            
            # Use Gemini with structured JSON output
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=assessment_input)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=assessment_system_prompt,
                    max_output_tokens=2000,  # Increased for assessment generation
                    temperature=0.3
                )
            )
            
            # Parse structured output with fallback handling
            print(f"[ASSESSMENT_DEBUG] Raw Gemini response text: {response.text[:500]}...")
            
            # Initialize default assessment data - avoid hardcoded department fallbacks
            assessment_data = {
                "investigative_history": response.text,
                "possible_diagnosis": "Assessment based on interview responses", 
                "confidence_level": 70,
                "recommended_department": None,  # Will be extracted from AI response
                "recommended_doctor": None,      # Will be extracted from AI response  
                "doctor_comparison_analysis": "Based on symptoms and patient responses"
            }
            
            # Try different parsing strategies
            import re
            
            # Strategy 1: Direct JSON parsing (if response is clean JSON)
            try:
                parsed_json = json.loads(response.text)
                assessment_data = parsed_json
                print(f"[ASSESSMENT_DEBUG] ✅ Direct JSON parse successful: {list(assessment_data.keys())}")
            except json.JSONDecodeError:
                print(f"[ASSESSMENT_DEBUG] ❌ Direct JSON parse failed, trying markdown extraction")
                
                # Strategy 2: Extract JSON from markdown code blocks
                json_match = re.search(r'```json\s*({.*?})\s*```', response.text, re.DOTALL)
                if json_match:
                    print(f"[ASSESSMENT_DEBUG] 🔍 Found JSON in markdown block")
                    try:
                        markdown_json = json.loads(json_match.group(1))
                        assessment_data = markdown_json
                        print(f"[ASSESSMENT_DEBUG] ✅ Markdown JSON parse successful")
                        print(f"[ASSESSMENT_DEBUG] 🎯 Extracted recommended_department: {assessment_data.get('recommended_department')}")
                    except json.JSONDecodeError as e:
                        print(f"[ASSESSMENT_DEBUG] ❌ Markdown JSON parse failed: {e}")
                else:
                    print(f"[ASSESSMENT_DEBUG] ❌ No markdown JSON block found")
            
            # Ensure we have investigative_history as clean text
            if isinstance(assessment_data.get("investigative_history"), str) and assessment_data["investigative_history"].startswith("```json"):
                # Clean up investigative_history if it contains the full markdown response
                clean_history = assessment_data.get("investigative_history", "Assessment summary")
                json_match = re.search(r'"investigative_history":\s*"([^"]*)"', assessment_data["investigative_history"])
                if json_match:
                    clean_history = json_match.group(1)
                assessment_data["investigative_history"] = clean_history
                print(f"[ASSESSMENT_DEBUG] 🧹 Cleaned investigative_history")
            
            print(f"[ASSESSMENT_DEBUG] 📊 Final parsing result:")
            print(f"[ASSESSMENT_DEBUG]   - recommended_department: {assessment_data.get('recommended_department')}")
            print(f"[ASSESSMENT_DEBUG]   - possible_diagnosis: {assessment_data.get('possible_diagnosis')}")
            print(f"[ASSESSMENT_DEBUG]   - confidence_level: {assessment_data.get('confidence_level')}")
            
            # Extract AI recommended department - try multiple strategies if JSON parsing failed
            ai_suggested_dept = assessment_data.get("recommended_department")
            
            # If JSON parsing failed and we don't have the department, try text extraction
            if not ai_suggested_dept:
                print("[ASSESSMENT_DEBUG] 🔍 Department not found in JSON, attempting text extraction")
                dept_patterns = [
                    r'"recommended_department":\s*"([^"]+)"',
                    r'recommended_department[:\s]+([A-Za-z\s]+)(?:\n|,|\})',
                    r'department[:\s]+([A-Za-z\s]+)(?:\n|,|\})',
                    r'(Orthopedics?|Cardiology|Urology|Pediatrics?|Diabetologist|General Medicine)'
                ]
                
                for pattern in dept_patterns:
                    match = re.search(pattern, response.text, re.IGNORECASE)
                    if match:
                        ai_suggested_dept = match.group(1).strip()
                        print(f"[ASSESSMENT_DEBUG] ✅ Extracted department from text: '{ai_suggested_dept}'")
                        break
                
                # Last resort fallback only if no department found anywhere
                if not ai_suggested_dept:
                    ai_suggested_dept = "General Medicine"
                    print("[ASSESSMENT_DEBUG] ⚠️ Using final fallback: General Medicine")
            
            # For AI help option, ignore previous consultation doctor to avoid conflicts
            # Patient specifically chose AI help, so prioritize AI recommendation
            patient_chosen_doctor = None  # Clear previous doctor choice for AI help flow
            
            print(f"[ASSESSMENT_DEBUG] Final parsed assessment_data keys: {list(assessment_data.keys())}")
            print(f"[ASSESSMENT_DEBUG] Final assessment_data: {assessment_data}")
            print(f"[ASSESSMENT_DEBUG] AI suggested department extracted: '{ai_suggested_dept}'")
            print(f"[ASSESSMENT_DEBUG] Patient chosen doctor (cleared for AI help): '{patient_chosen_doctor}'")
            
            doctor_recommendations = department_service.get_doctor_recommendations(
                ai_suggested_dept=ai_suggested_dept,
                patient_chosen_doctor=patient_chosen_doctor
            )
            
            print(f"[ASSESSMENT_DEBUG] Doctor recommendations received: {doctor_recommendations}")
            
            # Determine final recommended doctor and department
            final_department = doctor_recommendations['matched_department'] or ai_suggested_dept
            final_doctor = "Visit hospital reception"
            
            if doctor_recommendations['recommendation_type'] == 'perfect_match':
                final_doctor = doctor_recommendations['patient_doctor_info'].name
                final_department = doctor_recommendations['patient_doctor_info'].department
            elif doctor_recommendations['recommendation_type'] == 'patient_choice_only':
                final_doctor = doctor_recommendations['patient_doctor_info'].name
                final_department = doctor_recommendations['patient_doctor_info'].department
            elif doctor_recommendations['recommendation_type'] == 'ai_department' and doctor_recommendations['recommended_doctors']:
                # Pick first available doctor from AI recommended department
                final_doctor = doctor_recommendations['recommended_doctors'][0].name
                final_department = doctor_recommendations['matched_department']
            elif doctor_recommendations['recommendation_type'] == 'reception_referral':
                # AI suggested department not available in CSV
                final_doctor = "Visit hospital reception"
                final_department = "Reception"
                print(f"[ASSESSMENT_DEBUG] AI suggested '{ai_suggested_dept}' not in CSV - directing to reception")
            elif doctor_recommendations['recommendation_type'] == 'conflict_resolution':
                # Include both options in the recommendation
                patient_doc = doctor_recommendations['patient_doctor_info']
                ai_docs = doctor_recommendations['recommended_doctors']
                if ai_docs:
                    final_doctor = f"Dr. {patient_doc.name} ({patient_doc.department}) or Dr. {ai_docs[0].name} ({doctor_recommendations['matched_department']})"
                else:
                    final_doctor = f"Dr. {patient_doc.name} ({patient_doc.department}) or {doctor_recommendations['matched_department']} specialist"
            
            # Enhanced doctor comparison analysis
            enhanced_comparison = self._generate_enhanced_comparison(
                assessment_data.get("doctor_comparison_analysis", ""),
                doctor_recommendations
            )
            
            print(f"[ASSESSMENT_DEBUG] Final department: '{final_department}'")
            print(f"[ASSESSMENT_DEBUG] Final doctor: '{final_doctor}'")
            print(f"[ASSESSMENT_DEBUG] Enhanced comparison: '{enhanced_comparison[:100]}...'")
            
            # Get pre-consultation diagnostics
            diagnostics_result = diagnostics_service.get_pre_consultation_diagnostics(
                possible_diagnosis=assessment_data.get("possible_diagnosis", ""),
                investigative_history=assessment_data.get("investigative_history", "")
            )
            
            print(f"[ASSESSMENT_DEBUG] Diagnostics result: {diagnostics_result}")
            
            return {
                "assessment": InvestigativeResult(
                    investigative_history=assessment_data.get("investigative_history", "Assessment completed based on patient responses"),
                    possible_diagnosis=assessment_data.get("possible_diagnosis", "Further evaluation recommended")
                ),
                "response_id": None,  # Gemini doesn't use response IDs
                "confidence_level": assessment_data.get("confidence_level", 50),
                "recommended_department": final_department,
                "recommended_doctor": final_doctor,
                "doctor_comparison_analysis": enhanced_comparison,
                "pre_consultation_diagnostics": diagnostics_result.get("diagnostics", {}),
                "matched_diagnostic_condition": diagnostics_result.get("matched_condition"),
                "diagnostics_explanation": diagnostics_result.get("explanation", ""),
                "reasoning_tokens": 0,  # Not available in Gemini API
                "department_recommendations": doctor_recommendations  # Additional metadata
            }
            
        except Exception as e:
            print(f"Error generating assessment: {e}")
            import traceback
            traceback.print_exc()
            return {
                "assessment": InvestigativeResult(
                    investigative_history="Assessment completed based on patient responses",
                    possible_diagnosis="Further evaluation recommended due to processing error"
                ),
                "response_id": None,
                "confidence_level": 30,
                "recommended_department": "General Medicine",
                "recommended_doctor": "General Practitioner",
                "doctor_comparison_analysis": "Error occurred during assessment",
                "reasoning_tokens": 0
            }

    def _generate_enhanced_comparison(self, original_analysis: str, doctor_recommendations: Dict) -> str:
        """Generate enhanced doctor comparison analysis with department availability info"""
        
        recommendation_type = doctor_recommendations['recommendation_type']
        
        if recommendation_type == 'perfect_match':
            return f"✅ Perfect Match: Your chosen doctor Dr. {doctor_recommendations['patient_doctor_info'].name} in {doctor_recommendations['patient_doctor_info'].department} aligns perfectly with the AI's medical assessment. This is an excellent choice for your condition."
        
        elif recommendation_type == 'conflict_resolution':
            patient_doc = doctor_recommendations['patient_doctor_info']
            ai_dept = doctor_recommendations['matched_department']
            ai_doctors = doctor_recommendations['recommended_doctors']
            
            analysis = f"⚖️ Based on your symptoms, {ai_dept} specialist is suggested. "
            analysis += f"You can visit both doctors:\n"
            analysis += f"• Your choice: Dr. {patient_doc.name} ({patient_doc.department})\n"
            analysis += f"• AI recommendation: "
            if ai_doctors:
                analysis += f"Dr. {ai_doctors[0].name} ({ai_dept})"
            else:
                analysis += f"{ai_dept} specialist"
            analysis += f"\n\nBoth consultations may provide comprehensive care for your condition."
            return analysis
        
        elif recommendation_type == 'patient_choice_only':
            return f"👤 Patient Choice: Your selected doctor Dr. {doctor_recommendations['patient_doctor_info'].name} in {doctor_recommendations['patient_doctor_info'].department} is available and suitable for consultation."
        
        elif recommendation_type == 'ai_department':
            ai_dept = doctor_recommendations['matched_department']
            ai_doctors = doctor_recommendations['recommended_doctors']
            if ai_doctors:
                return f"🤖 AI Recommendation: Based on your symptoms, {ai_dept} department is most suitable. Dr. {ai_doctors[0].name} is available for consultation."
            else:
                return f"🤖 AI Recommendation: {ai_dept} department is recommended for your condition."
        
        else:  # hospital_reception
            return f"🏥 General Consultation: The recommended specialty department is not currently available. Please visit hospital reception for general consultation and proper referral to the appropriate specialist."
