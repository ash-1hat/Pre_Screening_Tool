"""
Follow-up Interview API Router
Handles follow-up interviews for returning patients (Option 1)
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
import uuid
from datetime import datetime
from typing import Dict, List

from models.medical import (
    QuestionRequest, QuestionResponse, AnswerSubmission, 
    AnswerResponse, InterviewSession, QuestionAnswer, InterviewStatus
)
from services.followup_service import followup_service
from services.session_service import sessions, get_session, update_session
from services.supabase_service import supabase_service
from services.prescreening_service import prescreening_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for follow-up interview sessions
followup_interview_sessions: Dict[str, InterviewSession] = {}

@router.post("/followup/start-interview", response_model=QuestionResponse)
async def start_followup_interview(request: QuestionRequest):
    """Start a new follow-up interview session"""
    
    try:
        logger.info(f"🔄 [FOLLOWUP] Starting follow-up interview for session: {request.session_id}")
        
        # Get patient session
        session = await get_session(request.session_id)
        if not session:
            logger.error(f"❌ [FOLLOWUP] Session not found: {request.session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"📋 [FOLLOWUP] Session data keys: {session.keys()}")
        patient_info = session.get("patient_info")
        if not patient_info:
            logger.error(f"❌ [FOLLOWUP] Patient information not found in session")
            raise HTTPException(status_code=400, detail="Patient information not found")
        
        # Get doctor selection info (optional validation - allow if not set)
        selected_doctor_choice = session.get("selected_doctor_choice", {})
        logger.info(f"🩺 [FOLLOWUP] Doctor choice validation: {selected_doctor_choice}")
        
        # Skip validation if doctor choice not set (for backward compatibility)
        if selected_doctor_choice and selected_doctor_choice.get("type") not in ["followup", None]:
            logger.warning(f"⚠️ [FOLLOWUP] Non-followup selection type: {selected_doctor_choice.get('type')}, but allowing")
        
        logger.info(f"👤 [FOLLOWUP] Patient info: {patient_info}")
        logger.info(f"🩺 [FOLLOWUP] Doctor choice: {selected_doctor_choice}")
        
        # Get previous medical record from consultation data (optional for testing)
        consultation_data = session.get("consultation_data")
        if not consultation_data:
            logger.warning(f"⚠️ [FOLLOWUP] No previous consultation data found, using fallback")
            consultation_data = {"raw_pradhi_response": "{}", "consultation_date": "2025-08-25", "doctor_name": "Previous Doctor", "doctor_specialty": "General Medicine"}
        
        logger.info(f"📊 [FOLLOWUP] Consultation data keys: {list(consultation_data.keys()) if consultation_data else 'None'}")
        
        # Extract previous medical record from raw_pradhi_response
        previous_medical_record = "Previous consultation data available"
        if consultation_data.get("raw_pradhi_response"):
            try:
                import json
                pradhi_data = consultation_data["raw_pradhi_response"]
                if isinstance(pradhi_data, str):
                    pradhi_data = json.loads(pradhi_data)
                
                # Format previous medical record for follow-up service
                previous_medical_record = f"""
Previous Consultation Date: {consultation_data.get('consultation_date', 'N/A')}
Doctor: {consultation_data.get('doctor_name', 'N/A')}
Diagnosis: {pradhi_data.get('insights', {}).get('Diagnosis', ['N/A'])[0] if pradhi_data.get('insights', {}).get('Diagnosis') else 'N/A'}
Prescription Data: {pradhi_data.get('prescription_data', [])}
Investigation: {pradhi_data.get('investigation', [])}
Next Steps: {pradhi_data.get('next_steps', [])}
Associated Symptoms: {pradhi_data.get('associated_symptoms', [])}
                """.strip()
                
                logger.info(f"📝 [FOLLOWUP] Formatted previous medical record")
                
            except Exception as e:
                logger.error(f"❌ [FOLLOWUP] Error parsing previous medical record: {e}")
                previous_medical_record = f"Previous consultation on {consultation_data.get('consultation_date', 'N/A')} with {consultation_data.get('doctor_name', 'N/A')}"
        
        # Create interview session
        current_time = datetime.now().isoformat()
        interview_session = InterviewSession(
            session_id=request.session_id,
            patient_id=request.patient_id,
            status=InterviewStatus.ACTIVE,
            conversation_history=[],
            question_number=1,
            unknown_count=0,
            created_at=current_time,
            updated_at=current_time,
            expires_at=None,
            max_questions=6,  # Follow-up interviews have 6 questions
            max_unknowns=3
        )
        
        followup_interview_sessions[request.session_id] = interview_session
        logger.info(f"✅ [FOLLOWUP] Interview session created and stored")
        
        # Generate first follow-up question
        try:
            first_question = followup_service.generate_followup_question(
                patient_age=patient_info.get("age", 0),
                patient_gender=patient_info.get("gender", ""),
                doctor_department=selected_doctor_choice.get("doctor_specialty", "General Medicine"),
                last_consultation_date=consultation_data.get("consultation_date", ""),
                previous_medical_record=previous_medical_record,
                question_number=1,
                conversation_history=""
            )
            
            logger.info(f"❓ [FOLLOWUP] Generated first question: {first_question[:100]}...")
            
        except Exception as e:
            logger.error(f"❌ [FOLLOWUP] Error generating first question: {e}")
            first_question = "How are you feeling since your last visit?"
        
        # Store the first question for next answer submission
        interview_session.last_question_asked = first_question
        
        return QuestionResponse(
            success=True,
            question=first_question,
            question_number=1,
            progress={
                "current_question": 1,
                "max_questions": 6,
                "unknown_count": 0,
                "max_unknowns": 3,
                "completion_percent": 0
            },
            interview_complete=False,
            response_id=None,
            reasoning_tokens=0
        )
        logger.info(f"🩺 [FOLLOWUP] Doctor choice validation: {selected_doctor_choice}")
        
        # Skip validation if doctor choice not set (for backward compatibility)
        if selected_doctor_choice and selected_doctor_choice.get("type") not in ["followup", None]:
            logger.warning(f"⚠️ [FOLLOWUP] Non-followup selection type: {selected_doctor_choice.get('type')}, but allowing")
        
        logger.info(f"👤 [FOLLOWUP] Patient info: {patient_info}")
        logger.info(f"🩺 [FOLLOWUP] Doctor choice: {selected_doctor_choice}")
        
        # Get previous medical record from consultation data (optional for testing)
        consultation_data = session.get("consultation_data")
        if not consultation_data:
            logger.warning(f"⚠️ [FOLLOWUP] No previous consultation data found, using fallback")
            consultation_data = {"raw_pradhi_response": "{}", "consultation_date": "2025-08-25", "doctor_name": "Previous Doctor", "doctor_specialty": "General Medicine"}
        
        logger.info(f"📊 [FOLLOWUP] Consultation data keys: {list(consultation_data.keys()) if consultation_data else 'None'}")
        
        # Extract previous medical record from raw_pradhi_response
        previous_medical_record = "Previous consultation data available"
        if consultation_data.get("raw_pradhi_response"):
            try:
                import json
                pradhi_data = consultation_data["raw_pradhi_response"]
                if isinstance(pradhi_data, str):
                    pradhi_data = json.loads(pradhi_data)
                
                # Format previous medical record for follow-up service
                previous_medical_record = f"""
Previous Consultation Date: {consultation_data.get('consultation_date', 'N/A')}
Doctor: {consultation_data.get('doctor_name', 'N/A')}
Diagnosis: {pradhi_data.get('insights', {}).get('Diagnosis', ['N/A'])[0] if pradhi_data.get('insights', {}).get('Diagnosis') else 'N/A'}
Prescription Data: {pradhi_data.get('prescription_data', [])}
Investigation: {pradhi_data.get('investigation', [])}
Next Steps: {pradhi_data.get('next_steps', [])}
Associated Symptoms: {pradhi_data.get('associated_symptoms', [])}
                """.strip()
                
                logger.info(f"📝 [FOLLOWUP] Formatted previous medical record")
                
            except Exception as e:
                logger.error(f"❌ [FOLLOWUP] Error parsing previous medical record: {e}")
                previous_medical_record = f"Previous consultation on {consultation_data.get('consultation_date', 'N/A')} with {consultation_data.get('doctor_name', 'N/A')}"
        
        # Create interview session
        current_time = datetime.now().isoformat()
        interview_session = InterviewSession(
            session_id=request.session_id,
            patient_id=request.patient_id,
            status=InterviewStatus.ACTIVE,
            conversation_history=[],
            question_number=1,
            unknown_count=0,
            created_at=current_time,
            updated_at=current_time,
            expires_at=None,
            max_questions=6,  # Follow-up interviews have 6 questions
            max_unknowns=3
        )
        
        followup_interview_sessions[request.session_id] = interview_session
        logger.info(f"✅ [FOLLOWUP] Interview session created and stored")
        
        # Generate first follow-up question
        try:
            first_question = followup_service.generate_followup_question(
                patient_age=patient_info.get("age", 0),
                patient_gender=patient_info.get("gender", ""),
                doctor_department=selected_doctor_choice.get("doctor_specialty", "General Medicine"),
                last_consultation_date=consultation_data.get("consultation_date", ""),
                previous_medical_record=previous_medical_record,
                question_number=1,
                conversation_history=""
            )
            
            logger.info(f"❓ [FOLLOWUP] Generated first question: {first_question[:100]}...")
            
        except Exception as e:
            logger.error(f"❌ [FOLLOWUP] Error generating first question: {e}")
            first_question = "How are you feeling since your last visit?"
        
        # Store the first question for next answer submission
        interview_session.last_question_asked = first_question
        
        return QuestionResponse(
            success=True,
            question=first_question,
            question_number=1,
            progress={
                "current_question": 1,
                "max_questions": 6,
                "unknown_count": 0,
                "max_unknowns": 3,
                "completion_percent": 0
            },
            interview_complete=False,
            response_id=None,
            reasoning_tokens=0
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [FOLLOWUP] Error in start_followup_interview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start follow-up interview: {str(e)}")

@router.post("/followup/submit-answer", response_model=AnswerResponse)
async def submit_followup_answer(submission: AnswerSubmission):
    """Submit patient answer and get next follow-up question"""
    
    logger.info(f"📝 [FOLLOWUP] Submit answer for session: {submission.session_id}")
    logger.info(f"💬 [FOLLOWUP] Answer: {submission.answer}")
    
    # Get interview session
    if submission.session_id not in followup_interview_sessions:
        logger.error(f"❌ [FOLLOWUP] Interview session not found: {submission.session_id}")
        raise HTTPException(status_code=404, detail="Follow-up interview session not found")
    
    interview_session = followup_interview_sessions[submission.session_id]
    logger.info(f"📊 [FOLLOWUP] Session status: {interview_session.status}, Question: {interview_session.question_number}")
    
    if interview_session.status != InterviewStatus.ACTIVE:
        logger.error(f"❌ [FOLLOWUP] Interview session not active: {interview_session.status}")
        raise HTTPException(status_code=400, detail="Follow-up interview session is not active")
    
    # Get patient and consultation info from main session
    session = await get_session(submission.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    patient_info = session.get("patient_info")
    consultation_data = session.get("consultation_data")
    selected_doctor_choice = session.get("selected_doctor_choice", {})
    
    # Store the Q&A pair
    current_question = interview_session.last_question_asked or "How are you feeling since your last visit?"
    qa_pair = QuestionAnswer(
        question=current_question,
        answer=submission.answer.strip(),
        timestamp=datetime.now().isoformat()
    )
    interview_session.conversation_history.append(qa_pair)
    
    # Check for "I don't know" responses
    if "don't know" in submission.answer.lower() or "not sure" in submission.answer.lower():
        interview_session.unknown_count += 1
        logger.info(f"🤷 [FOLLOWUP] Unknown response detected. Count: {interview_session.unknown_count}")
    
    # Check stopping conditions - early completion after 4 questions if sufficient info
    max_questions_reached = interview_session.question_number >= 6
    early_completion_possible = interview_session.question_number >= 4
    too_many_unknowns = interview_session.unknown_count >= 3
    
    # Check if we have sufficient information for early completion
    has_treatment_info = any("medic" in qa.question.lower() or "treatment" in qa.question.lower() for qa in interview_session.conversation_history)
    has_symptom_info = any("feel" in qa.question.lower() or "symptom" in qa.question.lower() for qa in interview_session.conversation_history)
    early_completion_ready = early_completion_possible and has_treatment_info and has_symptom_info
    
    logger.info(f"🔍 [FOLLOWUP] Max questions: {max_questions_reached} ({interview_session.question_number}/6)")
    logger.info(f"🔍 [FOLLOWUP] Early completion ready: {early_completion_ready} (Q{interview_session.question_number})")
    logger.info(f"🔍 [FOLLOWUP] Too many unknowns: {too_many_unknowns} ({interview_session.unknown_count}/3)")
    
    if max_questions_reached or too_many_unknowns or early_completion_ready:
        logger.info(f"✅ [FOLLOWUP] Interview complete - generating assessment")
        interview_session.status = InterviewStatus.COMPLETED
        interview_session.updated_at = datetime.now().isoformat()
        
        return AnswerResponse(
            success=True,
            message="Follow-up interview completed. Ready for assessment.",
            next_question=None,
            question_number=interview_session.question_number,
            progress={
                "current_question": interview_session.question_number,
                "max_questions": 6,
                "unknown_count": interview_session.unknown_count,
                "max_unknowns": 3,
                "completion_percent": 100
            },
            interview_complete=True,
            response_id=None,
            reasoning_tokens=0
        )
    
    # Generate next question
    interview_session.question_number += 1
    
    # Build conversation history for context
    conversation_history = "\n".join([
        f"Q{i+1}: {qa.question}\nA{i+1}: {qa.answer}"
        for i, qa in enumerate(interview_session.conversation_history)
    ])
    
    # Extract previous medical record again for context
    previous_medical_record = "Previous consultation data available"
    if consultation_data and consultation_data.get("raw_pradhi_response"):
        try:
            import json
            pradhi_data = consultation_data["raw_pradhi_response"]
            if isinstance(pradhi_data, str):
                pradhi_data = json.loads(pradhi_data)
            
            previous_medical_record = f"""
Previous Consultation Date: {consultation_data.get('consultation_date', 'N/A')}
Doctor: {consultation_data.get('doctor_name', 'N/A')}
Diagnosis: {pradhi_data.get('insights', {}).get('Diagnosis', ['N/A'])[0] if pradhi_data.get('insights', {}).get('Diagnosis') else 'N/A'}
Prescription Data: {pradhi_data.get('prescription_data', [])}
Investigation: {pradhi_data.get('investigation', [])}
Next Steps: {pradhi_data.get('next_steps', [])}
Associated Symptoms: {pradhi_data.get('associated_symptoms', [])}
            """.strip()
            
        except Exception as e:
            logger.error(f"❌ [FOLLOWUP] Error parsing medical record for next question: {e}")
    
    try:
        next_question = followup_service.generate_followup_question(
            patient_age=patient_info.get("age", 0),
            patient_gender=patient_info.get("gender", ""),
            doctor_department=selected_doctor_choice.get("doctor_specialty", "General Medicine"),
            last_consultation_date=consultation_data.get("consultation_date", ""),
            previous_medical_record=previous_medical_record,
            question_number=interview_session.question_number,
            conversation_history=conversation_history
        )
        
        logger.info(f"❓ [FOLLOWUP] Generated question {interview_session.question_number}: {next_question[:100]}...")
        
    except Exception as e:
        logger.error(f"❌ [FOLLOWUP] Error generating next question: {e}")
        next_question = "Can you tell me more about how you've been feeling?"
    
    # Store the question for next submission
    interview_session.last_question_asked = next_question
    interview_session.updated_at = datetime.now().isoformat()
    
    completion_percent = min((interview_session.question_number / 6) * 100, 100)
    
    logger.info(f"📊 [FOLLOWUP] Progress: {completion_percent}%")
    
    return AnswerResponse(
        success=True,
        message="Answer recorded successfully",
        next_question=next_question,
        question_number=interview_session.question_number,
        progress={
            "current_question": interview_session.question_number,
            "max_questions": 6,
            "unknown_count": interview_session.unknown_count,
            "max_unknowns": 3,
            "completion_percent": completion_percent
        },
        interview_complete=False,
        response_id=None,
        reasoning_tokens=0
    )

@router.get("/followup/interview/{session_id}")
async def get_followup_interview_status(session_id: str):
    """Get current follow-up interview session status"""
    
    if session_id not in followup_interview_sessions:
        raise HTTPException(status_code=404, detail="Follow-up interview session not found")
    
    interview_session = followup_interview_sessions[session_id]
    
    completion_percent = min((interview_session.question_number / 6) * 100, 100)
    
    return {
        "success": True,
        "session_id": session_id,
        "status": interview_session.status,
        "question_number": interview_session.question_number,
        "conversation_history": interview_session.conversation_history,
        "progress": {
            "current_question": interview_session.question_number,
            "max_questions": 6,
            "unknown_count": interview_session.unknown_count,
            "max_unknowns": 3,
            "completion_percent": completion_percent
        },
        "interview_complete": interview_session.status == InterviewStatus.COMPLETED
    }

@router.post("/followup/generate-assessment")
async def generate_followup_assessment(request: QuestionRequest):
    """Generate follow-up assessment based on completed interview"""
    
    try:
        logger.info(f"🔄 [FOLLOWUP] Generating assessment for session: {request.session_id}")
        
        # Get interview session
        if request.session_id not in followup_interview_sessions:
            logger.error(f"❌ [FOLLOWUP] Interview session not found: {request.session_id}")
            raise HTTPException(status_code=404, detail="Follow-up interview session not found")
        
        interview_session = followup_interview_sessions[request.session_id]
        
        if interview_session.status != InterviewStatus.COMPLETED:
            logger.error(f"❌ [FOLLOWUP] Interview not completed: {interview_session.status}")
            raise HTTPException(status_code=400, detail="Interview must be completed before generating assessment")
        
        # Get patient session data
        session = await get_session(request.session_id)
        if not session:
            logger.error(f"❌ [FOLLOWUP] Session not found: {request.session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        patient_info = session.get("patient_info")
        consultation_data = session.get("consultation_data")
        
        if not patient_info:
            logger.error(f"❌ [FOLLOWUP] Patient information not found")
            raise HTTPException(status_code=400, detail="Patient information not found")
        
        # Build interview responses
        interview_responses = "\n".join([
            f"Q{i+1}: {qa.question}\nA{i+1}: {qa.answer}"
            for i, qa in enumerate(interview_session.conversation_history)
        ])
        
        # Extract previous visit summary
        previous_visit_summary = "Previous consultation data available"
        chief_complaint = "Follow-up visit"
        
        if consultation_data and consultation_data.get("raw_pradhi_response"):
            try:
                import json
                pradhi_data = consultation_data["raw_pradhi_response"]
                if isinstance(pradhi_data, str):
                    pradhi_data = json.loads(pradhi_data)
                
                diagnosis = pradhi_data.get('insights', {}).get('Diagnosis', ['N/A'])
                chief_complaint = diagnosis[0] if diagnosis else "Follow-up visit"
                
                previous_visit_summary = f"""
Previous Visit Date: {consultation_data.get('consultation_date', 'N/A')}
Doctor: {consultation_data.get('doctor_name', 'N/A')}
Diagnosis: {chief_complaint}
Treatment Plan: {pradhi_data.get('insights', {}).get('Treatment Plan', [])}
Prescription: {pradhi_data.get('insights', {}).get('Prescription Data', [])}
                """.strip()
                
            except Exception as e:
                logger.error(f"❌ [FOLLOWUP] Error parsing previous visit data: {e}")
        
        logger.info(f"📝 [FOLLOWUP] Generating assessment with followup service")
        
        # Generate assessment using followup service
        assessment_result = followup_service.generate_followup_assessment(
            patient_age=patient_info.get("age", 0),
            patient_gender=patient_info.get("gender", ""),
            chief_complaint=chief_complaint,
            previous_visit_summary=previous_visit_summary,
            follow_up_interview=interview_responses
        )
        
        logger.info(f"✅ [FOLLOWUP] Assessment generated successfully")
        
        # Collect pre-screening data
        try:
            prescreening_data = prescreening_service.collect_prescreening_data(
                session_data={
                    "patient_info": patient_info,
                    "consultation_data": consultation_data,
                    "selected_doctor_choice": {}  # Follow-up doesn't have new doctor selection
                },
                assessment_result=assessment_result,
                diagnostics_result={"diagnostics": {}},  # Follow-up may not have diagnostics
                conversation_history=[qa.__dict__ for qa in interview_session.conversation_history],
                visit_type="follow-up"
            )
            
            # Store pre-screening data in session for later acceptance
            session["prescreening_data"] = prescreening_data
            
            # Update session in database
            await update_session(request.session_id, session)
            
            # Print pre-screening JSON to terminal
            prescreening_service.print_prescreening_json(prescreening_data)
            
        except Exception as e:
            logger.error(f"❌ [FOLLOWUP] Error collecting pre-screening data: {e}")
        
        return {
            "success": True,
            "assessment": assessment_result.get("investigative_history", ""),
            "possible_diagnosis": assessment_result.get("possible_diagnosis", "Assessment based on follow-up interview"),
            "confidence_level": "High",
            "interview_complete": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [FOLLOWUP] Error generating assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate follow-up assessment: {str(e)}")
