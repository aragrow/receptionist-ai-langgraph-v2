# ==================== config/routing_config.py ====================
"""
Routing configuration for 3-tier agent system.
Defines confidence thresholds, agent mappings, and routing decision logic.

Summary of Routing Configuration
1. Confidence Thresholds

HIGH = 0.75: Auto-route to next tier
MEDIUM = 0.40: Ask clarification
< 0.40: Escalate to human

2. Clarification Limits

MAX_CLARIFICATIONS = 2: Total attempts before escalation
MAX_L1_CLARIFICATIONS = 1: L1 only gets 1 attempt
MAX_L2_CLARIFICATIONS = 2: L2 gets 2 attempts

3. Routing Maps

Caller Type → L2 Agent: Maps client/prospect/partner to appropriate L2
L1 Intent → L3 Agent: Maps broad intents to L3 specialists
L2 Intent → L3 Agent: Maps refined intents to L3 specialists

4. Slot Definitions

Required Slots: Must be filled before L3 execution
Optional Slots: Nice to have but not blocking

5. Escalation Rules

Low confidence
Max clarifications reached
User requested human
Sensitive keywords detected
Technical errors

6. Routing Decision Functions
Core routing logic:

should_clarify(): Check if clarification needed
should_escalate_to_human(): Check if escalation needed
get_l2_agent_for_caller_type(): Select L2 agent
get_l3_agent_for_intent(): Select L3 agent
get_required_slots_for_intent(): Get required slots
determine_routing_decision(): Comprehensive routing logic

7. Agent Capabilities Matrix
Defines what each agent can handle - used for validation

Key Features

Centralized Configuration: All routing logic in one place
Type-Safe: Uses enums to prevent invalid states
Flexible: Easy to adjust thresholds and mappings
Extensible: Easy to add new intents, agents, or rules
Validated: Routing path validation prevents illegal transitions
Documented: Rich context for logging and debugging

"""

from typing import Dict, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass

from src.models.agent_models import (
    RoutingDecision, 
    L2AgentType, 
    L3AgentType,
    EscalationReason
)


# ============ Confidence Thresholds ============

@dataclass
class ConfidenceThresholds:
    """Confidence score thresholds for routing decisions."""
    
    # Auto-route thresholds
    HIGH: float = 0.75  # >= 0.75: Auto-route to next tier
    MEDIUM: float = 0.40  # 0.40-0.74: Ask clarification
    # < 0.40: Escalate to human
    
    # Caller type detection thresholds
    CALLER_TYPE_HIGH: float = 0.80  # High confidence in caller type
    CALLER_TYPE_MEDIUM: float = 0.50  # Medium confidence
    
    # Entity extraction thresholds
    ENTITY_EXTRACTION_MIN: float = 0.60  # Minimum confidence for entity


# Global instance
CONFIDENCE_THRESHOLDS = ConfidenceThresholds()


# ============ Clarification Limits ============

@dataclass
class ClarificationLimits:
    """Limits for clarification attempts."""
    
    MAX_CLARIFICATIONS: int = 2  # Maximum clarification attempts before escalation
    MAX_L1_CLARIFICATIONS: int = 1  # Max clarifications at L1
    MAX_L2_CLARIFICATIONS: int = 2  # Max clarifications at L2


# Global instance
CLARIFICATION_LIMITS = ClarificationLimits()


# ============ Caller Type to L2 Agent Mapping ============

CALLER_TYPE_TO_L2_AGENT: Dict[str, L2AgentType] = {
    "client": L2AgentType.CLIENT_RECEPTIONIST,
    "prospect": L2AgentType.PROSPECT_RECEPTIONIST,
    "partner": L2AgentType.PARTNER_RECEPTIONIST,
    "vendor": L2AgentType.PARTNER_RECEPTIONIST,  # Vendors use partner receptionist
    "lead": L2AgentType.PROSPECT_RECEPTIONIST,  # Leads are treated as prospects
    "unknown": L2AgentType.GENERAL_RECEPTIONIST,
}


# ============ Intent to L3 Agent Mapping ============

# L1 broad intent categories to L3 agents
L1_INTENT_TO_L3_AGENT: Dict[str, L3AgentType] = {
    "scheduling": L3AgentType.SCHEDULING_AGENT,
    "booking": L3AgentType.SALES_AGENT,
    "sales": L3AgentType.SALES_AGENT,
    "support": L3AgentType.SUPPORT_AGENT,
    "technical": L3AgentType.SUPPORT_AGENT,
    "billing": L3AgentType.BILLING_AGENT,
    "payment": L3AgentType.BILLING_AGENT,
    "invoice": L3AgentType.BILLING_AGENT,
    "partner": L3AgentType.PARTNER_AGENT,
    "vendor": L3AgentType.PARTNER_AGENT,
    "general": L3AgentType.GENERAL_AGENT,
    "inquiry": L3AgentType.GENERAL_AGENT,
}


# L2 refined intents to L3 agents (more specific mapping)
L2_INTENT_TO_L3_AGENT: Dict[str, L3AgentType] = {
    # Sales & Booking
    "book_home_cleaning": L3AgentType.SALES_AGENT,
    "book_commercial_cleaning": L3AgentType.SALES_AGENT,
    "request_quote": L3AgentType.SALES_AGENT,
    "schedule_service": L3AgentType.SCHEDULING_AGENT,
    "reschedule_service": L3AgentType.SCHEDULING_AGENT,
    "cancel_service": L3AgentType.SCHEDULING_AGENT,
    
    # Support
    "service_complaint": L3AgentType.SUPPORT_AGENT,
    "technical_issue": L3AgentType.SUPPORT_AGENT,
    "quality_issue": L3AgentType.SUPPORT_AGENT,
    "check_service_status": L3AgentType.SUPPORT_AGENT,
    "report_problem": L3AgentType.SUPPORT_AGENT,
    
    # Billing
    "check_invoice": L3AgentType.BILLING_AGENT,
    "payment_inquiry": L3AgentType.BILLING_AGENT,
    "billing_dispute": L3AgentType.BILLING_AGENT,
    "update_payment_method": L3AgentType.BILLING_AGENT,
    "request_receipt": L3AgentType.BILLING_AGENT,
    
    # Partner/Vendor
    "vendor_checkin": L3AgentType.PARTNER_AGENT,
    "update_availability": L3AgentType.PARTNER_AGENT,
    "partner_inquiry": L3AgentType.PARTNER_AGENT,
    
    # General
    "general_inquiry": L3AgentType.GENERAL_AGENT,
    "company_info": L3AgentType.GENERAL_AGENT,
    "hours_of_operation": L3AgentType.GENERAL_AGENT,
    "service_areas": L3AgentType.GENERAL_AGENT,
}


# ============ Slot Definitions by Intent ============

INTENT_REQUIRED_SLOTS: Dict[str, List[str]] = {
    # Booking intents
    "book_home_cleaning": ["address", "preferred_date", "service_type", "contact_number"],
    "book_commercial_cleaning": ["address", "preferred_date", "service_type", "contact_number", "square_footage"],
    "request_quote": ["address", "service_type", "contact_number"],
    
    # Scheduling intents
    "schedule_service": ["preferred_date", "preferred_time", "service_type"],
    "reschedule_service": ["job_id", "new_date", "new_time"],
    "cancel_service": ["job_id", "cancellation_reason"],
    
    # Support intents
    "service_complaint": ["job_id", "complaint_details"],
    "check_service_status": ["job_id"],
    "report_problem": ["problem_description", "urgency_level"],
    
    # Billing intents
    "check_invoice": ["invoice_id"],
    "payment_inquiry": ["account_number"],
    "billing_dispute": ["invoice_id", "dispute_reason"],
    
    # Partner intents
    "vendor_checkin": ["vendor_id", "job_id", "status_update"],
    "update_availability": ["vendor_id", "availability_dates"],
}


# Optional slots (nice to have but not required)
INTENT_OPTIONAL_SLOTS: Dict[str, List[str]] = {
    "book_home_cleaning": ["recurrence", "special_instructions", "preferred_time"],
    "book_commercial_cleaning": ["recurrence", "special_instructions", "preferred_time"],
    "request_quote": ["square_footage", "special_requirements"],
    "schedule_service": ["special_instructions"],
    "service_complaint": ["preferred_contact_method"],
}


# ============ Escalation Rules ============

@dataclass
class EscalationRule:
    """Rule for when to escalate to human."""
    
    condition: str
    reason: EscalationReason
    priority: str  # "low", "medium", "high", "urgent"


ESCALATION_RULES: List[EscalationRule] = [
    EscalationRule(
        condition="confidence_below_threshold",
        reason=EscalationReason.LOW_CONFIDENCE,
        priority="medium"
    ),
    EscalationRule(
        condition="max_clarifications_reached",
        reason=EscalationReason.MAX_CLARIFICATIONS_REACHED,
        priority="high"
    ),
    EscalationRule(
        condition="user_requested_human",
        reason=EscalationReason.USER_REQUESTED,
        priority="high"
    ),
    EscalationRule(
        condition="sensitive_complaint",
        reason=EscalationReason.SENSITIVE_ISSUE,
        priority="urgent"
    ),
    EscalationRule(
        condition="technical_error",
        reason=EscalationReason.TECHNICAL_ERROR,
        priority="high"
    ),
    EscalationRule(
        condition="complex_multi_intent",
        reason=EscalationReason.COMPLEX_REQUEST,
        priority="medium"
    ),
]


# Keywords that trigger sensitive issue escalation
SENSITIVE_KEYWORDS: List[str] = [
    "lawsuit", "legal", "attorney", "discrimination", "harassment",
    "injury", "emergency", "urgent", "hospital", "danger", "threat"
]


# ============ Routing Decision Functions ============

def should_clarify(confidence: float, tier: str = "L1") -> bool:
    """
    Determine if clarification is needed based on confidence score.
    
    Args:
        confidence: Confidence score (0.0 to 1.0)
        tier: Which tier is making the decision (L1, L2, L3)
    
    Returns:
        True if clarification should be requested
    """
    return CONFIDENCE_THRESHOLDS.MEDIUM <= confidence < CONFIDENCE_THRESHOLDS.HIGH


def should_escalate_to_human(
    confidence: float,
    clarification_count: int = 0,
    user_text: Optional[str] = None
) -> tuple[bool, Optional[EscalationReason]]:
    """
    Determine if human escalation is needed.
    
    Args:
        confidence: Confidence score
        clarification_count: Number of clarification attempts made
        user_text: User's message text (for sensitive keyword detection)
    
    Returns:
        Tuple of (should_escalate, reason)
    """
    # Low confidence
    if confidence < CONFIDENCE_THRESHOLDS.MEDIUM:
        return True, EscalationReason.LOW_CONFIDENCE
    
    # Max clarifications reached
    if clarification_count >= CLARIFICATION_LIMITS.MAX_CLARIFICATIONS:
        return True, EscalationReason.MAX_CLARIFICATIONS_REACHED
    
    # User explicitly requests human
    if user_text:
        user_lower = user_text.lower()
        if any(phrase in user_lower for phrase in [
            "speak to a person", "talk to human", "real person",
            "representative", "manager", "supervisor"
        ]):
            return True, EscalationReason.USER_REQUESTED
        
        # Sensitive keywords
        if any(keyword in user_lower for keyword in SENSITIVE_KEYWORDS):
            return True, EscalationReason.SENSITIVE_ISSUE
    
    return False, None


def get_l2_agent_for_caller_type(caller_type: str) -> L2AgentType:
    """
    Get appropriate L2 agent based on caller type.
    
    Args:
        caller_type: Detected caller type
    
    Returns:
        L2AgentType enum value
    """
    return CALLER_TYPE_TO_L2_AGENT.get(
        caller_type.lower(),
        L2AgentType.GENERAL_RECEPTIONIST
    )


def get_l3_agent_for_intent(
    intent_name: str,
    is_refined: bool = False
) -> L3AgentType:
    """
    Get appropriate L3 agent based on intent.
    
    Args:
        intent_name: Intent name (broad L1 or refined L2)
        is_refined: Whether this is a refined L2 intent
    
    Returns:
        L3AgentType enum value
    """
    mapping = L2_INTENT_TO_L3_AGENT if is_refined else L1_INTENT_TO_L3_AGENT
    return mapping.get(
        intent_name.lower(),
        L3AgentType.GENERAL_AGENT
    )


def get_required_slots_for_intent(intent_name: str) -> List[str]:
    """
    Get required slots for a given intent.
    
    Args:
        intent_name: Intent name
    
    Returns:
        List of required slot names
    """
    return INTENT_REQUIRED_SLOTS.get(intent_name.lower(), [])


def get_optional_slots_for_intent(intent_name: str) -> List[str]:
    """
    Get optional slots for a given intent.
    
    Args:
        intent_name: Intent name
    
    Returns:
        List of optional slot names
    """
    return INTENT_OPTIONAL_SLOTS.get(intent_name.lower(), [])


def determine_routing_decision(
    confidence: float,
    has_missing_slots: bool,
    clarification_count: int,
    user_text: Optional[str] = None
) -> RoutingDecision:
    """
    Comprehensive routing decision logic.
    
    Args:
        confidence: Confidence score
        has_missing_slots: Whether required slots are missing
        clarification_count: Number of clarifications attempted
        user_text: User's message (for escalation checks)
    
    Returns:
        RoutingDecision enum value
    """
    # Check for escalation first
    should_esc, reason = should_escalate_to_human(confidence, clarification_count, user_text)
    if should_esc:
        return RoutingDecision.ESCALATE_TO_HUMAN
    
    # If slots are missing, clarify (even if confidence is high)
    if has_missing_slots:
        if clarification_count >= CLARIFICATION_LIMITS.MAX_CLARIFICATIONS:
            return RoutingDecision.ESCALATE_TO_HUMAN
        return RoutingDecision.CLARIFY
    
    # If confidence is medium, clarify
    if should_clarify(confidence):
        if clarification_count >= CLARIFICATION_LIMITS.MAX_CLARIFICATIONS:
            return RoutingDecision.ESCALATE_TO_HUMAN
        return RoutingDecision.CLARIFY
    
    # High confidence and no missing slots = route forward
    if confidence >= CONFIDENCE_THRESHOLDS.HIGH:
        return RoutingDecision.ROUTE_TO_L3  # Assuming we're at L2
    
    # Default to clarify
    return RoutingDecision.CLARIFY


def get_escalation_priority(reason: EscalationReason) -> str:
    """
    Get priority level for an escalation reason.
    
    Args:
        reason: EscalationReason enum
    
    Returns:
        Priority string: "low", "medium", "high", or "urgent"
    """
    priority_map = {
        EscalationReason.LOW_CONFIDENCE: "medium",
        EscalationReason.MAX_CLARIFICATIONS_REACHED: "high",
        EscalationReason.USER_REQUESTED: "high",
        EscalationReason.SENSITIVE_ISSUE: "urgent",
        EscalationReason.TECHNICAL_ERROR: "high",
        EscalationReason.COMPLEX_REQUEST: "medium",
        EscalationReason.OUT_OF_SCOPE: "low",
    }
    return priority_map.get(reason, "medium")


# ============ Routing Path Validation ============

def validate_routing_path(current_tier: str, next_tier: str) -> bool:
    """
    Validate that routing path is legal.
    
    Args:
        current_tier: Current tier (L1, L2, L3, HUMAN)
        next_tier: Proposed next tier
    
    Returns:
        True if routing is valid
    """
    valid_transitions = {
        "L1": ["L2", "HUMAN"],
        "L2": ["L3", "HUMAN", "L1"],  # Can loop back to L1 for reclassification
        "L3": ["HUMAN", "COMPLETE"],
        "HUMAN": ["COMPLETE"],
    }
    
    return next_tier in valid_transitions.get(current_tier, [])


# ============ Routing Context Builder ============

def build_routing_context(
    tier: str,
    intent: str,
    confidence: float,
    caller_type: str,
    entities: Dict,
    missing_slots: List[str]
) -> Dict:
    """
    Build a standardized routing context object for logging and debugging.
    
    Args:
        tier: Current tier
        intent: Current intent
        confidence: Confidence score
        caller_type: Caller type
        entities: Extracted entities
        missing_slots: Missing slots
    
    Returns:
        Dictionary with routing context
    """
    return {
        "tier": tier,
        "intent": intent,
        "confidence": confidence,
        "confidence_level": (
            "high" if confidence >= CONFIDENCE_THRESHOLDS.HIGH
            else "medium" if confidence >= CONFIDENCE_THRESHOLDS.MEDIUM
            else "low"
        ),
        "caller_type": caller_type,
        "entities_count": len(entities),
        "missing_slots_count": len(missing_slots),
        "missing_slots": missing_slots,
        "needs_clarification": should_clarify(confidence) or len(missing_slots) > 0,
        "needs_escalation": should_escalate_to_human(confidence)[0],
    }


# ============ Agent Capability Matrix ============

AGENT_CAPABILITIES: Dict[str, List[str]] = {
    # L2 Agents
    "client_receptionist_l2": [
        "check_service_status", "schedule_service", "billing_inquiry",
        "service_complaint", "reschedule_service", "cancel_service"
    ],
    "prospect_receptionist_l2": [
        "request_quote", "book_home_cleaning", "book_commercial_cleaning",
        "service_inquiry", "company_info"
    ],
    "partner_receptionist_l2": [
        "vendor_checkin", "update_availability", "partner_inquiry",
        "schedule_update"
    ],
    "general_receptionist_l2": [
        "general_inquiry", "company_info", "hours_of_operation",
        "service_areas"
    ],
    
    # L3 Agents
    "sales_agent_l3": [
        "book_home_cleaning", "book_commercial_cleaning", "request_quote",
        "upsell_services"
    ],
    "support_agent_l3": [
        "service_complaint", "technical_issue", "quality_issue",
        "check_service_status", "report_problem"
    ],
    "billing_agent_l3": [
        "check_invoice", "payment_inquiry", "billing_dispute",
        "update_payment_method", "request_receipt"
    ],
    "scheduling_agent_l3": [
        "schedule_service", "reschedule_service", "cancel_service",
        "check_availability"
    ],
    "partner_agent_l3": [
        "vendor_checkin", "update_availability", "partner_inquiry"
    ],
    "general_agent_l3": [
        "general_inquiry", "company_info", "hours_of_operation",
        "service_areas", "faq"
    ],
}


def can_agent_handle_intent(agent_type: str, intent: str) -> bool:
    """
    Check if an agent can handle a given intent.
    
    Args:
        agent_type: Agent type string (e.g., "sales_agent_l3")
        intent: Intent name
    
    Returns:
        True if agent can handle intent
    """
    capabilities = AGENT_CAPABILITIES.get(agent_type, [])
    return intent in capabilities