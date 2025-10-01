# ==================== src/models/database_models.py ====================

"""
Database models for MongoDB collections.
Updated with Session Management models for Phase 7.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


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