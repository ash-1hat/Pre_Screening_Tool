"""
Pre-consultation diagnostics service using LLM and CSV data
"""

import csv
import os
import json
from typing import Dict, List, Optional, Any
from google import genai
from google.genai import types
from core.config import settings

class DiagnosticsService:
    def __init__(self):
        self.diagnostics_data = []
        self.client = None
        self.model = settings.gemini_model
        self._load_diagnostics_data()
        self._initialize_gemini()
        
    def _load_diagnostics_data(self):
        """Load pre-diagnostics CSV data"""
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'pre-diagonstics.csv')
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                self.diagnostics_data = list(reader)
            print(f"[DIAGNOSTICS_SERVICE] Loaded {len(self.diagnostics_data)} diagnostic entries")
        except Exception as e:
            print(f"[DIAGNOSTICS_SERVICE] Error loading CSV: {e}")
            self.diagnostics_data = []
    
    def _initialize_gemini(self):
        """Initialize Gemini AI client"""
        try:
            self.client = genai.Client(api_key=settings.gemini_api_key)
            print(f"[DIAGNOSTICS_SERVICE] Gemini client initialized with model: {self.model}")
        except Exception as e:
            print(f"[DIAGNOSTICS_SERVICE] Error initializing Gemini: {e}")
            self.client = None
    
    def get_pre_consultation_diagnostics(self, possible_diagnosis: str, investigative_history: str) -> Dict[str, Any]:
        """
        Get pre-consultation diagnostics based on diagnosis and patient history
        
        Args:
            possible_diagnosis: AI-generated possible diagnosis
            investigative_history: Patient interview summary
            
        Returns:
            Dictionary with diagnostics suggestions grouped by type
        """
        if not self.client or not self.diagnostics_data:
            return {"diagnostics": {}, "matched_condition": None, "explanation": "Diagnostics service unavailable"}
        
        try:
            # Create prompt for LLM to match diagnosis with CSV data
            csv_conditions = []
            for entry in self.diagnostics_data:
                condition = entry.get('Condition', '')
                sub_condition = entry.get('Sub-Condition', '')
                pre_consultation = entry.get('Pre-Consultation (Diagnostics)', '')
                
                if condition and sub_condition and pre_consultation:
                    csv_conditions.append({
                        'condition': condition,
                        'sub_condition': sub_condition,
                        'diagnostics': pre_consultation
                    })
            
            prompt = self._create_matching_prompt(
                possible_diagnosis, 
                investigative_history, 
                csv_conditions
            )
            
            print(f"[DIAGNOSTICS_DEBUG] Matching diagnosis: '{possible_diagnosis}'")
            print(f"[DIAGNOSTICS_DEBUG] Available conditions: {len(csv_conditions)}")
            
            # Get LLM response using new API
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            if not response or not response.text:
                return {"diagnostics": {}, "matched_condition": None}
            
            print(f"[DIAGNOSTICS_DEBUG] LLM response: {response.text[:200]}...")
            
            # Parse LLM response
            result = self._parse_diagnostics_response(response.text)
            
            return result
            
        except Exception as e:
            print(f"[DIAGNOSTICS_ERROR] Error getting diagnostics: {e}")
            return {"diagnostics": {}, "matched_condition": None}
    
    def _create_matching_prompt(self, diagnosis: str, history: str, conditions: List[Dict]) -> str:
        """Create prompt for LLM to match diagnosis with CSV conditions"""
        
        conditions_text = "\n".join([
            f"- {cond['condition']} → {cond['sub_condition']}: {cond['diagnostics']}"
            for cond in conditions
        ])
        
        prompt = f"""You are a medical diagnostics expert. Your task is to match a patient's possible diagnosis with pre-consultation diagnostic recommendations.

PATIENT INFORMATION:
- Possible Diagnosis: {diagnosis}
- Patient History: {history}

AVAILABLE DIAGNOSTIC CONDITIONS:
{conditions_text}

INSTRUCTIONS:
1. Find the BEST MATCHING condition/sub-condition from the list above that relates to the patient's diagnosis
2. Use fuzzy matching - look for similar medical terms, symptoms, or conditions
3. Focus primarily on the SUB-CONDITION for matching
4. If you find a relevant match, extract the pre-consultation diagnostics
5. Group the diagnostics by type (Imaging, Blood Tests, Clinical Tests, etc.)
6. Return ONLY the test names without any explanations or descriptions

RESPONSE FORMAT (JSON only):
{{
    "matched_condition": "Condition → Sub-Condition" or null,
    "diagnostics": {{
        "Imaging": ["X-Ray", "MRI"],
        "Blood Tests": ["CBC", "ESR"],
        "Clinical Tests": ["Physical examination", "Range of motion test"],
        "Other": ["Additional tests"]
    }}
}}

IMPORTANT: Return only concise test names without explanations, descriptions, or reasoning. Example:
- Good: "X-Ray (AP, Lateral, Sunrise views)", "MRI", "CBC"
- Bad: "X-Ray (to rule out fractures)", "MRI of the knee for detailed assessment"

If no relevant match is found, return:
{{
    "matched_condition": null,
    "diagnostics": {{}}
}}

Generate response:"""
        
        return prompt
    
    def _parse_diagnostics_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response and extract diagnostics information"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                result = json.loads(json_text)
                
                # Validate structure
                if not isinstance(result.get('diagnostics'), dict):
                    result['diagnostics'] = {}
                
                return result
            else:
                # Fallback parsing if JSON not found
                return {
                    "matched_condition": None,
                    "diagnostics": {}
                }
                
        except json.JSONDecodeError as e:
            print(f"[DIAGNOSTICS_ERROR] JSON parsing error: {e}")
            return {
                "matched_condition": None,
                "diagnostics": {}
            }
        except Exception as e:
            print(f"[DIAGNOSTICS_ERROR] Response parsing error: {e}")
            return {
                "matched_condition": None,
                "diagnostics": {}
            }

# Global instance
diagnostics_service = DiagnosticsService()
