"""
Export service for generating JSON data with patient and assessment information
"""

import json
import csv
from typing import Dict, Any, Optional
from datetime import datetime

class ExportService:
    def __init__(self):
        self.doctor_lookup = {}
        self._load_doctor_data()
    
    def _load_doctor_data(self):
        """Load doctor data from CSV for ID lookup"""
        try:
            with open('DepartmentswithDoctors.csv', 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    doctor_id = row.get('onehat_doctor_id', '').strip()
                    doctor_name = row.get('Doctor Name', '').strip()
                    department = row.get('Department', '').strip()
                    
                    if doctor_id and doctor_name and department:
                        # Create lookup by name and department
                        key = f"{doctor_name}|{department}".lower()
                        self.doctor_lookup[key] = doctor_id
                        
                        # Also create lookup by name only (fallback)
                        name_key = doctor_name.lower()
                        if name_key not in self.doctor_lookup:
                            self.doctor_lookup[name_key] = doctor_id
            
            print(f"[EXPORT_SERVICE] Loaded {len(self.doctor_lookup)} doctor entries")
            
        except Exception as e:
            print(f"[EXPORT_ERROR] Failed to load doctor data: {e}")
            self.doctor_lookup = {}
    
    def get_doctor_id(self, doctor_name: str, department: str = None) -> Optional[str]:
        """Get doctor ID from name and department"""
        if not doctor_name:
            return None
            
        # Try exact match with department first
        if department:
            key = f"{doctor_name}|{department}".lower()
            if key in self.doctor_lookup:
                return self.doctor_lookup[key]
        
        # Fallback to name only
        name_key = doctor_name.lower()
        return self.doctor_lookup.get(name_key)
    
    def generate_assessment_json(self, 
                                patient_info: Dict,
                                assessment_data: Dict,
                                doctor_recommendations: Dict,
                                diagnostics_result: Dict) -> Dict[str, Any]:
        """Generate comprehensive JSON export of assessment data"""
        
        # Extract patient information
        patient_name = patient_info.get('name', '')
        patient_mobile = patient_info.get('mobile', '')
        patient_age = patient_info.get('age', '')
        patient_gender = str(patient_info.get('gender', '')).replace('GenderEnum.', '')
        
        # Get chosen doctor ID
        chosen_doctor = patient_info.get('chosen_doctor')
        chosen_doctor_id = None
        if chosen_doctor:
            chosen_doctor_id = self.get_doctor_id(chosen_doctor)
        
        # Extract assessment information
        investigative_summary = assessment_data.get('investigative_history', '')
        possible_diagnosis = assessment_data.get('possible_diagnosis', '')
        
        # Extract doctor recommendations
        suggested_department = doctor_recommendations.get('matched_department', '')
        suggested_doctors = doctor_recommendations.get('recommended_doctors', [])
        suggested_doctor_name = ''
        suggested_doctor_id = None
        
        if suggested_doctors and len(suggested_doctors) > 0:
            suggested_doctor_name = suggested_doctors[0].name
            suggested_doctor_id = self.get_doctor_id(
                suggested_doctor_name, 
                suggested_department
            )
        
        # Extract pre-consultation diagnostics
        pre_consultation_diagnostics = diagnostics_result.get('diagnostics', {})
        
        # Generate export JSON
        export_data = {
            "Patient_Name": patient_name,
            "Patient_Mobile": patient_mobile,
            "Patient_Age": patient_age,
            "Patient_Gender": patient_gender,
            "Patient_Chosen_Doctor_id": chosen_doctor_id,
            "Investigative_Summary": investigative_summary,
            "Possible_Diagnosis": possible_diagnosis,
            "Suggested_Department": suggested_department,
            "Suggested_Doctor_id": suggested_doctor_id,
            "Pre_Consultation_Diagnostics": pre_consultation_diagnostics,
            "Export_Timestamp": datetime.now().isoformat()
        }
        
        return export_data
    
    def print_assessment_json(self, export_data: Dict[str, Any]):
        """Print formatted JSON to terminal"""
        print("\n" + "="*80)
        print("📋 ASSESSMENT EXPORT DATA")
        print("="*80)
        print(json.dumps(export_data, indent=2, ensure_ascii=False))
        print("="*80)
        print("✅ Assessment data exported successfully\n")

# Global instance
export_service = ExportService()
