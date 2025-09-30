# ==================== src/models/workflow_models.py ====================
"""Workflow state models."""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class CallerType(str, Enum):
    """Types of callers."""
    
    CLIENT = "client"
    VENDOR = "vendor"
    PROSPECT = "prospect"
    PARTNER = "partner"
    LEAD = "lead"  # Keeping for backward compatibility
    UNKNOWN = "unknown"


class Intent(str, Enum):
    """Call intents."""
    
    GENERAL_INQUIRY = "general_inquiry"
    SERVICE_INQUIRY = "service_inquiry"
    SERVICE_REQUEST = "service_request"
    STATUS_CHECK = "status_check"
    COMPLAINT = "complaint"
    SALES_INQUIRY = "sales_inquiry"
    SCHEDULE_UPDATE = "schedule_update"
    PROFILE_UPDATE = "profile_update"
    BOOKING = "booking"
    BILLING = "billing"
    SUPPORT = "support"
    TECHNICAL_ISSUE = "technical_issue"
    CANCEL_REQUEST = "cancel_request"
    RESCHEDULE = "reschedule"
    QUOTE_REQUEST = "quote_request"
    OTHER = "other"


class AgentTier(str, Enum):
    """Agent tier levels for routing."""
    
    L1 = "L1"  # Light classifier
    L2 = "L2"  # Intent refiner
    L3 = "L3"  # Domain specialist
    HUMAN = "HUMAN"  # Human escalation


class IntentL1(BaseModel):
    """Level 1 intent classification (broad categorization)."""
    
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    category: Optional[str] = None  # e.g., "sales", "support", "billing"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class IntentL2(BaseModel):
    """Level 2 intent classification (refined intent)."""
    
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    subcategory: Optional[str] = None
    parent_intent_l1: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class ConversationMessage(BaseModel):
    """Individual message in conversation history."""
    
    role: str  # "user" or "agent" or "system"
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tier: Optional[str] = None  # Which tier generated this message
    agent_name: Optional[str] = None
    metadata: Dict[str, Any] = {}


class WorkflowState(BaseModel):
    """Complete workflow state for AI Receptionist LangGraph workflow with 3-tier routing."""
    
    # ============ Session & Call Information ============
    session_id: Optional[str] = None
    call_sid: Optional[str] = None
    caller_phone: Optional[str] = None
    speech_text: Optional[str] = None
    
    # ============ Caller Identification ============
    caller_type: Optional[CallerType] = None
    caller_profile: Optional[Dict[str, Any]] = None
    client: Optional[Any] = None  # Client model
    vendor: Optional[Any] = None  # Vendor model
    
    # ============ Multi-Tier Intent Tracking ============
    intent: Optional[Intent] = None  # Legacy field, kept for backward compatibility
    intent_l1: Optional[IntentL1] = None  # Level 1: Broad classification
    intent_l2: Optional[IntentL2] = None  # Level 2: Refined intent
    
    # ============ Entity Extraction & Slot Filling ============
    entities: Dict[str, Any] = Field(default_factory=dict)  # Extracted entities (date, address, service_type, etc.)
    required_slots: List[str] = Field(default_factory=list)  # Slots needed to complete action
    missing_slots: List[str] = Field(default_factory=list)  # Slots still needed
    
    # ============ Routing Information ============
    current_tier: Optional[AgentTier] = None  # Current processing tier (L1/L2/L3/HUMAN)
    routing_reason: Optional[str] = None  # Why this routing decision was made
    routing_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    routing_history: List[Dict[str, Any]] = Field(default_factory=list)  # Track routing path
    
    # ============ Agent Selection ============
    current_agent: Optional[str] = None  # Current agent handling request
    selected_l2_agent: Optional[str] = None  # Which L2 agent to use
    selected_l3_agent: Optional[str] = None  # Which L3 agent to use
    
    # ============ Clarification Handling ============
    clarification_count: int = 0  # Number of clarification attempts
    max_clarifications: int = 2  # Maximum clarifications before escalation
    awaiting_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_context: Dict[str, Any] = Field(default_factory=dict)
    
    # ============ Context & Conversation ============
    context_data: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    previous_messages: List[Dict[str, str]] = Field(default_factory=list)  # Legacy format
    
    # ============ Response Generation ============
    response_text: Optional[str] = None
    next_action: Optional[str] = None
    
    # ============ Escalation & Ticketing ============
    requires_human_escalation: bool = False
    escalation_reason: Optional[str] = None
    ticket_id: Optional[str] = None
    escalation_priority: Optional[str] = None  # "low", "medium", "high", "urgent"
    
    # ============ Processing Flags ============
    processed: bool = False
    error_message: Optional[str] = None
    turn_count: int = 0
    
    # ============ Confidence Thresholds (configurable) ============
    confidence_threshold_high: float = 0.75  # Auto-route
    confidence_threshold_medium: float = 0.40  # Ask clarification
    # Below medium = escalate to human
    
    # ============ Metadata & Tracking ============
    time_details: Optional[str] = None
    agent_prompt: Optional[str] = None
    processing_start_time: Optional[datetime] = None
    processing_end_time: Optional[datetime] = None
    total_processing_time_ms: Optional[float] = None
    
    # ============ Action Results (L3 outputs) ============
    action_result: Optional[Dict[str, Any]] = None
    action_success: Optional[bool] = None
    confirmation_message: Optional[str] = None
    next_steps: Optional[List[str]] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True  # Allow Client/Vendor models


# ============ Helper Functions ============

def create_conversation_message(
    role: str,
    text: str,
    tier: Optional[str] = None,
    agent_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ConversationMessage:
    """Helper function to create a conversation message."""
    return ConversationMessage(
        role=role,
        text=text,
        tier=tier,
        agent_name=agent_name,
        metadata=metadata or {}
    )


def should_clarify(confidence: float, threshold_high: float = 0.75, threshold_medium: float = 0.40) -> bool:
    """Determine if clarification is needed based on confidence score."""
    return threshold_medium <= confidence < threshold_high


def should_escalate(confidence: float, threshold_medium: float = 0.40) -> bool:
    """Determine if human escalation is needed based on confidence score."""
    return confidence < threshold_medium


def add_routing_step(state: WorkflowState, from_tier: str, to_tier: str, reason: str, confidence: float):
    """Add a routing step to the routing history."""
    state.routing_history.append({
        "from_tier": from_tier,
        "to_tier": to_tier,
        "reason": reason,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat()
    })


def get_caller_type_value(caller_type) -> str:
    """
    Safely get the string value of a caller type (handles both enum and string).
    
    Args:
        caller_type: CallerType enum or string
    
    Returns:
        String value of caller type
    """
    if caller_type is None:
        return "unknown"
    if hasattr(caller_type, 'value'):
        return caller_type.value
    return str(caller_type)