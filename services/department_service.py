"""
Department and Doctor Recommendation Service
"""

import csv
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class Doctor:
    id: str
    name: str
    department: str

class DepartmentService:
    def __init__(self):
        self.doctors: List[Doctor] = []
        self.departments: Dict[str, List[Doctor]] = {}
        self._load_hospital_data()
    
    def _load_hospital_data(self):
        """Load doctors and departments from CSV file"""
        try:
            csv_path = os.path.join(os.path.dirname(__file__), '..', 'DepartmentswithDoctors.csv')
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    doctor = Doctor(
                        id=row['onehat_doctor_id'],
                        name=row['Doctor Name'],
                        department=row['Department']
                    )
                    self.doctors.append(doctor)
                    
                    # Group by department
                    if doctor.department not in self.departments:
                        self.departments[doctor.department] = []
                    self.departments[doctor.department].append(doctor)
            
            print(f"[DEPT_SERVICE] Loaded {len(self.doctors)} doctors from {len(self.departments)} departments")
            
        except Exception as e:
            print(f"[DEPT_SERVICE] Error loading hospital data: {e}")
    
    def get_available_departments(self) -> List[str]:
        """Get list of all available departments"""
        return list(self.departments.keys())
    
    def get_doctors_by_department(self, department: str) -> List[Doctor]:
        """Get all doctors in a specific department"""
        return self.departments.get(department, [])
    
    def find_doctor_by_name(self, doctor_name: str) -> Optional[Doctor]:
        """Find a doctor by name"""
        for doctor in self.doctors:
            if doctor.name.lower() == doctor_name.lower():
                return doctor
        return None
    
    def is_department_available(self, department: str) -> bool:
        """Check if a department exists in the hospital"""
        # Normalize department names for comparison
        available_depts = [dept.lower() for dept in self.departments.keys()]
        return department.lower() in available_depts
    
    def find_matching_department(self, ai_suggested_dept: str) -> Optional[str]:
        """Find the best matching department from available ones"""
        ai_dept_lower = ai_suggested_dept.lower()
        
        # Direct match
        for dept in self.departments.keys():
            if dept.lower() == ai_dept_lower:
                return dept
        
        # Common medical specialty mappings (exact mappings only)
        specialty_mappings = {
            'orthopedic': 'Orthopedics',
            'orthopedics': 'Orthopedics',
            'ortho': 'Orthopedics',
            'cardiac': 'Cardiology',
            'cardiology': 'Cardiology',
            'heart': 'Cardiology',
            'diabetes': 'Diabetologist',
            'diabetologist': 'Diabetologist',
            'endocrine': 'Diabetologist',
            'pediatric': 'Pediatrics',
            'pediatrics': 'Pediatrics',
            'children': 'Pediatrics',
            'urology': 'Urology',
            'kidney': 'Urology',
            'general medicine': 'General Medicine',
            'general': 'General Medicine',
            'internal medicine': 'General Medicine',
            'internal': 'General Medicine'
        }
        
        # Check exact keyword matches
        if ai_dept_lower in specialty_mappings:
            mapped_dept = specialty_mappings[ai_dept_lower]
            if mapped_dept in self.departments:
                return mapped_dept
        
        # Check if any keyword is contained in the AI suggestion
        for keyword, dept in specialty_mappings.items():
            if keyword in ai_dept_lower and dept in self.departments:
                return dept
        
        # Only do partial matching for very specific cases to avoid false matches
        # like "Neurology" matching "Urology"
        for dept in self.departments.keys():
            dept_lower = dept.lower()
            # Only match if AI suggestion exactly starts with department name
            if ai_dept_lower.startswith(dept_lower) and len(ai_dept_lower) - len(dept_lower) <= 3:
                return dept
        
        return None
    
    def get_doctor_recommendations(self, ai_suggested_dept: str, patient_chosen_doctor: str = None) -> Dict:
        """
        Get comprehensive doctor recommendations based on AI suggestion and patient choice
        """
        print(f"[DEPT_DEBUG] Getting recommendations for AI dept: '{ai_suggested_dept}', Patient doctor: '{patient_chosen_doctor}'")
        
        result = {
            'ai_suggested_department': ai_suggested_dept,
            'department_available': False,
            'matched_department': None,
            'recommended_doctors': [],
            'patient_chosen_doctor': patient_chosen_doctor,
            'patient_doctor_available': False,
            'patient_doctor_info': None,
            'recommendation_type': 'hospital_reception',  # Default
            'message': 'Please visit hospital reception for general consultation'
        }
        
        # Check if AI suggested department is available
        matched_dept = self.find_matching_department(ai_suggested_dept)
        print(f"[DEPT_DEBUG] AI suggested dept '{ai_suggested_dept}' matched to: '{matched_dept}'")
        
        if matched_dept:
            result['department_available'] = True
            result['matched_department'] = matched_dept
            result['recommended_doctors'] = self.get_doctors_by_department(matched_dept)
            result['recommendation_type'] = 'ai_department'
            result['message'] = f'Proceed to {matched_dept} department'
            print(f"[DEPT_DEBUG] Found {len(result['recommended_doctors'])} doctors in {matched_dept}")
        else:
            # AI suggested department not available in CSV - direct to reception
            result['department_available'] = False
            result['matched_department'] = None
            result['recommended_doctors'] = []
            result['recommendation_type'] = 'reception_referral'
            result['message'] = 'Please visit hospital reception'
            print(f"[DEPT_DEBUG] AI suggested dept '{ai_suggested_dept}' not found in CSV - directing to reception")
        
        # Check patient's chosen doctor
        if patient_chosen_doctor:
            patient_doctor = self.find_doctor_by_name(patient_chosen_doctor)
            print(f"[DEPT_DEBUG] Patient doctor '{patient_chosen_doctor}' found: {patient_doctor.name if patient_doctor else 'Not found'}")
            
            if patient_doctor:
                result['patient_doctor_available'] = True
                result['patient_doctor_info'] = patient_doctor
                print(f"[DEPT_DEBUG] Patient doctor department: '{patient_doctor.department}'")
                
                # Determine final recommendation
                if matched_dept and patient_doctor.department == matched_dept:
                    # Perfect match - AI and patient agree
                    result['recommendation_type'] = 'perfect_match'
                    result['message'] = f'Excellent choice! Proceed to Dr. {patient_doctor.name} in {patient_doctor.department}'
                elif matched_dept and patient_doctor.department != matched_dept:
                    # Conflict - suggest both options
                    result['recommendation_type'] = 'conflict_resolution'
                    result['message'] = f'Two options available: 1) Your choice: Dr. {patient_doctor.name} ({patient_doctor.department}) 2) AI recommendation: {matched_dept} department'
                    print(f"[DEPT_DEBUG] Conflict detected: Patient chose {patient_doctor.department}, AI suggests {matched_dept}")
                else:
                    # Patient doctor available but AI dept not found
                    result['recommendation_type'] = 'patient_choice_only'
                    result['message'] = f'Proceed to your chosen doctor: Dr. {patient_doctor.name} in {patient_doctor.department}'
        
        print(f"[DEPT_DEBUG] Final recommendation type: '{result['recommendation_type']}'")
        print(f"[DEPT_DEBUG] Final message: '{result['message']}'")
        return result

# Global instance
department_service = DepartmentService()
