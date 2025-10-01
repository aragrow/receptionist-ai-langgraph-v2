# ==================== src/nodes/clarification_handler.py ====================
"""
Clarification Handler Node for AI Receptionist with telemetry.
Manages clarification questions and response parsing.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.models.workflow_models import WorkflowState, AgentTier, ConversationMessage
from src.models.agent_models import ClarificationRequest
from src.services.llm_service import LLMService
from src.config.routing_config import MAX_CLARIFICATIONS

# Import telemetry services (with graceful fallback)
try:
    from src.services.metrics_service import get_metrics_service
    from src.services.logging_service import get_logging_service
    TELEMETRY_ENABLED = True
except ImportError:
    TELEMETRY_ENABLED = False

logger = logging.getLogger(__name__)


class ClarificationHandler:
    """
    Handles clarification loops for missing information with telemetry tracking.
    
    Responsibilities:
    - Generate clarification questions from missing slots
    - Parse user responses to fill slots
    - Track clarification attempts
    - Route back to appropriate tier or escalate
    - Record metrics for clarification success/failure
    """
    
    def __init__(self, llm_service: LLMService):
        """
        Initialize clarification handler.
        
        Args:
            llm_service: LLM service for generating questions and parsing responses
        """
        self.llm_service = llm_service
        
        # Initialize telemetry services if available
        if TELEMETRY_ENABLED:
            self.metrics = get_metrics_service()
            self.telemetry_logger = get_logging_service()
        else:
            self.metrics = None
            self.telemetry_logger = None
            logger.warning("Telemetry services not available for ClarificationHandler")
    
    async def __call__(self, state: WorkflowState) -> WorkflowState:
        """
        Main clarification handling logic with metrics tracking.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated workflow state with clarification question or filled slots
        """
        logger.info(
            f"[ClarificationHandler] Processing clarification "
            f"(attempt {state.clarification_count + 1}/{MAX_CLARIFICATIONS})"
        )
        
        # Increment clarification count
        state.clarification_count += 1
        
        # Get missing slots
        missing_slots = self._identify_missing_slots(state)
        
        if not missing_slots:
            logger.info("[ClarificationHandler] No missing slots, proceeding")
            return state
        
        # Check if max clarifications reached
        if state.clarification_count >= MAX_CLARIFICATIONS:
            logger.warning(
                f"[ClarificationHandler] Max clarifications reached "
                f"({state.clarification_count}/{MAX_CLARIFICATIONS})"
            )
            
            # Record max clarifications reached
            if self.telemetry_logger:
                self.telemetry_logger.log_max_clarifications_reached(
                    session_id=state.session_id or "unknown",
                    tier=state.current_tier.value if hasattr(state.current_tier, 'value') else str(state.current_tier),
                    max_attempts=MAX_CLARIFICATIONS,
                    still_missing_slots=missing_slots
                )
            
            # Record clarification metrics
            if self.metrics:
                self.metrics.record_clarification(
                    session_id=state.session_id or "unknown",
                    tier=state.current_tier.value if hasattr(state.current_tier, 'value') else str(state.current_tier),
                    attempt_number=state.clarification_count,
                    missing_slots=missing_slots,
                    resolved=False
                )
            
            state.requires_human_escalation = True
            state.escalation_reason = "max_clarifications_reached"
            return state
        
        # Generate clarification question
        clarification_question = await self._generate_clarification_question(
            state,
            missing_slots
        )
        
        # Log clarification request
        if self.telemetry_logger:
            self.telemetry_logger.log_clarification_request(
                session_id=state.session_id or "unknown",
                tier=state.current_tier.value if hasattr(state.current_tier, 'value') else str(state.current_tier),
                attempt_number=state.clarification_count,
                missing_slots=missing_slots,
                question=clarification_question
            )
        
        # Update state with clarification
        state.response_text = clarification_question
        state.missing_slots = missing_slots
        state.awaiting_clarification = True
        
        logger.info(f"[ClarificationHandler] Asked for: {', '.join(missing_slots)}")
        
        return state
    
    async def process_clarification_response(
        self,
        state: WorkflowState,
        user_response: str
    ) -> WorkflowState:
        """
        Process user's response to clarification question.
        
        Args:
            state: Current workflow state
            user_response: User's response text
        
        Returns:
            Updated workflow state with parsed slots
        """
        logger.info("[ClarificationHandler] Processing clarification response")
        
        # Parse response to extract entities
        extracted_entities = await self._parse_clarification_response(
            state,
            user_response
        )
        
        # Update entities in state
        if extracted_entities:
            state.entities.update(extracted_entities)
        
        # Check if slots are now filled
        still_missing = self._identify_missing_slots(state)
        resolved = len(still_missing) == 0
        
        # Log clarification response
        if self.telemetry_logger:
            self.telemetry_logger.log_clarification_response(
                session_id=state.session_id or "unknown",
                tier=state.current_tier.value if hasattr(state.current_tier, 'value') else str(state.current_tier),
                attempt_number=state.clarification_count,
                resolved=resolved,
                slots_filled=extracted_entities
            )
        
        # Record clarification metrics
        if self.metrics:
            self.metrics.record_clarification(
                session_id=state.session_id or "unknown",
                tier=state.current_tier.value if hasattr(state.current_tier, 'value') else str(state.current_tier),
                attempt_number=state.clarification_count,
                missing_slots=still_missing,
                resolved=resolved
            )
        
        # Update state
        state.missing_slots = still_missing
        state.awaiting_clarification = False
        
        if resolved:
            logger.info("[ClarificationHandler] All slots filled successfully")
        else:
            logger.info(f"[ClarificationHandler] Still missing: {', '.join(still_missing)}")
        
        return state
    
    # ============ Helper Methods ============
    
    def _identify_missing_slots(self, state: WorkflowState) -> List[str]:
        """
        Identify which required slots are still missing.
        
        Args:
            state: Current workflow state
        
        Returns:
            List of missing slot names
        """
        if not state.required_slots:
            return []
        
        missing = []
        for slot in state.required_slots:
            if slot not in state.entities or not state.entities[slot]:
                missing.append(slot)
        
        return missing
    
    async def _generate_clarification_question(
        self,
        state: WorkflowState,
        missing_slots: List[str]
    ) -> str:
        """
        Generate a natural clarification question for missing slots.
        
        Args:
            state: Current workflow state
            missing_slots: List of missing slot names
        
        Returns:
            Clarification question text
        """
        # Simple implementation - can be enhanced with LLM
        if len(missing_slots) == 1:
            slot = missing_slots[0]
            questions = {
                "address": "What's the property address where you need service?",
                "preferred_date": "What date would work best for you?",
                "contact_number": "What's the best phone number to reach you?",
                "email": "What email address should we use?",
                "service_type": "What type of service do you need?",
                "property_type": "Is this for a house, apartment, or commercial property?",
            }
            return questions.get(slot, f"Could you provide the {slot.replace('_', ' ')}?")
        else:
            # Multiple missing slots
            slot_list = ", ".join([s.replace('_', ' ') for s in missing_slots[:-1]])
            slot_list += f", and {missing_slots[-1].replace('_', ' ')}"
            return f"To help you better, I need a few more details: {slot_list}. Could you provide those?"
    
    async def _parse_clarification_response(
        self,
        state: WorkflowState,
        user_response: str
    ) -> Dict[str, Any]:
        """
        Parse user's response to extract missing entities.
        
        Args:
            state: Current workflow state
            user_response: User's response text
        
        Returns:
            Dictionary of extracted entities
        """
        # This should use LLM or NER to extract entities
        # Simplified implementation for now
        extracted = {}
        
        # Log the extraction attempt
        if self.telemetry_logger:
            self.telemetry_logger.log_slot_extraction(
                session_id=state.session_id or "unknown",
                tier=state.current_tier.value if hasattr(state.current_tier, 'value') else str(state.current_tier),
                extracted_entities=extracted,
                confidence_scores=None
            )
        
        return extracted
    
    def should_clarify(self, state: WorkflowState) -> bool:
        """
        Determine if clarification is needed.
        
        Args:
            state: Current workflow state
        
        Returns:
            True if clarification should be attempted
        """
        # Check if we have missing slots
        has_missing_slots = len(state.missing_slots) > 0
        
        # Check if we haven't exceeded max attempts
        can_clarify = state.clarification_count < MAX_CLARIFICATIONS
        
        return has_missing_slots and can_clarify