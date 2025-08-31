"""
Session management service for handling user sessions
"""

from typing import Dict, Optional
import uuid
from datetime import datetime, timedelta
from core.config import settings

# In-memory session storage (in production, use Redis or database)
sessions: Dict[str, dict] = {}

def create_session() -> str:
    """Create a new session and return session ID"""
    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "last_accessed": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(seconds=settings.session_timeout)).isoformat(),
        "patient_info": None,
        "current_page": "patient_form",
        "interview_session": None
    }
    sessions[session_id] = session_data
    return session_id

def get_session(session_id: str) -> Optional[dict]:
    """Get session data by session ID"""
    if session_id not in sessions:
        return None
    
    session = sessions[session_id]
    
    # Check if session is expired (with error handling)
    try:
        if "expires_at" in session:
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.now() > expires_at:
                del sessions[session_id]
                return None
    except Exception as e:
        print(f"Error checking session expiration: {e}")
        # Continue without expiration check if there's an issue
    
    # Update last accessed time
    session["last_accessed"] = datetime.now().isoformat()
    return session

def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get existing session or create new one"""
    if session_id and get_session(session_id):
        return session_id
    return create_session()

def update_session(session_id: str, data: dict) -> bool:
    """Update session data"""
    if session_id not in sessions:
        return False
    
    sessions[session_id].update(data)
    sessions[session_id]["last_accessed"] = datetime.now().isoformat()
    return True

def delete_session(session_id: str) -> bool:
    """Delete session"""
    if session_id in sessions:
        del sessions[session_id]
        return True
    return False

def cleanup_expired_sessions():
    """Remove expired sessions"""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, session_data in sessions.items():
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if current_time > expires_at:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del sessions[session_id]
    
    return len(expired_sessions)
