# ==================== src/agents/receptionist_l1.py ====================
"""
Receptionist L1 Agent - Ultra-light classifier.
Identifies broad intent and caller type with minimal processing.
"""

import logging
import time
from typing import Optional
import os

from dotenv import load_dotenv
from src.agents.base_agent import BaseAgent
from src.models.workflow_models import WorkflowState, CallerType
from src.models.agent_models import L1Output, RoutingDecision
from src.services.database_service import DatabaseService
from config.routing_config import (
    get_l2_agent_for_caller_type,
    CONFIDENCE_THRESHOLDS,
    determine_routing_decision
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ReceptionistL1(BaseAgent):
    """
    Level 1 Receptionist Agent - Ultra-light classifier.
    
    Responsibilities:
    - Identify broad intent category (scheduling, support, billing, sales, general)
    - Detect caller type (client, prospect, partner, unknown)
    - Make quick routing decision to appropriate L2 agent
    - Keep processing fast and lightweight (< 1 second target)
    """
    
    # Broad intent categories for L1
    BROAD_INTENTS = [
        "scheduling",   # Booking, appointments, calendar
        "support",      # Issues, complaints, help
        "billing",      # Payments, invoices, account
        "sales",        # New services, quotes, inquiries
        "general"       # Information, FAQs, other
    ]
    
    # Keywords for intent detection (fallback)
    INTENT_KEYWORDS = {
        "scheduling": [
            "schedule", "appointment", "book", "booking", "reschedule",
            "cancel", "change", "when", "time", "date", "calendar"
        ],
        "support": [
            "problem", "issue", "help", "complaint", "broken", "not working",
            "urgent", "emergency", "fix", "wrong", "mistake"
        ],
        "billing": [
            "invoice", "payment", "pay", "bill", "charge", "cost", "price",
            "refund", "credit card", "account", "balance"
        ],
        "sales": [
            "quote", "estimate", "new", "service", "buy", "purchase",
            "interested", "information", "how much", "pricing"
        ],
        "general": [
            "hello", "hi", "hours", "open", "location", "where", "contact",
            "question", "info", "about"
        ]
    }
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize Receptionist L1.
        
        
        Args:
            db_service: Database service for prompt retrieval
        """
        model_name = os.getenv("LLM__MODEL_NAME", "gemini-1.5-flash-1234")

        super().__init__(
            agent_name="receptionist_l1",
            agent_tier="L1",
            model_name=model_name,  # Fast model for L1
            temperature=0.2,  # Low temperature for consistent classification
            max_tokens=300    # L1 needs minimal output
        )
        
        self.db_service = db_service
        self.system_prompt: Optional[str] = None
        
        logger.info("ReceptionistL1 initialized")
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """
        Process incoming call with L1 classification.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated workflow state with L1 results
        """
        start_time = time.time()
        
        try:
            logger.info(f"L1 processing call from {state.caller_phone}")
            
            # Load system prompt if not cached
            if not self.system_prompt:
                await self._load_system_prompt()
            
            # Build prompt for classification
            prompt = self.build_prompt(state)
            
            # Call LLM for classification
            llm_response = await self.call_llm(
                prompt=prompt,
                system_instruction=self.system_prompt
            )
            
            # Parse JSON response into L1Output
            l1_output = self.parse_llm_json(
                llm_response=llm_response,
                output_model=L1Output,
                strict=False  # Use lenient parsing for L1 (speed priority)
            )
            
            # If parsing failed, use fallback classification
            if not isinstance(l1_output, L1Output):
                logger.warning("L1 JSON parsing failed, using fallback classification")
                l1_output = self._fallback_classification(state)
            
            # Adjust confidence with context
            l1_output.confidence = self.adjust_confidence_with_context(
                base_confidence=l1_output.confidence,
                has_caller_profile=state.caller_profile is not None,
                conversation_turn=state.turn_count + 1,
                has_previous_context=len(state.conversation_history) > 0
            )
            
            # Determine routing decision
            l1_output.routing_decision = self._determine_l1_routing(
                l1_output,
                state
            )
            
            # Select L2 agent if routing forward
            if l1_output.routing_decision == RoutingDecision.ROUTE_TO_L2:
                l1_output.suggested_l2_agent = get_l2_agent_for_caller_type(
                    l1_output.caller_type
                )
            
            # Update state with L1 results
            state = self._update_state_with_l1_output(state, l1_output)
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            state.intent_l1.timestamp = state.intent_l1.timestamp or state.processing_start_time
            
            # Log execution
            self.log_agent_execution(
                state=state,
                output=l1_output,
                processing_time_ms=processing_time_ms,
                success=True
            )
            
            logger.info(
                f"L1 completed: intent={l1_output.intent_name}, "
                f"caller_type={l1_output.caller_type}, "
                f"confidence={l1_output.confidence:.2f}, "
                f"routing={l1_output.routing_decision.value}, "
                f"time={processing_time_ms:.0f}ms"
            )
            
            return state
        
        except Exception as e:
            logger.error(f"L1 processing failed: {e}")
            
            # Use fallback on error
            fallback_output = self._fallback_classification(state)
            state = self._update_state_with_l1_output(state, fallback_output)
            state.error_message = f"L1 processing error: {str(e)}"
            
            processing_time_ms = (time.time() - start_time) * 1000
            self.log_agent_execution(
                state=state,
                output=fallback_output,
                processing_time_ms=processing_time_ms,
                success=False,
                error=str(e)
            )
            
            return state
    
    def build_prompt(self, state: WorkflowState) -> str:
        """
        Build L1 classification prompt.
        
        Args:
            state: Current workflow state
        
        Returns:
            Formatted prompt string
        """
        # Get caller info
        caller_phone = state.caller_phone or "unknown"
        if state.caller_type:
            if hasattr(state.caller_type, 'value'):
                caller_type = state.caller_type.value
            else:
                caller_type = str(state.caller_type)
        else:
            caller_type = "unknown"
        speech_text = self.sanitize_input(state.speech_text or "")
        
        # Build context
        context_parts = []
        
        if state.caller_profile:
            context_parts.append(f"Known {caller_type}")
        else:
            context_parts.append("Unknown caller")
        
        if state.conversation_history:
            context_parts.append(f"Turn {len(state.conversation_history) + 1}")
        
        context_str = ", ".join(context_parts)
        
        prompt = f"""Classify the following user input into a broad intent category.

User Input: "{speech_text}"
Context: {context_str}
Caller Phone: {caller_phone}

Available Intent Categories:
- scheduling: Booking, appointments, rescheduling, cancellations
- support: Problems, complaints, issues, help requests
- billing: Payments, invoices, account questions
- sales: New service inquiries, quotes, interested prospects
- general: General information, FAQs, other

Available Caller Types:
- client: Existing customer with account
- prospect: Potential new customer
- partner: Vendor or business partner
- unknown: Cannot determine from available information

Output Requirements:
1. Provide a JSON response with the following structure
2. Be concise and fast - this is a quick classifier
3. Confidence should be 0.0 to 1.0
4. Reasoning should be brief (one sentence)

JSON Format:
{{
    "intent_name": "one of the intent categories",
    "intent_category": "same as intent_name for L1",
    "confidence": 0.0-1.0,
    "caller_type": "one of the caller types",
    "caller_type_confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Respond ONLY with valid JSON, no additional text."""
        
        return prompt
    
    async def _load_system_prompt(self):
        """Load system prompt from database."""
        try:
            prompt_doc = await self.db_service.find_agent_action_prompt(
                agent="receptionist_l1",
                action="classify_intent",
                level=True
            )
            
            if prompt_doc and "prompt" in prompt_doc:
                self.system_prompt = prompt_doc["prompt"]
                logger.info("L1 system prompt loaded from database")
            else:
                # Use default system prompt
                self.system_prompt = self._get_default_system_prompt()
                logger.warning("Using default L1 system prompt (not found in database)")
        
        except Exception as e:
            logger.error(f"Failed to load L1 system prompt: {e}")
            self.system_prompt = self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for L1."""
        return """You are a fast, efficient call classifier for an AI receptionist system.
Your job is to quickly categorize incoming calls into broad intent categories.
Be decisive and fast - accuracy is important but speed is critical.
Always respond with valid JSON only, no additional text.
If uncertain, default to 'general' intent and lower confidence."""
    
    def _determine_l1_routing(
        self,
        l1_output: L1Output,
        state: WorkflowState
    ) -> RoutingDecision:
        """
        Determine routing decision for L1.
        
        Args:
            l1_output: L1 classification output
            state: Current workflow state
        
        Returns:
            RoutingDecision enum
        """
        # Check for escalation conditions
        should_esc, esc_reason = self.should_escalate(
            confidence=l1_output.confidence,
            clarification_count=state.clarification_count,
            user_text=state.speech_text
        )
        
        if should_esc:
            logger.info(f"L1 escalation triggered: {esc_reason}")
            state.escalation_reason = esc_reason
            return RoutingDecision.ESCALATE_TO_HUMAN
        
        # Check if clarification needed (L1 only asks if very uncertain)
        if self.should_clarify(l1_output.confidence) and state.clarification_count == 0:
            # L1 only clarifies once and only if confidence is very low
            if l1_output.confidence < 0.50:
                logger.info(f"L1 requesting clarification (confidence: {l1_output.confidence:.2f})")
                return RoutingDecision.CLARIFY
        
        # Default: route to L2
        logger.info(f"L1 routing to L2 (confidence: {l1_output.confidence:.2f})")
        return RoutingDecision.ROUTE_TO_L2
    
    def _fallback_classification(self, state: WorkflowState) -> L1Output:
        """
        Fallback classification using keyword matching.
        
        Args:
            state: Current workflow state
        
        Returns:
            L1Output with fallback classification
        """
        logger.info("Using L1 fallback classification (keyword matching)")
        
        speech_text = (state.speech_text or "").lower()
        
        # Count keyword matches for each intent
        intent_scores = {}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            matches, matched_kws = self.extract_keywords(speech_text, keywords)
            intent_scores[intent] = matches
        
        # Get intent with most matches
        best_intent = max(intent_scores, key=intent_scores.get)
        max_matches = intent_scores[best_intent]
        
        # Calculate confidence based on matches
        if max_matches >= 3:
            confidence = 0.70
        elif max_matches >= 2:
            confidence = 0.55
        elif max_matches >= 1:
            confidence = 0.40
        else:
            best_intent = "general"
            confidence = 0.30
        
        # Determine caller type (use existing detection if available)
        caller_type = state.caller_type.value if state.caller_type else "unknown"
        caller_type_confidence = 0.80 if state.caller_type else 0.30
        
        return L1Output(
            intent_name=best_intent,
            intent_category=best_intent,
            confidence=confidence,
            caller_type=caller_type,
            caller_type_confidence=caller_type_confidence,
            routing_decision=RoutingDecision.ROUTE_TO_L2,
            suggested_l2_agent=get_l2_agent_for_caller_type(caller_type),
            reasoning=f"Fallback classification: matched {max_matches} keywords for {best_intent}"
        )
    
    def _update_state_with_l1_output(
        self,
        state: WorkflowState,
        l1_output: L1Output
    ) -> WorkflowState:
        """
        Update workflow state with L1 output.
        
        Args:
            state: Current workflow state
            l1_output: L1 classification output
        
        Returns:
            Updated workflow state
        """
        from src.models.workflow_models import IntentL1
        from datetime import datetime, UTC
        
        # Update intent L1
        state.intent_l1 = IntentL1(
            name=l1_output.intent_name,
            confidence=l1_output.confidence,
            category=l1_output.intent_category,
            timestamp=datetime.now(UTC)
        )
        
        # Update caller type if detected (and not already set from identity check)
        # Handle both string and enum values
        if not state.caller_type or state.caller_type == CallerType.UNKNOWN:
            # Ensure caller_type is a CallerType enum
            if isinstance(l1_output.caller_type, str):
                try:
                    state.caller_type = CallerType(l1_output.caller_type)
                except ValueError:
                    # If invalid value, default to UNKNOWN
                    state.caller_type = CallerType.UNKNOWN
            else:
                state.caller_type = l1_output.caller_type
        
        # Update routing info
        state.current_tier = "L1"
        state.current_agent = self.agent_name
        state.routing_confidence = l1_output.confidence
        state.routing_reason = l1_output.reasoning or f"L1 classified as {l1_output.intent_name}"
        
        # Handle suggested_l2_agent - ensure it's a string value
        if l1_output.suggested_l2_agent:
            if hasattr(l1_output.suggested_l2_agent, 'value'):
                state.selected_l2_agent = l1_output.suggested_l2_agent.value
            else:
                state.selected_l2_agent = str(l1_output.suggested_l2_agent)
        
        # Add preliminary entities if any
        if l1_output.preliminary_entities:
            state.entities.update(l1_output.preliminary_entities)
        
        # Add to routing history
        from config.routing_config import add_routing_step
        add_routing_step(
            state=state,
            from_tier="START",
            to_tier="L1",
            reason=f"Initial classification: {l1_output.intent_name}",
            confidence=l1_output.confidence
        )
        
        return state

# ============ Factory Function ============

def create_receptionist_l1(db_service: DatabaseService) -> ReceptionistL1:
    """
    Factory function to create Receptionist L1 agent.
    
    Args:
        db_service: Database service instance
    
    Returns:
        Initialized ReceptionistL1 agent
    """
    return ReceptionistL1(db_service=db_service)