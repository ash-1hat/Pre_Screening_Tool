"""
Follow-up Assessment API Router
Handles assessment generation for follow-up interviews
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict

from services.followup_service import followup_service
from services.session_service import sessions, get_session
from routers.followup import followup_interview_sessions
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/followup/generate-assessment")
async def generate_followup_assessment(request: dict):
    """Generate follow-up assessment after interview completion"""
    
    try:
        session_id = request.get("session_id")
        patient_id = request.get("patient_id")
        
        logger.info(f"🔄 [FOLLOWUP_ASSESSMENT] Generating assessment for session: {session_id}")
        
        # Get main session data
        session = await get_session(session_id)
        if not session:
            logger.error(f"❌ [FOLLOWUP_ASSESSMENT] Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get interview session
        if session_id not in followup_interview_sessions:
            logger.error(f"❌ [FOLLOWUP_ASSESSMENT] Follow-up interview session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Follow-up interview session not found")
        
        interview_session = followup_interview_sessions[session_id]
        
        # Verify interview is complete
        if interview_session.status.value != "completed":
            logger.error(f"❌ [FOLLOWUP_ASSESSMENT] Interview not completed: {interview_session.status}")
            raise HTTPException(status_code=400, detail="Follow-up interview not completed")
        
        patient_info = session.get("patient_info", {})
        consultation_data = session.get("consultation_data", {})
        
        # Build follow-up interview data
        follow_up_interview = "\n".join([
            f"Q{i+1}: {qa.question}\nA{i+1}: {qa.answer}"
            for i, qa in enumerate(interview_session.conversation_history)
        ])
        
        # Extract chief complaint from previous consultation
        chief_complaint = "Follow-up visit"
        if consultation_data.get("raw_pradhi_response"):
            try:
                import json
                pradhi_data = consultation_data["raw_pradhi_response"]
                if isinstance(pradhi_data, str):
                    pradhi_data = json.loads(pradhi_data)
                
                # Try to get chief complaint from previous data
                if pradhi_data.get("insights", {}).get("Diagnosis"):
                    chief_complaint = f"Follow-up for {pradhi_data['insights']['Diagnosis'][0]}"
                
            except Exception as e:
                logger.error(f"❌ [FOLLOWUP_ASSESSMENT] Error parsing chief complaint: {e}")
        
        # Format previous visit summary
        previous_visit_summary = f"""
Previous Consultation Date: {consultation_data.get('consultation_date', 'N/A')}
Doctor: {consultation_data.get('doctor_name', 'N/A')}
Department: {consultation_data.get('doctor_specialty', 'N/A')}
        """.strip()
        
        if consultation_data.get("raw_pradhi_response"):
            try:
                import json
                pradhi_data = consultation_data["raw_pradhi_response"]
                if isinstance(pradhi_data, str):
                    pradhi_data = json.loads(pradhi_data)
                
                previous_visit_summary += f"""
Diagnosis: {pradhi_data.get('insights', {}).get('Diagnosis', ['N/A'])[0] if pradhi_data.get('insights', {}).get('Diagnosis') else 'N/A'}
Prescription: {len(pradhi_data.get('prescription_data', []))} medications prescribed
Investigation: {len(pradhi_data.get('investigation', []))} tests ordered
                """.strip()
                
            except Exception as e:
                logger.error(f"❌ [FOLLOWUP_ASSESSMENT] Error parsing previous visit summary: {e}")
        
        logger.info(f"📊 [FOLLOWUP_ASSESSMENT] Generating assessment with followup service")
        
        # Generate follow-up assessment
        assessment_result = followup_service.generate_followup_assessment(
            patient_age=patient_info.get("age", 0),
            patient_gender=patient_info.get("gender", ""),
            chief_complaint=chief_complaint,
            previous_visit_summary=previous_visit_summary,
            follow_up_interview=follow_up_interview
        )
        
        logger.info(f"✅ [FOLLOWUP_ASSESSMENT] Assessment generated successfully")
        
        # Format response for frontend
        response = {
            "success": True,
            "assessment_type": "followup",
            "assessment": {
                "investigative_history": assessment_result.get("investigative_history", ""),
                "possible_diagnosis": assessment_result.get("comparative_diagnosis", {}).get("current_status", "")
            },
            "confidence_level": "High",  # Follow-up assessments are generally high confidence
            "recommended_action": "Continue with follow-up care as planned",
            "followup_specific_data": {
                "comparative_diagnosis": assessment_result.get("comparative_diagnosis", {}),
                "treatment_adherence_analysis": assessment_result.get("treatment_adherence_analysis", {}),
                "pending_diagnostics": assessment_result.get("pending_diagnostics", []),
                "symptom_progression": assessment_result.get("symptom_progression", {}),
                "followup_recommendations": assessment_result.get("followup_recommendations", [])
            },
            "interview_summary": {
                "total_questions": len(interview_session.conversation_history),
                "unknown_responses": interview_session.unknown_count,
                "completion_time": interview_session.updated_at
            }
        }
        
        # Store assessment in session
        session["followup_assessment"] = response
        
        logger.info(f"📋 [FOLLOWUP_ASSESSMENT] Assessment stored in session")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [FOLLOWUP_ASSESSMENT] Error generating assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate follow-up assessment: {str(e)}")

@router.get("/followup/assessment/{session_id}")
async def get_followup_assessment(session_id: str):
    """Get stored follow-up assessment"""
    
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        assessment = session.get("followup_assessment")
        if not assessment:
            raise HTTPException(status_code=404, detail="Follow-up assessment not found")
        
        return assessment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [FOLLOWUP_ASSESSMENT] Error retrieving assessment: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve follow-up assessment")
