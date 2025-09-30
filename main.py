# ==================== main.py ====================
"""
Main entry point for the AI Receptionist system.
uvicorn main:app --reload

run_test.py -  To do Basic Tesing of the Agents
replicate_conversations.py - Run some conversations to see the results.
"""
import logging
import logging.config
from logging.handlers import RotatingFileHandler
import asyncio
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any


from src.workflow.workflow_runner import WorkflowRunner
from config.settings import settings

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "./logs/ai_receptionist.log",
            "maxBytes": 10485760,
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

# Initialize FastAPI

app = FastAPI(
    title="AI Receptionist System",
    description="MongoDB-based AI Receptionist with LangGraph workflow",
    version="1.0.0"
)

# Global workflow runner
workflow_runner = WorkflowRunner()


class CallRequest(BaseModel):
    """Request model for call processing."""
    caller_phone: str
    speech_text: str
    call_sid: str


class CallResponse(BaseModel):
    """Response model for call processing."""
    success: bool
    caller_type: str = None
    intent: str = None
    response: str = None
    next_action: str = None
    error: str = None


@app.get("/health")
async def health_check():
    print("""Health check endpoint.""")
    return {"status": "healthy", "environment": settings.environment}


@app.post("/process-call", response_model=CallResponse)
async def process_call(request: CallRequest):
    logger.info("Process an incoming call through the AI Receptionist workflow.")
    try:
        call_data = {
            "caller_phone": request.caller_phone,
            "speech_text": request.speech_text,
            "call_sid": request.call_sid
        }
        
        result = await workflow_runner.run_workflow(call_data)
        
        return CallResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Call processing failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Receptionist System",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)