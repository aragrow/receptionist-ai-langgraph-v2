# ==================== src/workflow/routing_conditions.py ====================
"""
Conditional routing functions for LangGraph workflow.
These functions determine which path to take at each decision point.
"""
import logging
from typing import Literal

from src.models.workflow_models import WorkflowState
from config.routing_config import CONFIDENCE_THRESHOLDS, MAX_CLARIFICATIONS

logger = logging.getLogger(__name__)


# ============ L1 Routing Conditions ============

def check_l1_confidence(state: WorkflowState) -> Literal["l2", "escalate"]:
    """
    Check L1 confidence and route accordingly.
    
    Decision Logic:
    - confidence >= 0.40: route to L2
    - confidence < 0.40: escalate to human
    - error or escalation flag: escalate
    
    Args:
        state: Current workflow state
    
    Returns:
        "l2" or "escalate"
    """
    # Check for errors
    if state.error_message:
        logger.info(f"L1 routing: error detected, escalating")
        return "escalate"
    
    # Check explicit escalation flag
    if state.requires_human_escalation:
        logger.info(f"L1 routing: explicit escalation requested")
        return "escalate"
    
    # Check if L1 intent exists
    if not state.intent_l1:
        logger.warning("L1 routing: no intent found, escalating")
        return "escalate"
    
    # Check confidence threshold
    confidence = state.intent_l1.confidence
    threshold = CONFIDENCE_THRESHOLDS["LOW"]
    
    if confidence < threshold:
        logger.info(f"L1 routing: low confidence ({confidence:.2f} < {threshold}), escalating")
        return "escalate"
    
    logger.info(f"L1 routing: sufficient confidence ({confidence:.2f}), proceeding to L2")
    return "l2"


# ============ L2 Routing Conditions ============

def check_l2_confidence(state: WorkflowState) -> Literal["clarify", "l3", "escalate"]:
    """
    Check L2 confidence and slot completeness.
    
    Decision Logic:
    - High confidence (≥0.75) + all slots filled: route to L3
    - Medium confidence (0.40-0.74) OR missing slots: clarify
    - Low confidence (<0.40): escalate
    - Max clarifications reached: escalate
    
    Args:
        state: Current workflow state
    
    Returns:
        "clarify", "l3", or "escalate"
    """
    # Check for errors
    if state.error_message:
        logger.info("L2 routing: error detected, escalating")
        return "escalate"
    
    # Check explicit escalation flag
    if state.requires_human_escalation:
        logger.info("L2 routing: explicit escalation requested")
        return "escalate"
    
    # Check max clarifications
    if state.clarification_count >= MAX_CLARIFICATIONS:
        logger.info(f"L2 routing: max clarifications reached ({state.clarification_count}), escalating")
        return "escalate"
    
    # Check if L2 intent exists
    if not state.intent_l2:
        logger.warning("L2 routing: no refined intent found, clarifying")
        return "clarify"
    
    confidence = state.intent_l2.confidence
    
    # Low confidence → escalate
    if confidence < CONFIDENCE_THRESHOLDS["LOW"]:
        logger.info(f"L2 routing: low confidence ({confidence:.2f}), escalating")
        return "escalate"
    
    # Check slot completeness
    slots_complete = check_slots_complete(state)
    
    # High confidence + complete slots → L3
    if confidence >= CONFIDENCE_THRESHOLDS["HIGH"] and slots_complete:
        logger.info(f"L2 routing: high confidence ({confidence:.2f}) and slots complete, proceeding to L3")
        return "l3"
    
    # Medium confidence or missing slots → clarify
    logger.info(
        f"L2 routing: medium confidence ({confidence:.2f}) or incomplete slots, "
        f"requesting clarification (attempt {state.clarification_count + 1})"
    )
    return "clarify"


def check_slots_complete(state: WorkflowState) -> bool:
    """
    Check if all required slots are filled.
    
    Args:
        state: Current workflow state
    
    Returns:
        True if all required slots have values
    """
    if not state.required_slots:
        # No slots required
        return True
    
    missing_slots = []
    for slot in state.required_slots:
        if slot not in state.entities or not state.entities.get(slot):
            missing_slots.append(slot)
    
    if missing_slots:
        logger.debug(f"Missing slots: {missing_slots}")
        return False
    
    logger.debug("All required slots filled")
    return True


# ============ Clarification Routing Conditions ============

def check_max_clarifications(state: WorkflowState) -> Literal["l2", "escalate"]:
    """
    Check if max clarification attempts reached.
    
    Decision Logic:
    - clarification_count < MAX: return to L2
    - clarification_count >= MAX: escalate to human
    
    Args:
        state: Current workflow state
    
    Returns:
        "l2" or "escalate"
    """
    if state.clarification_count >= MAX_CLARIFICATIONS:
        logger.info(f"Clarification routing: max attempts reached ({state.clarification_count}), escalating")
        return "escalate"
    
    logger.info(f"Clarification routing: attempt {state.clarification_count}/{MAX_CLARIFICATIONS}, returning to L2")
    return "l2"


# ============ General Escalation Conditions ============

def check_escalation_needed(state: WorkflowState) -> bool:
    """
    Comprehensive check if human escalation is needed.
    
    Escalation triggers:
    1. Explicit escalation flag set
    2. Error message present
    3. Max clarifications reached
    4. Low confidence at any tier
    5. Critical missing slots after max attempts
    
    Args:
        state: Current workflow state
    
    Returns:
        True if escalation needed
    """
    # Explicit flag
    if state.requires_human_escalation:
        logger.info(f"Escalation check: explicit flag set - {state.escalation_reason}")
        return True
    
    # Error occurred
    if state.error_message:
        logger.info(f"Escalation check: error present - {state.error_message}")
        return True
    
    # Max clarifications
    if state.clarification_count >= MAX_CLARIFICATIONS:
        logger.info(f"Escalation check: max clarifications reached ({state.clarification_count})")
        return True
    
    # Low L1 confidence
    if state.intent_l1 and state.intent_l1.confidence < CONFIDENCE_THRESHOLDS["LOW"]:
        logger.info(f"Escalation check: L1 confidence too low ({state.intent_l1.confidence:.2f})")
        return True
    
    # Low L2 confidence
    if state.intent_l2 and state.intent_l2.confidence < CONFIDENCE_THRESHOLDS["LOW"]:
        logger.info(f"Escalation check: L2 confidence too low ({state.intent_l2.confidence:.2f})")
        return True
    
    logger.debug("Escalation check: no escalation needed")
    return False


# ============ Routing Decision Wrapper ============

def route_after_l2_processing(state: WorkflowState) -> Literal["clarify", "l3", "escalate"]:
    """
    Comprehensive routing decision after L2 processing.
    Combines confidence checks and slot checks.
    
    This is the main routing function used in the workflow graph.
    
    Args:
        state: Current workflow state
    
    Returns:
        Next destination: "clarify", "l3", or "escalate"
    """
    return check_l2_confidence(state)


def route_after_clarification_response(state: WorkflowState) -> Literal["l2", "escalate"]:
    """
    Routing decision after user provides clarification.
    
    Args:
        state: Current workflow state
    
    Returns:
        "l2" to reprocess or "escalate" if max attempts reached
    """
    return check_max_clarifications(state)


# ============ Utility Helpers ============

def get_confidence_level(confidence: float) -> str:
    """
    Get human-readable confidence level.
    
    Args:
        confidence: Confidence score (0.0-1.0)
    
    Returns:
        "high", "medium", or "low"
    """
    if confidence >= CONFIDENCE_THRESHOLDS["HIGH"]:
        return "high"
    elif confidence >= CONFIDENCE_THRESHOLDS["MEDIUM"]:
        return "medium"
    else:
        return "low"


def should_ask_clarification(state: WorkflowState) -> bool:
    """
    Determine if clarification question should be asked.
    
    Args:
        state: Current workflow state
    
    Returns:
        True if clarification is appropriate
    """
    # Don't ask if at max attempts
    if state.clarification_count >= MAX_CLARIFICATIONS:
        return False
    
    # Don't ask if already awaiting clarification
    if state.awaiting_clarification:
        return False
    
    # Ask if slots missing
    if not check_slots_complete(state):
        return True
    
    # Ask if confidence is medium
    if state.intent_l2:
        confidence_level = get_confidence_level(state.intent_l2.confidence)
        if confidence_level == "medium":
            return True
    
    return False


def format_routing_decision(state: WorkflowState) -> dict:
    """
    Format routing decision for logging and debugging.
    
    Args:
        state: Current workflow state
    
    Returns:
        Dictionary with routing information
    """
    return {
        "current_tier": state.current_tier,
        "l1_intent": state.intent_l1.name if state.intent_l1 else None,
        "l1_confidence": state.intent_l1.confidence if state.intent_l1 else None,
        "l2_intent": state.intent_l2.name if state.intent_l2 else None,
        "l2_confidence": state.intent_l2.confidence if state.intent_l2 else None,
        "slots_complete": check_slots_complete(state),
        "clarification_count": state.clarification_count,
        "requires_escalation": check_escalation_needed(state),
        "should_clarify": should_ask_clarification(state)
    }