# ==================== src/api/call_router.py ====================

"""
Call Processing Router

Handles incoming call processing through the AI Receptionist workflow.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger("ai_receptionist.call_router")

router = APIRouter()


# ============ Request/Response Models ============

class CallRequest(BaseModel):
    """Request model for call processing"""
    
    caller_phone: str = Field(..., description="Caller's phone number")
    speech_text: str = Field(..., description="Transcribed speech from caller")
    call_sid: str = Field(..., description="Unique call identifier")
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for continuing conversation"
    )


class CallResponse(BaseModel):
    """Response model for call processing"""
    
    success: bool
    session_id: str = Field(..., description="Session ID for this conversation")
    caller_type: Optional[str] = None
    intent: Optional[str] = None
    response: str
    next_action: Optional[str] = None
    current_tier: Optional[str] = None
    turn_count: int = 0
    requires_escalation: bool = False
    ticket_id: Optional[str] = None
    error: Optional[str] = None


# ============ Dependency Injection ============

def get_services():
    """Get services from main.py"""
    from main import services
    return services


# ============ Endpoints ============

@router.post("/process-call", response_model=CallResponse)
async def process_call(
    request: CallRequest,
    background_tasks: BackgroundTasks,
    services=Depends(get_services)
):
    """
    Process an incoming call through the AI Receptionist workflow.
    
    Supports multi-turn conversations with automatic session management.
    
    Args:
        request: Call request with phone, text, and optional session_id
        background_tasks: FastAPI background tasks for async operations
    
    Returns:
        Call response with AI-generated response and session info
    """
    logger.info(f"📞 Incoming call: {request.call_sid} from {request.caller_phone}")
    
    try:
        # Load or create session
        state = None
        if request.session_id:
            logger.info(f"🔄 Continuing session: {request.session_id}")
            state = await services.session_service.load_session(request.session_id)
            
            if not state:
                logger.warning(f"⚠️ Session not found, creating new: {request.session_id}")
        
        # Process through workflow
        result = await services.workflow_runner.process_call(
            call_data={
                "call_sid": request.call_sid,
                "caller_phone": request.caller_phone,
                "speech_text": request.speech_text,
                "session_id": request.session_id,
                "existing_state": state
            }
        )
        
        # Save session state
        session_id = result.session_id or request.session_id or request.call_sid
        await services.session_service.save_session(
            session_id=session_id,
            state=result
        )
        
        # Schedule cleanup in background
        background_tasks.add_task(
            services.session_service.cleanup_expired_sessions
        )
        
        # Build response
        response = CallResponse(
            success=True,
            session_id=session_id,
            caller_type=result.caller_type.value if hasattr(result.caller_type, 'value') else str(result.caller_type),
            intent=result.intent_name,
            response=result.response_text or "I'm processing your request...",
            next_action=result.next_action,
            current_tier=result.current_tier.value if hasattr(result.current_tier, 'value') else str(result.current_tier),
            turn_count=len(result.conversation_history),
            requires_escalation=result.requires_human_escalation,
            ticket_id=result.ticket_id
        )
        
        logger.info(
            f"✅ Call processed: tier={response.current_tier}, "
            f"intent={response.intent}, escalation={response.requires_escalation}"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Call processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Call processing failed: {str(e)}"
        )