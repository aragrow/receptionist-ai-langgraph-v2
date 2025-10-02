# ==================== src/models/database_models.py ====================

"""
Database models for MongoDB collections.
Updated with Session Management models for Phase 7.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId
from enum import Enum


# ============ Custom Types ============

class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


# ============ Base Document ============

class BaseDocument(BaseModel):
    """Base document with common fields."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")


# ============ Existing Models (Clients, Vendors, Properties, Jobs, Visits) ============

class Client(BaseDocument):
    """Client model."""
    
    name: str
    email: str
    phone: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Vendor(BaseDocument):
    """Vendor model."""
    
    name: str
    company: str
    email: str
    phone: str
    specialty: str
    rating: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Property(BaseDocument):
    """Property model."""
    
    client_id: PyObjectId
    address: str
    city: str
    state: str
    zip_code: str
    property_type: str
    square_footage: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Job(BaseDocument):
    """Job model."""
    
    property_id: PyObjectId
    vendor_id: PyObjectId
    title: str
    description: str
    status: str = "pending"  # pending, in-progress, completed
    scheduled_date: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    completion_date: Optional[datetime] = None


class Visit(BaseDocument):
    """Visit model."""
    
    job_id: PyObjectId
    visit_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    technician_name: str
    report: Optional[str] = None
    status: str = "scheduled"  # scheduled, completed, canceled


class KnowledgeBase(BaseDocument):
    """Knowledge base entry."""
    
    entity_id: PyObjectId  # Reference to any entity
    entity_type: str  # client, property, job, visit, vendor
    content: str
    embedding: List[float] = Field(default_factory=list)


# ============ NEW: Session Management Models ============

class SessionState(BaseDocument):
    """
    Session state document stored in MongoDB.
    
    Stores the complete WorkflowState for multi-turn conversations.
    """
    
    session_id: str = Field(..., description="Unique session identifier")
    
    # State data (serialized WorkflowState)
    state_data: Dict[str, Any] = Field(
        ...,
        description="Complete workflow state as dict"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp"
    )
    expires_at: datetime = Field(
        ...,
        description="Session expiration timestamp"
    )
    
    # Metadata for quick queries
    caller_phone: Optional[str] = Field(
        None,
        description="Caller's phone number (for filtering)"
    )
    caller_type: Optional[str] = Field(
        None,
        description="Caller type (client/prospect/partner/unknown)"
    )
    current_tier: Optional[str] = Field(
        None,
        description="Current tier (L1/L2/L3)"
    )


class RoutingLog(BaseDocument):
    """
    Routing decision log for analytics.
    
    Tracks each routing decision made during a session.
    """
    
    session_id: str = Field(..., description="Associated session ID")
    
    # Routing information
    from_tier: str = Field(..., description="Source tier (START/L1/L2/L3)")
    to_tier: str = Field(..., description="Destination tier (L1/L2/L3/HUMAN)")
    
    reason: str = Field(..., description="Routing reason/decision logic")
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for routing decision"
    )
    
    # Timestamp
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Routing decision timestamp"
    )
    
    # Additional context
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional routing metadata (intent, entities, etc.)"
    )


class EscalationTicket(BaseDocument):
    """
    Human escalation ticket.
    
    Created when a conversation requires human intervention.
    """
    
    ticket_id: str = Field(..., description="Unique ticket identifier")
    session_id: str = Field(..., description="Associated session ID")
    
    # Caller information
    caller_phone: Optional[str] = Field(None, description="Caller's phone number")
    caller_type: Optional[str] = Field(None, description="Caller type")
    
    # Escalation details
    escalation_reason: str = Field(
        ...,
        description="Reason for escalation"
    )
    priority: str = Field(
        default="medium",
        description="Ticket priority (low/medium/high/urgent)"
    )
    status: str = Field(
        default="open",
        description="Ticket status (open/assigned/in_progress/resolved/closed)"
    )
    
    # Assignment
    assigned_to: Optional[Dict[str, Any]] = Field(
        None,
        description="Assigned operator information"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Ticket creation timestamp"
    )
    assigned_at: Optional[datetime] = Field(
        None,
        description="Assignment timestamp"
    )
    resolved_at: Optional[datetime] = Field(
        None,
        description="Resolution timestamp"
    )
    
    # Context
    transcript: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conversation transcript"
    )
    state_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of workflow state at escalation"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for operator"
    )
    
    # Resolution
    resolution_notes: Optional[str] = Field(
        None,
        description="Resolution notes from operator"
    )
    resolution_action: Optional[str] = Field(
        None,
        description="Action taken to resolve"
    )


class ConversationLog(BaseDocument):
    """
    Complete conversation log for archival and analysis.
    
    Stores finalized conversations for compliance and training.
    """
    
    session_id: str = Field(..., description="Session identifier")
    
    # Caller information
    caller_phone: str = Field(..., description="Caller's phone number")
    caller_type: Optional[str] = Field(None, description="Caller type")
    
    # Conversation data
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Complete message history"
    )
    
    # Routing information
    routing_path: List[str] = Field(
        default_factory=list,
        description="Path through tiers (e.g., ['START→L1', 'L1→L2', 'L2→L3'])"
    )
    
    # Outcomes
    final_intent: Optional[str] = Field(
        None,
        description="Final classified intent"
    )
    final_tier: Optional[str] = Field(
        None,
        description="Final tier reached"
    )
    final_agent: Optional[str] = Field(
        None,
        description="Final agent that handled request"
    )
    
    escalated: bool = Field(
        default=False,
        description="Whether conversation was escalated"
    )
    ticket_id: Optional[str] = Field(
        None,
        description="Associated ticket ID if escalated"
    )
    
    # Timestamps
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Conversation start time"
    )
    ended_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Conversation end time"
    )
    
    # Metrics
    total_turns: int = Field(default=0, description="Total conversation turns")
    clarification_count: int = Field(default=0, description="Number of clarifications")
    avg_confidence: float = Field(default=0.0, description="Average confidence score")
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class AgentActionPrompt(BaseDocument):
    """
    Agent action prompt (existing model - keeping for reference).
    """
    
    agent: str = Field(..., description="Agent name")
    action: str = Field(..., description="Action name")
    level: int = Field(..., description="Prompt level/version")
    prompt: str = Field(..., description="Prompt text")
    active: bool = Field(default=True, description="Is this prompt active?")
    version: str = Field(default="1.0.0", description="Prompt version")
    notes: Optional[str] = Field(None, description="Notes about this prompt")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ============ Operator Models (for ticket management) ============

class Operator(BaseDocument):
    """
    Human operator for handling escalated tickets.
    """
    
    operator_id: str = Field(..., description="Unique operator identifier")
    name: str = Field(..., description="Operator name")
    email: str = Field(..., description="Operator email")
    
    # Status
    status: str = Field(
        default="available",
        description="Operator status (available/busy/offline)"
    )
    
    # Specialties
    specialties: List[str] = Field(
        default_factory=list,
        description="Areas of expertise (billing/technical/sales/etc.)"
    )
    
    # Workload
    active_tickets: int = Field(
        default=0,
        description="Number of currently assigned tickets"
    )
    max_tickets: int = Field(
        default=5,
        description="Maximum concurrent tickets"
    )
    
    # Metrics
    total_tickets_handled: int = Field(default=0)
    avg_resolution_time_minutes: float = Field(default=0.0)
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_active_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ============ Export All Models ============

__all__ = [
    # Existing models
    "Client",
    "Vendor",
    "Property",
    "Job",
    "Visit",
    "KnowledgeBase",
    
    # Session management models
    "SessionState",
    "RoutingLog",
    "EscalationTicket",
    "ConversationLog",
    "AgentActionPrompt",
    "Operator",
    
    # Utility
    "PyObjectId",
    "BaseDocument"
]

class PromptVersion(BaseModel):
    """Track different versions of prompts"""
    version_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    action_name: str
    prompt_text: str
    version_number: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    created_by: str  # user/system who created it
    is_active: bool = False
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    notes: str = ""

class PromptPerformance(BaseModel):
    """Track performance metrics for prompt versions"""
    metric_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version_id: str
    agent_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    
    # Classification metrics
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    
    # Confidence metrics
    avg_confidence: Optional[float] = None
    low_confidence_rate: Optional[float] = None  # % below threshold
    
    # Operational metrics
    avg_response_time_ms: Optional[float] = None
    token_usage: Optional[int] = None
    cost_per_request: Optional[float] = None
    
    # User experience metrics
    clarification_rate: Optional[float] = None
    escalation_rate: Optional[float] = None
    success_rate: Optional[float] = None
    
    sample_size: int = 0

class MisclassifiedIntent(BaseModel):
    """Track misclassified intents for improvement"""
    misclassification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    
    user_message: str
    predicted_intent: str
    predicted_confidence: float
    actual_intent: str  # determined by human review or correction
    
    agent_name: str  # L1, L2, or L3
    prompt_version_id: str
    
    routing_path: List[str]  # path through tiers
    context: Dict[str, Any] = Field(default_factory=dict)
    
    reviewed: bool = False
    reviewer_notes: str = ""
    corrective_action_taken: bool = False

class FeedbackType(str, Enum):
    """Types of feedback users can provide"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"  # 1-5 stars
    TEXT_FEEDBACK = "text_feedback"
    ESCALATION_FEEDBACK = "escalation_feedback"

class FeedbackCategory(str, Enum):
    """Categories for feedback classification"""
    ACCURACY = "accuracy"
    SPEED = "speed"
    HELPFULNESS = "helpfulness"
    UNDERSTANDING = "understanding"
    RESOLUTION = "resolution"
    OTHER = "other"

class UserFeedback(BaseModel):
    """User feedback on agent interactions"""
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    message_id: Optional[str] = None  # Specific message being rated
    timestamp: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    
    feedback_type: FeedbackType
    rating: Optional[int] = None  # 1-5 for rating type
    feedback_text: Optional[str] = None
    category: Optional[FeedbackCategory] = None
    
    # Context
    agent_name: str  # Which agent generated the response
    intent: Optional[str] = None
    routing_path: List[str] = Field(default_factory=list)
    
    # User info
    user_id: Optional[str] = None
    caller_type: Optional[str] = None
    
    # Processing
    reviewed: bool = False
    reviewer_notes: str = ""
    action_taken: Optional[str] = None
    improvement_implemented: bool = False

class EscalationFeedback(BaseModel):
    """Feedback specifically for escalated cases"""
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    
    # Escalation context
    escalation_reason: str
    resolved: bool = False
    resolution_time_minutes: Optional[int] = None
    
    # User satisfaction
    was_escalation_necessary: bool
    user_satisfaction: int  # 1-5
    feedback_text: Optional[str] = None
    
    # Analysis
    could_have_been_automated: bool = False
    suggested_improvement: Optional[str] = None
    reviewed: bool = False

class FeedbackAnalytics(BaseModel):
    """Aggregated feedback analytics"""
    analytics_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    period_start: datetime
    period_end: datetime
    generated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    
    # Overall metrics
    total_feedback_count: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    avg_rating: Optional[float] = None
    
    # By agent
    feedback_by_agent: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # By intent
    feedback_by_intent: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Common issues
    top_issues: List[Dict[str, Any]] = Field(default_factory=list)
    improvement_opportunities: List[str] = Field(default_factory=list)
