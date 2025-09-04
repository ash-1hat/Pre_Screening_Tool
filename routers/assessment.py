"""
Medical assessment API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.medical_expert_service import MedicalExpertService
from services.session_service import get_session, update_session
from services.export_service import export_service
from services.prescreening_service import prescreening_service
from datetime import datetime
from routers.medical import interview_sessions
from models.assessment import AssessmentRequest, AssessmentResponse

router = APIRouter()
medical_expert = MedicalExpertService()

@router.post("/assessment/generate", response_model=AssessmentResponse)
async def generate_medical_assessment(request: AssessmentRequest):
    """Generate final medical assessment based on interview"""
    
    print(f"[ASSESSMENT_DEBUG] Received request: session_id={request.session_id}, patient_id={request.patient_id}")
    print(f"[ASSESSMENT_DEBUG] Available interview sessions: {list(interview_sessions.keys())}")
    
    # Get interview session
    if request.session_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    interview_session = interview_sessions[request.session_id]
    
    if not interview_session.conversation_history:
        raise HTTPException(status_code=400, detail="No interview data available")
    
    # Get patient info
    session = await get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    patient_info = session.get("patient_info")
    if not patient_info:
        raise HTTPException(status_code=400, detail="Patient information not found")
    
    try:
        # Generate assessment using medical expert AI with state management
        assessment_result = await medical_expert.generate_final_assessment(
            patient=patient_info,
            conversation_history=[qa.dict() for qa in interview_session.conversation_history],
            previous_response_id=interview_session.current_response_id
        )
        
        if not assessment_result or not assessment_result.get("assessment"):
            raise HTTPException(status_code=500, detail="Failed to generate assessment")
        
        assessment = assessment_result["assessment"]
        confidence_percentage = assessment_result.get("confidence_level", 50)
        recommended_department = assessment_result.get("recommended_department", "General Medicine")
        reasoning_tokens = assessment_result.get("reasoning_tokens", 0)
        
        # Update interview session with assessment response ID
        interview_session.previous_response_id = interview_session.current_response_id
        interview_session.current_response_id = assessment_result.get("response_id")
        interview_session.total_reasoning_tokens += reasoning_tokens
        
        # Determine confidence level and action based on percentage
        if confidence_percentage >= 70:
            confidence_level = "High"
            recommended_action = f"Proceed to {recommended_department} specialist"
        elif confidence_percentage >= 40:
            confidence_level = "Medium" 
            recommended_action = f"Consider consultation with {recommended_department}"
        else:
            confidence_level = "Low"
            recommended_action = "Visit hospital reception for general consultation"
        
        # Generate and print JSON export data
        try:
            # Get doctor recommendations from the assessment result
            doctor_recs = assessment_result.get("department_recommendations", {})
            
            export_data = export_service.generate_assessment_json(
                patient_info=patient_info,
                assessment_data={
                    "investigative_history": assessment.investigative_history,
                    "possible_diagnosis": assessment.possible_diagnosis
                },
                doctor_recommendations=doctor_recs,
                diagnostics_result={
                    "matched_condition": assessment_result.get("matched_diagnostic_condition"),
                    "diagnostics": assessment_result.get("pre_consultation_diagnostics", {})
                }
            )
            export_service.print_assessment_json(export_data)
        except Exception as e:
            print(f"[EXPORT_ERROR] Failed to generate export data: {e}")
            import traceback
            traceback.print_exc()
        
        # Collect pre-screening data
        try:
            # Determine visit type based on session data
            selected_doctor_choice = session.get("selected_doctor_choice", {})
            
            # Check for different visit types based on session data
            selection_type = selected_doctor_choice.get("type") or selected_doctor_choice.get("selection_type")
            if selection_type == "followup":
                visit_type = "follow-up"
            elif selection_type == "new" or selected_doctor_choice.get("doctor_name"):
                visit_type = "new-doctor"
            else:
                visit_type = "ai-help"  # Default for medical assessment endpoint
            
            print(f"[ASSESSMENT_DEBUG] Visit type determined: {visit_type}")
            print(f"[ASSESSMENT_DEBUG] Selected doctor choice: {selected_doctor_choice}")
            
            prescreening_data = prescreening_service.collect_prescreening_data(
                session_data={
                    "patient_info": patient_info,
                    "consultation_data": session.get("consultation_data", {}),
                    "selected_doctor_choice": selected_doctor_choice
                },
                assessment_result={
                    "investigative_history": assessment_result.get("investigative_history", assessment.investigative_history),
                    "possible_diagnosis": assessment.possible_diagnosis,
                    "recommended_department": recommended_department,
                    "recommended_doctors": doctor_recs.get("recommended_doctors", [])
                },
                diagnostics_result={
                    "diagnostics": assessment_result.get("pre_consultation_diagnostics", {})
                },
                conversation_history=[qa.dict() for qa in interview_session.conversation_history],
                visit_type=visit_type
            )
            
            # Store pre-screening data in session for later acceptance
            session["prescreening_data"] = prescreening_data
            
            # Update session in database
            await update_session(request.session_id, session)
            
            # Print pre-screening JSON to terminal
            prescreening_service.print_prescreening_json(prescreening_data)
            
        except Exception as e:
            print(f"[PRESCREENING_ERROR] Failed to collect pre-screening data: {e}")
            import traceback
            traceback.print_exc()
        
        # Update session storage with AI assessment results
        try:
            session["ai_assessment_results"] = {
                "ai_suggested_department": assessment_result.get("recommended_department"),
                "ai_suggested_doctor": assessment_result.get("recommended_doctor"),
                "department_recommendations": doctor_recs,
                "assessment_timestamp": datetime.now().isoformat()
            }
            
            # Update session in database with AI assessment results
            await update_session(request.session_id, session)
            
            print(f"[SESSION_UPDATE] Updated session with AI recommendations: dept={assessment_result.get('recommended_department')}, doctor={assessment_result.get('recommended_doctor')}")
        except Exception as e:
            print(f"[SESSION_ERROR] Failed to update session with AI recommendations: {e}")
        
        return AssessmentResponse(
            success=True,
            message="Medical assessment generated successfully",
            assessment=assessment,
            session_id=request.session_id,
            confidence_level=confidence_level,
            recommended_action=recommended_action,
            recommended_doctor=assessment_result.get("recommended_doctor"),
            recommended_department=assessment_result.get("recommended_department"),
            doctor_comparison_analysis=assessment_result.get("doctor_comparison_analysis"),
            pre_consultation_diagnostics=assessment_result.get("pre_consultation_diagnostics"),
            matched_diagnostic_condition=assessment_result.get("matched_diagnostic_condition"),
            diagnostics_explanation=assessment_result.get("diagnostics_explanation")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment generation failed: {str(e)}")

@router.get("/assessment/{session_id}")
async def get_assessment(session_id: str):
    """Get existing assessment for a session"""
    
    # Check if interview session exists and is completed
    if session_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    interview_session = interview_sessions[session_id]
    
    return {
        "success": True,
        "session_id": session_id,
        "interview_complete": interview_session.status.value == "completed",
        "conversation_history": interview_session.conversation_history,
        "question_count": len(interview_session.conversation_history),
        "status": interview_session.status.value
    }
