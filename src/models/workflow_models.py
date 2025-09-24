# ==================== src/models/workflow_models.py ====================
"""Workflow state models."""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from .database_models import Client, Vendor


class CallerType(str, Enum):
    """Types of callers."""
    
    CLIENT = "client"
    VENDOR = "vendor"
    LEAD = "lead"


class Intent(str, Enum):
    """Call intents."""
    
    GENERAL_INQUIRY = "general_inquiry"
    SERVICE_INQUIRY = "service_inquiry"
    SERVICE_REQUEST = "service_request"
    STATUS_CHECK = "status_check"
    COMPLAINT = "complaint"
    SALES_INQUIRY = "sales_inquiry"
    SCHEDULE_UPDATE = "schedule_update"
    OTHER = "other"


class WorkflowState(BaseModel):
    """Complete workflow state for AI Receptionist LangGraph workflow."""
    
    # Call information
    call_sid: Optional[str] = None
    caller_phone: Optional[str] = None
    speech_text: Optional[str] = None
    
    # Caller identification
    caller_type: Optional[CallerType] = None
    caller_profile: Optional[Dict[str, Any]] = None
    client: Optional[Client] = None
    vendor: Optional[Vendor] = None
    
    # Intent and context
    intent: Optional[Intent] = None
    context_data: Dict[str, Any] = {}
    conversation_history: List[Dict[str, str]] = []
    
    # Response generation
    response_text: Optional[str] = None
    next_action: Optional[str] = None
    
    # Processing flags
    processed: bool = False
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = True