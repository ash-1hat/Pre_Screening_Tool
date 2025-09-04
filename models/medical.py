"""
Medical interview data models
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class InterviewStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"

class QuestionAnswer(BaseModel):
    question: str = Field(..., description="Medical question asked")
    answer: str = Field(..., description="Patient's response")
    timestamp: str = Field(..., description="When the Q&A occurred")

class InterviewSession(BaseModel):
    session_id: str
    patient_id: str
    status: InterviewStatus = InterviewStatus.ACTIVE
    conversation_history: List[QuestionAnswer] = []
    question_number: int = 1
    unknown_count: int = 0
    max_questions: int = 6
    max_unknowns: int = 2
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    # Track the last question asked by AI
    last_question_asked: Optional[str] = None
    # GPT-5 Responses API state management
    current_response_id: Optional[str] = None
    previous_response_id: Optional[str] = None
    total_reasoning_tokens: int = 0

class QuestionRequest(BaseModel):
    session_id: str
    patient_id: str

class FollowupAssessmentRequest(BaseModel):
    session_id: str

class QuestionResponse(BaseModel):
    success: bool
    question: Optional[str] = None
    question_number: int
    progress: dict
    interview_complete: bool = False
    message: Optional[str] = None
    response_id: Optional[str] = None
    reasoning_tokens: int = 0

class AnswerSubmission(BaseModel):
    session_id: str
    patient_id: str
    answer: str = Field(..., min_length=1, description="Patient's answer to the current question")

class VoiceInfo(BaseModel):
    original_language: str = Field(..., description="Detected original language")
    original_text: str = Field(..., description="Original transcribed text")
    confidence: float = Field(..., description="Transcription confidence score")
    processing_time: float = Field(..., description="Voice processing time in seconds")

class AnswerResponse(BaseModel):
    success: bool
    message: str
    next_question: Optional[str] = None
    question_number: int
    progress: dict
    interview_complete: bool = False
    response_id: Optional[str] = None
    reasoning_tokens: int = 0
    voice_info: Optional[VoiceInfo] = None

class InterviewHistory(BaseModel):
    session_id: str
    patient_info: dict
    conversation_history: List[QuestionAnswer]
    status: InterviewStatus
    progress: dict
