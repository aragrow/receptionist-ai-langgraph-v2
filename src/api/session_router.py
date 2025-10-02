# ==================== src/api/session_router.py ====================

"""
Session Management Router

Handles session CRUD operations and conversation exports.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger("ai_receptionist.session_router")

router = APIRouter()


# ============ Response Models ============

class SessionInfoResponse(BaseModel):
    """Response model for session information"""
    
    session_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    current_tier: Optional[str] = None
    current_agent: Optional[str] = None
    turn_count: int
    caller_type: Optional[str] = None
    caller_phone: Optional[str] = None
    conversation_turns: int
    routing_path: list
    requires_escalation: bool


# ============ Dependency Injection ============

def get_services():
    """Get services from main.py"""
    from main import services
    return services


# ============ Endpoints ============

@router.get("/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(
    session_id: str,
    services=Depends(get_services)
):
    """
    Get information about a specific session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session information including conversation history and routing
    """
    logger.info(f"📊 Retrieving session info: {session_id}")
    
    try:
        session_info = await services.session_service.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )
        
        return SessionInfoResponse(
            session_id=session_info["session_id"],
            created_at=session_info["created_at"],
            updated_at=session_info["updated_at"],
            current_tier=session_info["current_tier"],
            current_agent=session_info["current_agent"],
            turn_count=session_info["turn_count"],
            caller_type=session_info["caller_type"],
            caller_phone=session_info["caller_phone"],
            conversation_turns=session_info["conversation_turns"],
            routing_path=session_info["routing_path"],
            requires_escalation=session_info["requires_human_escalation"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get session info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session info: {str(e)}"
        )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    services=Depends(get_services)
):
    """
    Delete a specific session.
    
    Args:
        session_id: Session identifier to delete
    
    Returns:
        Confirmation of deletion
    """
    logger.info(f"🗑️ Deleting session: {session_id}")
    
    try:
        deleted = await services.session_service.delete_session(session_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )
        
        return {
            "success": True,
            "message": f"Session {session_id} deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/{session_id}/export")
async def export_session(
    session_id: str,
    include_metadata: bool = True,
    services=Depends(get_services)
):
    """
    Export a complete conversation transcript.
    
    Args:
        session_id: Session identifier
        include_metadata: Include routing and state metadata (default: True)
    
    Returns:
        Complete conversation export
    """
    logger.info(f"📤 Exporting session: {session_id}")
    
    try:
        export = await services.session_service.export_conversation(
            session_id=session_id,
            include_metadata=include_metadata
        )
        
        if not export:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )
        
        return export
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to export session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export session: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_sessions(services=Depends(get_services)):
    """
    Manually trigger cleanup of expired sessions.
    
    Returns:
        Number of sessions cleaned up
    """
    logger.info("🧹 Manual session cleanup triggered")
    
    try:
        count = await services.session_service.cleanup_expired_sessions()
        
        return {
            "success": True,
            "sessions_cleaned": count,
            "message": f"Cleaned up {count} expired session(s)"
        }
    
    except Exception as e:
        logger.error(f"❌ Session cleanup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Session cleanup failed: {str(e)}"
        )