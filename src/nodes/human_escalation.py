# ==================== src/nodes/human_escalation.py ====================
"""
Human Escalation Node for AI Receptionist with telemetry.
Handles escalation to human operators with ticket creation.
"""

import logging
from typing import Optional
from datetime import datetime, timezone
import uuid

from src.models.workflow_models import WorkflowState, ConversationMessage
from src.services.ticket_service import TicketService

# Import telemetry services (with graceful fallback)
try:
    from src.services.metrics_service import get_metrics_service
    from src.services.logging_service import get_logging_service
    TELEMETRY_ENABLED = True
except ImportError:
    TELEMETRY_ENABLED = False

logger = logging.getLogger(__name__)


class HumanEscalationNode:
    """
    Handles escalation to human operators with comprehensive telemetry.
    
    Responsibilities:
    - Create escalation tickets with full context
    - Generate ticket IDs
    - Provide user-facing escalation messages
    - Log escalation reasons for analytics
    - Track escalation metrics
    """
    
    def __init__(self, ticket_service: TicketService):
        """
        Initialize human escalation node.
        
        Args:
            ticket_service: Service for creating and managing tickets
        """
        self.ticket_service = ticket_service
        
        # Initialize telemetry services if available
        if TELEMETRY_ENABLED:
            self.metrics = get_metrics_service()
            self.telemetry_logger = get_logging_service()
        else:
            self.metrics = None
            self.telemetry_logger = None
            logger.warning("Telemetry services not available for HumanEscalationNode")
    
    async def __call__(self, state: WorkflowState) -> WorkflowState:
        """
        Process human escalation request with full tracking.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated workflow state with ticket information
        """
        logger.info(
            f"[HumanEscalation] Escalating to human. "
            f"Reason: {state.escalation_reason or 'unspecified'}, "
            f"Clarification attempts: {state.clarification_count}"
        )
        
        # Generate ticket ID
        ticket_id = str(uuid.uuid4())
        
        # Determine escalation reason if not set
        if not state.escalation_reason:
            state.escalation_reason = self._determine_escalation_reason(state)
        
        # Determine escalation priority
        priority = self._determine_priority(state)
        
        # Create ticket with full context
        try:
            ticket = await self.ticket_service.create_ticket(
                session_id=state.session_id or "unknown",
                caller_phone=state.caller_phone,
                caller_type=state.caller_type.value if hasattr(state.caller_type, 'value') else str(state.caller_type),
                reason=state.escalation_reason,
                priority=priority,
                context={
                    "conversation_history": state.conversation_history,
                    "current_tier": state.current_tier.value if hasattr(state.current_tier, 'value') else str(state.current_tier),
                    "intent": state.intent_name,
                    "entities_collected": state.entities,
                    "missing_slots": state.missing_slots,
                    "clarification_attempts": state.clarification_count,
                    "routing_confidence": state.routing_confidence,
                    "speech_text": state.speech_text
                }
            )
            
            ticket_id = ticket.get("ticket_id", ticket_id)
            logger.info(f"[HumanEscalation] Ticket created: {ticket_id}")
            
        except Exception as e:
            logger.error(f"[HumanEscalation] Ticket creation failed: {e}")
            # Continue with escalation even if ticket creation fails
        
        # Record escalation metrics
        if self.metrics:
            self.metrics.record_escalation(
                session_id=state.session_id or "unknown",
                reason=state.escalation_reason,
                tier=state.current_tier.value if hasattr(state.current_tier, 'value') else str(state.current_tier),
                confidence=state.routing_confidence or 0.0,
                clarification_attempts=state.clarification_count,
                ticket_id=ticket_id
            )
        
        # Log escalation with full context
        if self.telemetry_logger:
            self.telemetry_logger.log_human_escalation(
                session_id=state.session_id or "unknown",
                tier=state.current_tier.value if hasattr(state.current_tier, 'value') else str(state.current_tier),
                reason=state.escalation_reason,
                confidence=state.routing_confidence or 0.0,
                clarification_attempts=state.clarification_count,
                ticket_id=ticket_id,
                context_data={
                    "intent": state.intent_name,
                    "missing_slots": state.missing_slots,
                    "priority": priority,
                    "caller_type": state.caller_type.value if hasattr(state.caller_type, 'value') else str(state.caller_type)
                }
            )
        
        # Update state
        state.requires_human_escalation = True
        state.ticket_id = ticket_id
        state.escalation_priority = priority
        
        # Generate user-facing message
        state.response_text = self._generate_user_message(
            ticket_id=ticket_id,
            reason=state.escalation_reason,
            priority=priority
        )
        
        # Add to conversation history
        if not hasattr(state, 'conversation_history'):
            state.conversation_history = []
        
        state.conversation_history.append(
            ConversationMessage(
                role="assistant",
                content=state.response_text,
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "action": "human_escalation",
                    "ticket_id": ticket_id,
                    "reason": state.escalation_reason
                }
            )
        )
        
        logger.info(f"[HumanEscalation] Escalation complete. Ticket: {ticket_id}")
        
        return state
    
    # ============ Helper Methods ============
    
    def _determine_escalation_reason(self, state: WorkflowState) -> str:
        """
        Determine the reason for escalation based on state.
        
        Args:
            state: Current workflow state
        
        Returns:
            Escalation reason string
        """
        if state.clarification_count >= state.max_clarifications:
            return "max_clarifications_reached"
        elif state.routing_confidence is not None and state.routing_confidence < 0.4:
            return "low_confidence"
        elif state.error_message:
            return "technical_error"
        elif "speak to" in (state.speech_text or "").lower():
            return "user_requested_human"
        else:
            return "complex_request"
    
    def _determine_priority(self, state: WorkflowState) -> str:
        """
        Determine escalation priority based on state.
        
        Args:
            state: Current workflow state
        
        Returns:
            Priority level (high/medium/low)
        """
        # High priority cases
        if state.error_message:
            return "high"
        if "urgent" in (state.speech_text or "").lower():
            return "high"
        if "emergency" in (state.speech_text or "").lower():
            return "high"
        
        # Medium priority (default)
        if state.clarification_count >= state.max_clarifications:
            return "medium"
        if state.routing_confidence is not None and state.routing_confidence < 0.4:
            return "medium"
        
        # Low priority
        return "low"
    
    def _generate_user_message(
        self,
        ticket_id: str,
        reason: str,
        priority: str
    ) -> str:
        """
        Generate user-facing escalation message.
        
        Args:
            ticket_id: Generated ticket ID
            reason: Escalation reason
            priority: Priority level
        
        Returns:
            User-friendly message
        """
        base_message = (
            "I want to make sure you get the best assistance possible. "
            "Let me connect you with one of our team members who can help you directly. "
        )
        
        # Add ticket information
        ticket_message = f"Your reference number is {ticket_id[:8]}. "
        
        # Add ETA based on priority
        if priority == "high":
            eta_message = "Someone will be with you within the next few minutes."
        elif priority == "medium":
            eta_message = "Someone will be with you shortly."
        else:
            eta_message = "Someone will reach out to you soon."
        
        # Add follow-up instructions
        follow_up = (
            "\n\nYou can reference this number in any future communications "
            "about this request."
        )
        
        return base_message + ticket_message + eta_message + follow_up
    
    @staticmethod
    def should_escalate(state: WorkflowState) -> bool:
        """
        Determine if escalation to human is needed.
        
        Args:
            state: Current workflow state
        
        Returns:
            True if escalation should occur
        """
        # Check explicit escalation flag
        if state.requires_human_escalation:
            return True
        
        # Check if max clarifications reached
        if state.clarification_count >= state.max_clarifications and state.missing_slots:
            return True
        
        # Check if confidence is too low (< 0.4)
        if state.routing_confidence is not None and state.routing_confidence < 0.4:
            return True
        
        # Check for explicit user request to speak with human
        if state.speech_text:
            user_text_lower = state.speech_text.lower()
            human_keywords = [
                "speak to a person",
                "talk to a human",
                "speak with someone",
                "real person",
                "customer service",
                "representative",
                "agent",
                "operator"
            ]
            if any(keyword in user_text_lower for keyword in human_keywords):
                return True
        
        return False