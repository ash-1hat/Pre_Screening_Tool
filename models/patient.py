"""
Patient data models for the medical pre-screening system
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum

class GenderEnum(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"

class PatientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Patient's full name")
    mobile: str = Field(..., pattern=r'^[6-9]\d{9}$', description="10-digit mobile number")
    age: int = Field(..., ge=1, le=120, description="Patient's age")
    gender: GenderEnum = Field(..., description="Patient's gender")
    chosen_doctor: Optional[str] = Field(None, description="Selected doctor name")
    chosen_department: Optional[str] = Field(None, description="Selected department")
    skip_doctor_selection: bool = Field(False, description="Let AI recommend doctor")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip().title()

    @field_validator('mobile')
    @classmethod
    def validate_mobile(cls, v):
        # Remove any spaces or special characters
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) != 10 or not cleaned.startswith(('6', '7', '8', '9')):
            raise ValueError('Invalid mobile number format')
        return cleaned

class PatientInfo(BaseModel):
    id: str = Field(..., description="Unique patient identifier")
    name: str
    mobile: str
    age: int
    gender: GenderEnum
    chosen_doctor: Optional[str] = None
    chosen_department: Optional[str] = None
    skip_doctor_selection: bool = False
    created_at: str

class PatientResponse(BaseModel):
    success: bool
    message: str
    patient: Optional[PatientInfo] = None
    session_id: str

class FaceRecognitionResult(BaseModel):
    success: bool
    message: str
    patient_data: Optional[dict] = None
    consultation_data: Optional[dict] = None
    recognition_info: Optional[dict] = None
