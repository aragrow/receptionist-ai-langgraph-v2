# ==================== src/models/agent_models.py ====================
"""
Agent output models for structured responses from L1, L2, and L3 agents.
These models ensure consistent, parseable outputs from LLM-based agents.

Summary of Models Created
1. L1Output - Light Classifier Output

intent_name: Broad intent (scheduling, support, billing, sales, general)
intent_category: Higher-level grouping
confidence: 0.0-1.0
caller_type: client/prospect/partner/unknown
routing_decision: Where to route next
suggested_l2_agent: Which L2 to use

2. L2Output - Intent Refiner Output

intent_name: Specific refined intent
entities: Extracted values
required_slots: What's needed
filled_slots: What's been extracted
missing_slots: What's still missing (auto-calculated)
routing_decision: Route to L3 or clarify
suggested_l3_agent: Which L3 to use
clarification_question: Generated question if needed

3. L3Output - Domain Specialist Output

action_name: What action was performed
action_status: success/failed/pending/etc.
action_result: Structured results (booking_id, invoice_url, etc.)
confirmation_message: User-facing message
next_steps: What happens next
error_code/error_message: If failed
requires_human_escalation: Escalation flag

4. ClarificationRequest - Structured Clarification

question: What to ask
question_type: open_ended/yes_no/multiple_choice/date/time
options: For multiple choice
missing_slots: What this is trying to fill
attempt_number: Track attempts

5. EscalationTicket - Human Escalation

ticket_id: Unique ID
escalation_reason: Why escalated
priority: low/medium/high/urgent
conversation_transcript: Full history
routing_history: Routing path
summary: Brief summary for human
status: open/assigned/in_progress/resolved/closed

6. Enums Added

RoutingDecision: Possible routing actions
L2AgentType: Types of L2 agents
L3AgentType: Types of L3 agents
EscalationReason: Why escalating
ActionStatus: L3 action status


Helper Functions
Created convenience functions for quick object creation:

create_l1_output()
create_l2_output()
create_l3_output()
create_clarification_request()


Key Features

Fully Structured JSON: All models force structured outputs from LLMs
Validation: Pydantic validators ensure data integrity
Type Safety: Strong typing with enums prevents invalid states
Auto-calculation: missing_slots auto-calculated in L2Output
Timestamps: All models track creation time
Extensible: Easy to add new fields without breaking existing code

"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime, UTC
from enum import Enum


# ============ Enums for Agent Outputs ============

class RoutingDecision(str, Enum):
    """Possible routing decisions from agents."""
    
    ROUTE_TO_L2 = "route_to_l2"
    ROUTE_TO_L3 = "route_to_l3"
    CLARIFY = "clarify"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    COMPLETE = "complete"
    ERROR = "error"


class L2AgentType(str, Enum):
    """Types of L2 agents (intent refiners)."""
    
    CLIENT_RECEPTIONIST = "client_receptionist_l2"
    PROSPECT_RECEPTIONIST = "prospect_receptionist_l2"
    PARTNER_RECEPTIONIST = "partner_receptionist_l2"
    GENERAL_RECEPTIONIST = "general_receptionist_l2"


class L3AgentType(str, Enum):
    """Types of L3 agents (domain specialists)."""
    
    SALES_AGENT = "sales_agent_l3"
    SUPPORT_AGENT = "support_agent_l3"
    BILLING_AGENT = "billing_agent_l3"
    SCHEDULING_AGENT = "scheduling_agent_l3"
    PARTNER_AGENT = "partner_agent_l3"
    GENERAL_AGENT = "general_agent_l3"


class EscalationReason(str, Enum):
    """Reasons for human escalation."""
    
    LOW_CONFIDENCE = "low_confidence"
    COMPLEX_REQUEST = "complex_request"
    MAX_CLARIFICATIONS_REACHED = "max_clarifications_reached"
    SENSITIVE_ISSUE = "sensitive_issue"
    USER_REQUESTED = "user_requested"
    TECHNICAL_ERROR = "technical_error"
    OUT_OF_SCOPE = "out_of_scope"


class ActionStatus(str, Enum):
    """Status of L3 action execution."""
    
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    REQUIRES_APPROVAL = "requires_approval"
    PENDING = "pending"


# ============ L1 Output Model ============

class L1Output(BaseModel):
    """
    Structured output from Level 1 (Receptionist L1) agent.
    Ultra-light classifier that identifies broad intent and caller type.
    """
    
    # Core classification
    intent_name: str = Field(
        ..., 
        description="Broad intent category (e.g., 'scheduling', 'support', 'billing', 'sales', 'general')"
    )
    intent_category: str = Field(
        ..., 
        description="Higher-level category grouping (e.g., 'sales', 'service', 'account')"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score for classification (0.0 to 1.0)"
    )
    
    # Caller identification
    caller_type: str = Field(
        ..., 
        description="Detected caller type: 'client', 'prospect', 'partner', 'unknown'"
    )
    caller_type_confidence: float = Field(
        default=0.5, 
        ge=0.0, 
        le=1.0,
        description="Confidence in caller type detection"
    )
    
    # Routing decision
    routing_decision: RoutingDecision = Field(
        ..., 
        description="Next routing action"
    )
    suggested_l2_agent: Optional[L2AgentType] = Field(
        default=None,
        description="Which L2 agent should handle this"
    )
    
    # Reasoning
    reasoning: Optional[str] = Field(
        default=None,
        description="Brief explanation of classification decision"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[float] = None
    
    # Extracted entities (minimal at L1)
    preliminary_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Any obvious entities extracted (kept minimal for speed)"
    )
    
    class Config:
        use_enum_values = True


# ============ L2 Output Model ============

class L2Output(BaseModel):
    """
    Structured output from Level 2 (Receptionist L2) agent.
    Intent refiner that extracts entities and identifies required slots.
    """
    
    # Refined intent
    intent_name: str = Field(
        ..., 
        description="Specific refined intent (e.g., 'book_home_cleaning', 'check_invoice_status')"
    )
    intent_subcategory: Optional[str] = Field(
        default=None,
        description="Sub-category within domain (e.g., 'one-time', 'recurring')"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Confidence in refined intent"
    )
    
    # Entity extraction
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="All extracted entities (date, address, service_type, etc.)"
    )
    
    # Slot management
    required_slots: List[str] = Field(
        default_factory=list,
        description="Slots needed to complete the action"
    )
    filled_slots: List[str] = Field(
        default_factory=list,
        description="Slots that have been successfully filled"
    )
    missing_slots: List[str] = Field(
        default_factory=list,
        description="Slots still needed from user"
    )
    
    # Slot validation
    slot_validation_errors: Dict[str, str] = Field(
        default_factory=dict,
        description="Any validation errors for filled slots (slot_name: error_message)"
    )
    
    # Routing decision
    routing_decision: RoutingDecision = Field(
        ...,
        description="Next routing action"
    )
    suggested_l3_agent: Optional[L3AgentType] = Field(
        default=None,
        description="Which L3 agent should handle this"
    )
    
    # Clarification handling
    needs_clarification: bool = Field(
        default=False,
        description="Whether clarification is needed"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Generated clarification question for user"
    )
    clarification_options: Optional[List[str]] = Field(
        default=None,
        description="Multiple choice options if applicable"
    )
    
    # Context and reasoning
    context_summary: Optional[str] = Field(
        default=None,
        description="Summary of relevant context for L3 agent"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation of intent refinement and routing decision"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[float] = None
    
    @validator('missing_slots', always=True)
    def calculate_missing_slots(cls, v, values):
        """Auto-calculate missing slots if not provided."""
        if v:
            return v
        required = values.get('required_slots', [])
        filled = values.get('filled_slots', [])
        return [slot for slot in required if slot not in filled]
    
    class Config:
        use_enum_values = True


# ============ L3 Output Model ============

class L3Output(BaseModel):
    """
    Structured output from Level 3 (Domain Specialist) agent.
    Action executor that performs domain-specific workflows.
    """
    
    # Action execution
    action_name: str = Field(
        ...,
        description="Name of action executed (e.g., 'create_booking', 'generate_invoice')"
    )
    action_status: ActionStatus = Field(
        ...,
        description="Status of action execution"
    )
    success: bool = Field(
        ...,
        description="Whether action completed successfully"
    )
    
    # Results
    action_result: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured result data (booking_id, invoice_url, ticket_number, etc.)"
    )
    
    # User communication
    confirmation_message: str = Field(
        ...,
        description="User-facing confirmation message"
    )
    next_steps: List[str] = Field(
        default_factory=list,
        description="What user should do next or what will happen next"
    )
    
    # Follow-up actions
    requires_follow_up: bool = Field(
        default=False,
        description="Whether this action requires follow-up"
    )
    follow_up_actions: List[str] = Field(
        default_factory=list,
        description="Actions that need to be completed later"
    )
    
    # Error handling
    error_code: Optional[str] = Field(
        default=None,
        description="Error code if action failed"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Human-readable error message"
    )
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error context for debugging"
    )
    
    # Escalation
    requires_human_escalation: bool = Field(
        default=False,
        description="Whether human intervention is needed"
    )
    escalation_reason: Optional[EscalationReason] = Field(
        default=None,
        description="Why escalation is needed"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[float] = None
    agent_type: Optional[L3AgentType] = Field(
        default=None,
        description="Which L3 agent generated this output"
    )
    
    # Additional context
    context_updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context updates to persist (e.g., booking details for future reference)"
    )
    
    class Config:
        use_enum_values = True


# ============ Clarification Request Model ============

class ClarificationRequest(BaseModel):
    """
    Model for structured clarification requests from L1 or L2 agents.
    """
    
    # Question
    question: str = Field(
        ...,
        description="Clarification question to ask user"
    )
    question_type: str = Field(
        default="open_ended",
        description="Type of question: 'open_ended', 'yes_no', 'multiple_choice', 'date', 'time'"
    )
    
    # Options (for multiple choice)
    options: Optional[List[str]] = Field(
        default=None,
        description="Multiple choice options if applicable"
    )
    
    # Slot context
    missing_slots: List[str] = Field(
        default_factory=list,
        description="Which slots this clarification is trying to fill"
    )
    slot_descriptions: Dict[str, str] = Field(
        default_factory=dict,
        description="Human-readable descriptions of what each slot is for"
    )
    
    # Guidance
    expected_format: Optional[str] = Field(
        default=None,
        description="Expected format of answer (e.g., 'YYYY-MM-DD', 'HH:MM AM/PM')"
    )
    example_answer: Optional[str] = Field(
        default=None,
        description="Example of valid answer"
    )
    
    # Context
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for clarification (why asking, what it's for)"
    )
    
    # Attempt tracking
    attempt_number: int = Field(
        default=1,
        ge=1,
        description="Which clarification attempt this is (1-indexed)"
    )
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


# ============ Escalation Ticket Model ============

class EscalationTicket(BaseModel):
    """
    Model for human escalation tickets.
    """
    
    # Identification
    ticket_id: str = Field(
        ...,
        description="Unique ticket identifier"
    )
    session_id: str = Field(
        ...,
        description="Associated session ID"
    )
    
    # Escalation details
    escalation_reason: EscalationReason = Field(
        ...,
        description="Why this was escalated"
    )
    priority: str = Field(
        default="medium",
        description="Priority level: 'low', 'medium', 'high', 'urgent'"
    )
    
    # Context
    caller_type: Optional[str] = None
    caller_phone: Optional[str] = None
    original_intent: Optional[str] = None
    
    # Conversation
    conversation_transcript: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Full conversation history"
    )
    routing_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Routing decisions made"
    )
    
    # Current state
    current_tier: str = Field(
        ...,
        description="Tier where escalation occurred"
    )
    extracted_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Entities extracted so far"
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="What information is still needed"
    )
    
    # Summary
    summary: str = Field(
        ...,
        description="Brief summary of issue for human operator"
    )
    suggested_action: Optional[str] = Field(
        default=None,
        description="Suggested next steps for human operator"
    )
    
    # Status tracking
    status: str = Field(
        default="open",
        description="Ticket status: 'open', 'assigned', 'in_progress', 'resolved', 'closed'"
    )
    assigned_to: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    class Config:
        use_enum_values = True


# ============ Helper Functions ============

def create_l1_output(
    intent_name: str,
    intent_category: str,
    confidence: float,
    caller_type: str,
    routing_decision: RoutingDecision,
    suggested_l2_agent: Optional[L2AgentType] = None,
    reasoning: Optional[str] = None
) -> L1Output:
    """Helper to create L1Output with common parameters."""
    return L1Output(
        intent_name=intent_name,
        intent_category=intent_category,
        confidence=confidence,
        caller_type=caller_type,
        caller_type_confidence=0.8,  # Default
        routing_decision=routing_decision,
        suggested_l2_agent=suggested_l2_agent,
        reasoning=reasoning
    )


def create_l2_output(
    intent_name: str,
    confidence: float,
    entities: Dict[str, Any],
    required_slots: List[str],
    filled_slots: List[str],
    routing_decision: RoutingDecision,
    suggested_l3_agent: Optional[L3AgentType] = None,
    clarification_question: Optional[str] = None
) -> L2Output:
    """Helper to create L2Output with common parameters."""
    return L2Output(
        intent_name=intent_name,
        confidence=confidence,
        entities=entities,
        required_slots=required_slots,
        filled_slots=filled_slots,
        routing_decision=routing_decision,
        suggested_l3_agent=suggested_l3_agent,
        needs_clarification=clarification_question is not None,
        clarification_question=clarification_question
    )


def create_l3_output(
    action_name: str,
    action_status: ActionStatus,
    success: bool,
    confirmation_message: str,
    action_result: Optional[Dict[str, Any]] = None,
    next_steps: Optional[List[str]] = None,
    error_message: Optional[str] = None
) -> L3Output:
    """Helper to create L3Output with common parameters."""
    return L3Output(
        action_name=action_name,
        action_status=action_status,
        success=success,
        confirmation_message=confirmation_message,
        action_result=action_result or {},
        next_steps=next_steps or [],
        error_message=error_message
    )


def create_clarification_request(
    question: str,
    missing_slots: List[str],
    question_type: str = "open_ended",
    options: Optional[List[str]] = None,
    attempt_number: int = 1
) -> ClarificationRequest:
    """Helper to create ClarificationRequest."""
    return ClarificationRequest(
        question=question,
        question_type=question_type,
        options=options,
        missing_slots=missing_slots,
        attempt_number=attempt_number
    )