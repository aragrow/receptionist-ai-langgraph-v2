"""
Main entry point for the AI Receptionist system with Session Management and Analytics.
uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import logging.config
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from src.workflow.workflow_runner import WorkflowRunner
from src.services.session_service import SessionService
from src.services.database_service import DatabaseService
from config.settings import settings


# ============ Logging Configuration ============

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "default",
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": "INFO",
            "formatter": "detailed",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "./logs/ai_receptionist.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default", "file"]
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("ai_receptionist")


# ============ Global Services ============

workflow_runner: Optional[WorkflowRunner] = None
session_service: Optional[SessionService] = None
db_service: Optional[DatabaseService] = None


# ============ Lifespan Context Manager ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    
    Handles:
    - Database connection initialization
    - Service initialization
    - Graceful shutdown
    """
    global workflow_runner, session_service, db_service
    
    logger.info("🚀 Starting AI Receptionist System...")
    
    try:
        # Initialize database service
        db_service = DatabaseService()
        await db_service.connect()
        logger.info("✅ Database connected")
        
        # Initialize session service
        session_service = SessionService(
            db_service=db_service,
            default_ttl_minutes=30,
            max_conversation_history=10
        )
        logger.info("✅ Session service initialized")
        
        # Initialize workflow runner
        workflow_runner = WorkflowRunner()
        await workflow_runner.initialize()
        logger.info("✅ Workflow runner initialized")
        
        logger.info("✨ System ready to process calls")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    finally:
        # Cleanup
        logger.info("🔄 Shutting down AI Receptionist System...")
        
        if workflow_runner:
            await workflow_runner.cleanup()
        
        if db_service:
            await db_service.disconnect()
        
        logger.info("👋 Shutdown complete")


# ============ FastAPI Application ============

app = FastAPI(
    title="AI Receptionist System",
    description="3-Tier Agentic Routing System with Session Management and Analytics",
    version="2.1.0",
    lifespan=lifespan
)


# ============ Include Analytics Router (if available) ============

try:
    from src.api.analytics_endpoints import router as analytics_router
    app.include_router(analytics_router)
    logger.info("✅ Analytics endpoints enabled at /analytics/*")
except ImportError:
    logger.warning("⚠️ Analytics endpoints not available (src/api/analytics_endpoints.py not found)")


# ============ Request/Response Models ============

class CallRequest(BaseModel):
    """Request model for call processing."""
    
    caller_phone: str = Field(..., description="Caller's phone number")
    speech_text: str = Field(..., description="Transcribed speech from caller")
    call_sid: str = Field(..., description="Unique call identifier")
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for continuing conversation (auto-generated if not provided)"
    )


class CallResponse(BaseModel):
    """Response model for call processing."""
    
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


class SessionInfoResponse(BaseModel):
    """Response model for session information."""
    
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


# ============ API Endpoints ============

@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "AI Receptionist System",
        "version": "2.1.0",
        "features": [
            "3-Tier Agentic Routing (L1/L2/L3)",
            "Multi-Turn Session Management",
            "Automatic Session Persistence",
            "Human Escalation Support",
            "Analytics Dashboard"
        ],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "dashboard": "/dashboard",
            "analytics": "/analytics/dashboard"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status and system information
    """
    try:
        # Check database connection
        db_healthy = db_service and db_service.db is not None
        
        # Get active sessions count
        active_sessions = 0
        if session_service:
            active_sessions = await session_service.get_active_sessions_count()
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "environment": settings.environment,
            "database_connected": db_healthy,
            "active_sessions": active_sessions,
            "session_ttl_minutes": session_service.default_ttl_minutes if session_service else 30
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/dashboard")
async def serve_dashboard():
    """
    Serve the analytics dashboard HTML page.
    
    Returns:
        HTML dashboard for viewing metrics and analytics
    """
    try:
        return FileResponse("templates/analytics_dashboard.html")
    except FileNotFoundError:
        logger.warning("Analytics dashboard HTML not found at templates/analytics_dashboard.html")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Dashboard not found",
                "message": "Analytics dashboard is not yet set up. Please create templates/analytics_dashboard.html"
            }
        )


@app.post("/process-call", response_model=CallResponse)
async def process_call(
    request: CallRequest,
    background_tasks: BackgroundTasks
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
        if request.session_id:
            logger.info(f"🔄 Continuing session: {request.session_id}")
            state = await session_service.load_session(request.session_id)
            
            if not state:
                logger.warning(f"⚠️ Session not found, creating new: {request.session_id}")
                state = None
        else:
            state = None
        
        # Process through workflow
        result = await workflow_runner.process_call(
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
        await session_service.save_session(
            session_id=session_id,
            state=result
        )
        
        # Schedule cleanup in background
        background_tasks.add_task(
            session_service.cleanup_expired_sessions
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
            f"intent={response.intent}, "
            f"escalation={response.requires_escalation}"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Call processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Call processing failed: {str(e)}"
        )


@app.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    """
    Get information about a specific session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session information including conversation history and routing
    """
    logger.info(f"📊 Retrieving session info: {session_id}")
    
    try:
        session_info = await session_service.get_session_info(session_id)
        
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


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a specific session.
    
    Args:
        session_id: Session identifier to delete
    
    Returns:
        Confirmation of deletion
    """
    logger.info(f"🗑️ Deleting session: {session_id}")
    
    try:
        deleted = await session_service.delete_session(session_id)
        
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


@app.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    include_metadata: bool = True
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
        export = await session_service.export_conversation(
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


@app.post("/sessions/cleanup")
async def cleanup_sessions():
    """
    Manually trigger cleanup of expired sessions.
    
    Returns:
        Number of sessions cleaned up
    """
    logger.info("🧹 Manual session cleanup triggered")
    
    try:
        count = await session_service.cleanup_expired_sessions()
        
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


@app.get("/stats")
async def get_system_stats():
    """
    Get system statistics and metrics.
    
    Returns:
        System statistics including session counts and routing metrics
    """
    logger.info("📊 Retrieving system statistics")
    
    try:
        active_sessions = await session_service.get_active_sessions_count()
        
        # Get recent routing logs for metrics
        recent_sessions = await session_service.get_recent_sessions(limit=100)
        
        # Calculate metrics
        total_turns = sum(s.get("turn_count", 0) for s in recent_sessions)
        avg_turns = total_turns / len(recent_sessions) if recent_sessions else 0
        
        return {
            "active_sessions": active_sessions,
            "recent_sessions_sample": len(recent_sessions),
            "avg_turns_per_session": round(avg_turns, 2),
            "session_ttl_minutes": session_service.default_ttl_minutes,
            "max_conversation_history": session_service.max_conversation_history,
            "analytics_available": "analytics_router" in str(app.routes)
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats: {str(e)}"
        )


# ============ Error Handlers ============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.environment == "development" else "An error occurred"
        }
    )


# ============ Main Entry Point ============

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )