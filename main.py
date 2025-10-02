"""
Main entry point for the AI Receptionist system.
Modular design with separated routers for maintainability.

uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse

from src.workflow.workflow_runner import WorkflowRunner
from src.services.session_service import SessionService
from src.services.database_service import DatabaseService
from src.services.feedback_service import FeedbackService
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


# ============ Global Services (Dependency Injection) ============

class ServiceContainer:
    """Container for global services (Dependency Injection pattern)"""
    
    def __init__(self):
        self.workflow_runner: Optional[WorkflowRunner] = None
        self.session_service: Optional[SessionService] = None
        self.db_service: Optional[DatabaseService] = None
        self.feedback_service: Optional[FeedbackService] = None
    
    async def initialize(self):
        """Initialize all services"""
        logger.info("🚀 Starting AI Receptionist System...")
        
        # Initialize database service
        self.db_service = DatabaseService()
        await self.db_service.connect()
        logger.info("✅ Database connected")
        
        # Initialize session service
        self.session_service = SessionService(
            db_service=self.db_service,
            default_ttl_minutes=30,
            max_conversation_history=10
        )
        logger.info("✅ Session service initialized")
        
        # Initialize feedback service
        self.feedback_service = FeedbackService(db_service=self.db_service)
        logger.info("✅ Feedback service initialized")
        
        # Initialize workflow runner
        self.workflow_runner = WorkflowRunner()
        await self.workflow_runner.initialize()
        logger.info("✅ Workflow runner initialized")
        
        logger.info("✨ System ready to process calls")
    
    async def cleanup(self):
        """Cleanup all services"""
        logger.info("🔄 Shutting down AI Receptionist System...")
        
        if self.workflow_runner:
            await self.workflow_runner.cleanup()
        
        if self.db_service:
            await self.db_service.disconnect()
        
        logger.info("👋 Shutdown complete")


# Global service container
services = ServiceContainer()


# ============ Lifespan Context Manager ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    try:
        await services.initialize()
        yield
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    finally:
        await services.cleanup()


# ============ FastAPI Application ============

app = FastAPI(
    title="AI Receptionist System",
    description="3-Tier Agentic Routing System with Session Management, Analytics, and Feedback Collection",
    version="2.2.0",
    lifespan=lifespan
)


# ============ Include Routers ============

# Core call processing
from src.api.call_router import router as call_router
app.include_router(call_router, tags=["Call Processing"])

# Session management
from src.api.session_router import router as session_router
app.include_router(session_router, prefix="/sessions", tags=["Sessions"])

# Feedback collection
from src.api.feedback_router import router as feedback_router
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])

# Improvement tracking
from src.api.improvement_router import router as improvement_router
app.include_router(improvement_router, prefix="/improvements", tags=["Improvements"])

# Authentication
from src.api.auth_router import router as auth_router
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Admin panel
from src.api.admin_router import router as admin_router
app.include_router(admin_router, prefix="/admin", tags=["Admin"])

# Webhooks
from src.api.webhook_router import router as webhook_router
app.include_router(webhook_router, prefix="/webhooks", tags=["Webhooks"])

# Analytics (optional - if available)
try:
    from src.api.analytics_endpoints import router as analytics_router
    app.include_router(analytics_router, tags=["Analytics"])
    logger.info("✅ Analytics endpoints enabled at /analytics/*")
except ImportError:
    logger.warning("⚠️ Analytics endpoints not available")


# ============ Core System Endpoints ============

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "AI Receptionist System",
        "version": "2.2.0",
        "features": [
            "3-Tier Agentic Routing (L1/L2/L3)",
            "Multi-Turn Session Management",
            "Automatic Session Persistence",
            "Human Escalation Support",
            "Analytics Dashboard",
            "User Feedback Collection",
            "Automated Improvement Tracking",
            "JWT Authentication",
            "Admin Panel",
            "Webhook Integration"
        ],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "dashboard": "/dashboard",
            "analytics": "/analytics/dashboard",
            "auth": "/auth",
            "admin": "/admin",
            "webhooks": "/webhooks",
            "feedback": "/feedback",
            "improvements": "/improvements"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db_healthy = services.db_service and services.db_service.db is not None
        
        active_sessions = 0
        if services.session_service:
            active_sessions = await services.session_service.get_active_sessions_count()
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "environment": settings.environment,
            "database_connected": db_healthy,
            "active_sessions": active_sessions,
            "session_ttl_minutes": services.session_service.default_ttl_minutes if services.session_service else 30,
            "feedback_enabled": services.feedback_service is not None,
            "services": {
                "workflow_runner": services.workflow_runner is not None,
                "session_service": services.session_service is not None,
                "db_service": services.db_service is not None,
                "feedback_service": services.feedback_service is not None
            }
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
    """Serve the analytics dashboard HTML page"""
    try:
        return FileResponse("templates/analytics_dashboard.html")
    except FileNotFoundError:
        logger.warning("Analytics dashboard HTML not found")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Dashboard not found",
                "message": "Analytics dashboard is not yet set up. Please create templates/analytics_dashboard.html"
            }
        )


@app.get("/stats")
async def get_system_stats():
    """Get system statistics and metrics"""
    logger.info("📊 Retrieving system statistics")
    
    try:
        active_sessions = await services.session_service.get_active_sessions_count()
        recent_sessions = await services.session_service.get_recent_sessions(limit=100)
        
        total_turns = sum(s.get("turn_count", 0) for s in recent_sessions)
        avg_turns = total_turns / len(recent_sessions) if recent_sessions else 0
        
        feedback_summary = await services.feedback_service.get_feedback_summary(days=7)
        
        return {
            "active_sessions": active_sessions,
            "recent_sessions_sample": len(recent_sessions),
            "avg_turns_per_session": round(avg_turns, 2),
            "session_ttl_minutes": services.session_service.default_ttl_minutes,
            "max_conversation_history": services.session_service.max_conversation_history,
            "analytics_available": "analytics_router" in str(app.routes),
            "feedback_stats": {
                "total_feedback": feedback_summary.get("total_feedback", 0),
                "positive_rate": round(feedback_summary.get("positive_rate", 0) * 100, 1),
                "avg_rating": feedback_summary.get("avg_rating")
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats: {str(e)}"
        )


# ============ Error Handlers ============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.environment == "development" else "An error occurred"
        }
    )


# ============ Dependency Injection Helpers ============

def get_workflow_runner() -> WorkflowRunner:
    """Get workflow runner service"""
    return services.workflow_runner


def get_session_service() -> SessionService:
    """Get session service"""
    return services.session_service


def get_feedback_service() -> FeedbackService:
    """Get feedback service"""
    return services.feedback_service


def get_db_service() -> DatabaseService:
    """Get database service"""
    return services.db_service


# ============ Main Entry Point ============

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )