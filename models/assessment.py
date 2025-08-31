"""
Medical assessment data models
"""

from pydantic import BaseModel, Field
from typing import Optional

class AssessmentRequest(BaseModel):
    session_id: str
    patient_id: str

class InvestigativeResult(BaseModel):
    investigative_history: str = Field(..., description="Complete interview summary")
    possible_diagnosis: str = Field(..., description="Medical assessment with confidence level")

class AssessmentResponse(BaseModel):
    success: bool
    message: str
    assessment: Optional[InvestigativeResult] = None
    session_id: str
    confidence_level: Optional[str] = None
    recommended_action: Optional[str] = None
    recommended_doctor: Optional[str] = None
    recommended_department: Optional[str] = None
    doctor_comparison_analysis: Optional[str] = None
    pre_consultation_diagnostics: Optional[dict] = None
    matched_diagnostic_condition: Optional[str] = None
    diagnostics_explanation: Optional[str] = None
