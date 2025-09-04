"""
Session management service for handling user sessions
"""

from typing import Dict, Optional
import uuid
import json
from datetime import datetime, timedelta
from core.config import settings
from services.supabase_service import supabase_service
import logging

logger = logging.getLogger(__name__)

# Keep in-memory sessions as fallback for local development
sessions: Dict[str, dict] = {}

async def create_session() -> str:
    """Create a new session and return session ID"""
    session_id = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(seconds=settings.session_timeout)
    
    session_data = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "last_accessed": datetime.now().isoformat(),
        "expires_at": expires_at.isoformat(),
        "patient_info": None,
        "current_page": "patient_form",
        "interview_session": None
    }
    
    try:
        # Store in database
        supabase_service.client.table('pre_screening_session').insert({
            'session_id': session_id,
            'session_data': session_data,
            'expires_at': expires_at.isoformat()
        }).execute()
        
    except Exception as e:
        logger.warning(f"Database session creation failed: {e}, using memory storage")
        # Fallback to in-memory storage
        sessions[session_id] = session_data
    
    return session_id

async def get_session(session_id: str) -> Optional[dict]:
    """Get session data by session ID from database"""
    try:
        # Try database first
        response = supabase_service.client.table('pre_screening_session').select('*').eq('session_id', session_id).single().execute()
        
        if response.data:
            session_data = response.data
            
            # Check if session is expired
            expires_at = datetime.fromisoformat(session_data['expires_at'].replace('Z', '+00:00'))
            if datetime.now() > expires_at.replace(tzinfo=None):
                # Delete expired session
                supabase_service.client.table('pre_screening_session').delete().eq('session_id', session_id).execute()
                return None
            
            # Update last accessed time
            supabase_service.client.table('pre_screening_session').update({
                'updated_at': datetime.now().isoformat()
            }).eq('session_id', session_id).execute()
            
            # Return session data in expected format
            session = session_data['session_data']
            session['last_accessed'] = datetime.now().isoformat()
            return session
            
    except Exception as e:
        logger.warning(f"Database session lookup failed: {e}, falling back to memory")
    
    # Fallback to in-memory sessions (for local development)
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
        logger.error(f"Error checking session expiration: {e}")
    
    # Update last accessed time
    session["last_accessed"] = datetime.now().isoformat()
    return session

async def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get existing session or create new one"""
    if session_id and await get_session(session_id):
        return session_id
    return await create_session()

async def update_session(session_id: str, data: dict) -> bool:
    """Update session data in database"""
    try:
        # Try database first
        existing_session = await get_session(session_id)
        if existing_session:
            # Update existing session data
            updated_data = existing_session.copy()
            updated_data.update(data)
            updated_data["last_accessed"] = datetime.now().isoformat()
            
            supabase_service.client.table('pre_screening_session').update({
                'session_data': updated_data
            }).eq('session_id', session_id).execute()
            
            return True
            
    except Exception as e:
        logger.warning(f"Database session update failed: {e}, falling back to memory")
    
    # Fallback to in-memory sessions
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
