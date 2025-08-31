"""
Medical interview API endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from models.medical import (
    QuestionRequest, QuestionResponse, AnswerSubmission, 
    AnswerResponse, InterviewSession, QuestionAnswer, InterviewStatus
)
from services.medical_expert_service import MedicalExpertService
from services.session_service import sessions, get_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize medical expert with error handling
try:
    medical_expert = MedicalExpertService()
    print("MedicalExpertService initialized successfully")
except Exception as e:
    print(f"Failed to initialize MedicalExpertService: {e}")
    medical_expert = None


# In-memory storage for interview sessions
interview_sessions: Dict[str, InterviewSession] = {}

@router.post("/medical/start-interview", response_model=QuestionResponse)
async def start_medical_interview(request: QuestionRequest):
    """Start a new medical interview session"""
    
    try:
        # Get patient session
        print(f"Getting session for session_id: {request.session_id}")
        session = get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        print(f"Session data keys: {session.keys()}")
        patient_info = session.get("patient_info")
        if not patient_info:
            print(f"❌ [MEDICAL] Patient information not found in session")
            raise HTTPException(status_code=400, detail="Patient information not found")
        
        print(f"Patient info: {patient_info}")
        
        # Create interview session
        print("Creating interview session...")
        current_time = datetime.now().isoformat()
        try:
            interview_session = InterviewSession(
                session_id=request.session_id,
                patient_id=request.patient_id,
                status=InterviewStatus.ACTIVE,
                conversation_history=[],
                question_number=1,
                unknown_count=0,
                created_at=current_time,
                updated_at=current_time,
                expires_at=None
            )
            print("Interview session created successfully")
        except Exception as e:
            print(f"Error creating interview session: {e}")
            raise
        
        interview_sessions[request.session_id] = interview_session
        print("Interview session stored")
        
        # Generate first question with error handling
        if not medical_expert:
            print("Medical expert not initialized, using fallback")
            first_question = "What is your main health concern or symptom that brought you here today?"
            response_id = None
            reasoning_tokens = 0
        else:
            try:
                question_result = await medical_expert.generate_next_question(
                    patient=patient_info,
                    conversation_history=[],
                    question_number=1,
                    unknown_count=0,
                    previous_response_id=None
                )
                
                # Handle both dict and string returns for backwards compatibility
                if isinstance(question_result, dict):
                    first_question = question_result.get("question", "What is your main health concern or symptom that brought you here today?")
                    response_id = question_result.get("response_id")
                    reasoning_tokens = question_result.get("reasoning_tokens", 0)
                else:
                    # Fallback for string return
                    first_question = str(question_result)
                    response_id = None
                    reasoning_tokens = 0
                
                # Update interview session with response ID
                interview_session.current_response_id = response_id
                interview_session.total_reasoning_tokens = reasoning_tokens
                # Store the first question for the next answer submission
                interview_session.last_question_asked = first_question
                
            except Exception as e:
                print(f"Error generating first question: {e}")
                import traceback
                traceback.print_exc()
                # Use fallback question
                first_question = "What is your main health concern or symptom that brought you here today?"
                response_id = None
                reasoning_tokens = 0
        
        return QuestionResponse(
            success=True,
            question=first_question,
            question_number=1,
            progress={
                "current_question": 1,
                "max_questions": 6,
                "unknown_count": 0,
                "max_unknowns": 2,
                "completion_percent": 0
            },
            interview_complete=False,
            response_id=response_id,
            reasoning_tokens=reasoning_tokens
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in start_medical_interview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")

@router.post("/medical/submit-answer", response_model=AnswerResponse)
async def submit_patient_answer(submission: AnswerSubmission):
    """Submit patient answer and get next question"""
    
    print(f"[DEBUG] Submit answer called with session_id: {submission.session_id}")
    print(f"[DEBUG] Answer: {submission.answer}")
    
    # Get interview session
    if submission.session_id not in interview_sessions:
        print(f"[DEBUG] Interview session not found for: {submission.session_id}")
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    interview_session = interview_sessions[submission.session_id]
    print(f"[DEBUG] Interview session status: {interview_session.status}")
    print(f"[DEBUG] Current question number: {interview_session.question_number}")
    
    if interview_session.status != InterviewStatus.ACTIVE:
        print(f"[DEBUG] Interview session not active: {interview_session.status}")
        raise HTTPException(status_code=400, detail="Interview session is not active")
    
    # Get patient info from main session
    session = get_session(submission.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    patient_info = session.get("patient_info")
    
    # Store the Q&A pair using the last question asked by AI
    if interview_session.last_question_asked:
        current_question = interview_session.last_question_asked
        print(f"[DEBUG] Using last question asked by AI: {current_question}")
    else:
        current_question = "What is your main health concern today?"  # Default fallback for first question
        print(f"[DEBUG] No previous question, using fallback question")
    
    # Store the Q&A pair
    qa_pair = QuestionAnswer(
        question=current_question,
        answer=submission.answer.strip(),
        timestamp=datetime.now().isoformat()
    )
    interview_session.conversation_history.append(qa_pair)
    
    # Check for "I don't know" responses
    if "don't know" in submission.answer.lower() or "not sure" in submission.answer.lower():
        interview_session.unknown_count += 1
    
    # Check stopping conditions
    max_questions_reached = interview_session.question_number >= interview_session.max_questions
    too_many_unknowns = interview_session.unknown_count >= interview_session.max_unknowns
    
    print(f"[DEBUG] Max questions reached: {max_questions_reached} ({interview_session.question_number}/{interview_session.max_questions})")
    print(f"[DEBUG] Too many unknowns: {too_many_unknowns} ({interview_session.unknown_count}/{interview_session.max_unknowns})")
    
    if max_questions_reached or too_many_unknowns:
        print(f"[DEBUG] Interview complete - returning completion response")
        interview_session.status = InterviewStatus.COMPLETED
        interview_session.updated_at = datetime.now().isoformat()
        
        return AnswerResponse(
            success=True,
            message="Interview completed. Ready for assessment.",
            next_question=None,
            question_number=interview_session.question_number,
            progress={
                "current_question": interview_session.question_number,
                "max_questions": interview_session.max_questions,
                "unknown_count": interview_session.unknown_count,
                "max_unknowns": interview_session.max_unknowns,
                "completion_percent": 100
            },
            interview_complete=True,
            response_id=None,
            reasoning_tokens=0
        )
    
    # Generate next question
    interview_session.question_number += 1
    
    # Update previous response ID for conversation continuity
    interview_session.previous_response_id = interview_session.current_response_id
    
    try:
        question_result = await medical_expert.generate_next_question(
            patient=patient_info,
            conversation_history=[qa.dict() for qa in interview_session.conversation_history],
            question_number=interview_session.question_number,
            unknown_count=interview_session.unknown_count,
            previous_response_id=interview_session.previous_response_id
        )
        
        # Handle both dict and string returns for backwards compatibility
        if isinstance(question_result, dict):
            next_question = question_result.get("question", "Can you tell me more about your symptoms?")
            response_id = question_result.get("response_id")
            reasoning_tokens = question_result.get("reasoning_tokens", 0)
        else:
            # Fallback for string return
            next_question = str(question_result)
            response_id = None
            reasoning_tokens = 0
        
        # Update interview session state
        interview_session.current_response_id = response_id
        interview_session.total_reasoning_tokens += reasoning_tokens
        # Store the question we just asked for the next answer submission
        interview_session.last_question_asked = next_question
        
    except Exception as e:
        print(f"Error generating next question: {e}")
        import traceback
        traceback.print_exc()
        # Use fallback question
        next_question = "Can you tell me more about your symptoms?"
        response_id = None
        reasoning_tokens = 0
    
    # Check if AI thinks assessment is ready
    if "ASSESSMENT_READY" in next_question:
        print(f"[DEBUG] AI indicates assessment ready")
        interview_session.status = InterviewStatus.COMPLETED
        interview_session.updated_at = datetime.now().isoformat()
        
        return AnswerResponse(
            success=True,
            message="Medical expert has sufficient information for assessment.",
            next_question=None,
            question_number=interview_session.question_number,
            progress={
                "current_question": interview_session.question_number,
                "max_questions": interview_session.max_questions,
                "unknown_count": interview_session.unknown_count,
                "max_unknowns": interview_session.max_unknowns,
                "completion_percent": 100
            },
            interview_complete=True,
            response_id=response_id,
            reasoning_tokens=reasoning_tokens
        )
    
    interview_session.updated_at = datetime.now().isoformat()
    
    completion_percent = min((interview_session.question_number / interview_session.max_questions) * 100, 100)
    
    print(f"[DEBUG] Returning next question: {next_question}")
    print(f"[DEBUG] Response ID: {response_id}")
    print(f"[DEBUG] Completion percent: {completion_percent}")
    
    response = AnswerResponse(
        success=True,
        message="Answer recorded successfully",
        next_question=next_question,
        question_number=interview_session.question_number,
        progress={
            "current_question": interview_session.question_number,
            "max_questions": interview_session.max_questions,
            "unknown_count": interview_session.unknown_count,
            "max_unknowns": interview_session.max_unknowns,
            "completion_percent": completion_percent
        },
        interview_complete=False,
        response_id=response_id,
        reasoning_tokens=reasoning_tokens
    )
    
    print(f"[DEBUG] Final response: {response.dict()}")
    return response

@router.get("/medical/interview/{session_id}")
async def get_interview_status(session_id: str):
    """Get current interview session status"""
    
    if session_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    interview_session = interview_sessions[session_id]
    
    completion_percent = min((interview_session.question_number / interview_session.max_questions) * 100, 100)
    
    return {
        "success": True,
        "session_id": session_id,
        "status": interview_session.status,
        "question_number": interview_session.question_number,
        "conversation_history": interview_session.conversation_history,
        "progress": {
            "current_question": interview_session.question_number,
            "max_questions": interview_session.max_questions,
            "unknown_count": interview_session.unknown_count,
            "max_unknowns": interview_session.max_unknowns,
            "completion_percent": completion_percent
        },
        "interview_complete": interview_session.status == InterviewStatus.COMPLETED
    }







# Comprehensive diagnostic endpoint
@router.get("/medical/debug-routes")
async def debug_routes():
    """Comprehensive diagnostic endpoint for voice-answer 404 troubleshooting"""
    import sys
    import inspect
    from fastapi import __version__ as fastapi_version
    
    # Get all registered routes in this router
    routes_info = []
    for route in router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes_info.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, 'name', 'unknown')
            })
    
    # Voice service moved to dedicated voice router
    voice_service_status = "moved_to_voice_router"
    
    # Check medical expert status
    medical_expert_status = "not_initialized" if medical_expert is None else "initialized"
    
    return {
        "fastapi_version": fastapi_version,
        "router_prefix": "/api",
        "total_routes": len(routes_info),
        "voice_routes": [r for r in routes_info if "voice" in r["path"]],
        "all_medical_routes": [r for r in routes_info if "/medical/" in r["path"]],
        "voice_service_status": voice_service_status,
        "medical_expert_status": medical_expert_status,
        "python_version": sys.version,
        "current_module": __name__,
        "voice_answer_function_exists": 'submit_voice_answer' in globals(),
        "voice_answer_signature": str(inspect.signature(submit_voice_answer)) if 'submit_voice_answer' in globals() else "not_found"
    }

# Simple test endpoint to verify router registration
@router.post("/medical/test-voice")
async def test_voice_endpoint():
    """Simple test endpoint to verify POST method registration"""
    return {"success": True, "message": "POST method working"}
