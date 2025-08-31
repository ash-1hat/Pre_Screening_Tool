"""
Hospital and department data models
"""

from pydantic import BaseModel
from typing import Dict, List

class Department(BaseModel):
    name: str
    doctors: List[str]

class DepartmentList(BaseModel):
    departments: List[str]

class DoctorList(BaseModel):
    department: str
    doctors: List[str]

class HospitalData(BaseModel):
    departments_doctors: Dict[str, List[str]]
    
class DoctorSelection(BaseModel):
    department: str
    doctor: str
