# ==================== src/agents/receptionist_l2_base.py ====================
"""
Receptionist L2 Base Agent - Intent refiner base class.
All specialized L2 agents (Client, Prospect, Partner, General) extend this class.
"""

import logging
import time
import re
from typing import Optional, List, Dict, Any, Tuple
from abc import abstractmethod
from datetime import datetime

from src.agents.base_agent import BaseAgent
from src.models.workflow_models import WorkflowState, IntentL2
from src.models.agent_models import L2Output, ClarificationRequest, RoutingDecision, L3AgentType
from src.services.database_service import DatabaseService
from config.routing_config import (
    get_l3_agent_for_intent,
    get_required_slots_for_intent,
    get_optional_slots_for_intent,
    determine_routing_decision,
    CONFIDENCE_THRESHOLDS
)

logger = logging.getLogger(__name__)


class ReceptionistL2Base(BaseAgent):
    """
    Base class for Level 2 Receptionist agents.
    
    Responsibilities:
    - Refine broad L1 intent into specific actionable intent
    - Extract entities and fill required slots
    - Validate extracted information
    - Generate clarification questions for missing slots
    - Route to appropriate L3 agent or request clarification
    
    Subclasses must implement:
    - get_intent_mappings(): Map L1 intents to specific L2 intents
    - get_specialized_prompts(): Provide caller-type-specific prompt additions
    """
    
    # Common slot patterns for extraction
    SLOT_PATTERNS = {
        "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "date": r'\b(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?)\b',
        "time": r'\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))\b',
        "address_number": r'\b\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd)\b',
    }
    
    def __init__(
        self,
        agent_name: str,
        caller_type: str,
        db_service: DatabaseService
    ):
        """
        Initialize L2 Base Agent.
        
        Args:
            agent_name: Name of the agent (e.g., "client_receptionist_l2")
            caller_type: Type of caller this agent handles
            db_service: Database service for prompt retrieval
        """
        super().__init__(
            agent_name=agent_name,
            agent_tier="L2",
            model_name=None,  # Will use LLM__MODEL_NAME from env
            temperature=0.4,  # Slightly higher than L1 for entity extraction
            max_tokens=800   # L2 needs more tokens for entity extraction
        )
        
        self.caller_type = caller_type
        self.db_service = db_service
        self.system_prompt: Optional[str] = None
        
        logger.info(f"ReceptionistL2Base initialized: {agent_name} for {caller_type}")
    
    # ============ Abstract Methods (must be implemented by subclasses) ============
    
    @abstractmethod
    def get_intent_mappings(self) -> Dict[str, List[str]]:
        """
        Get mapping from L1 broad intents to specific L2 intents.
        
        Returns:
            Dictionary mapping L1 intent to list of possible L2 intents
            Example: {"scheduling": ["book_home_cleaning", "reschedule_service", "cancel_service"]}
        """
        pass
    
    @abstractmethod
    def get_specialized_prompts(self) -> str:
        """
        Get caller-type-specific prompt additions.
        
        Returns:
            Additional prompt text specific to this caller type
        """
        pass
    
    # ============ Main Processing Method ============
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """
        Process state with L2 intent refinement.
        
        Args:
            state: Current workflow state with L1 classification
        
        Returns:
            Updated workflow state with L2 refinement
        """
        start_time = time.time()
        
        try:
            logger.info(
                f"L2 ({self.agent_name}) processing: "
                f"L1_intent={state.intent_l1.name if state.intent_l1 else 'none'}, "
                f"caller={state.caller_type.value if state.caller_type else 'unknown'}"
            )
            
            # Load system prompt if not cached
            if not self.system_prompt:
                await self._load_system_prompt()
            
            # Build prompt for intent refinement
            prompt = self.build_prompt(state)
            
            # Call LLM for refinement
            llm_response = await self.call_llm(
                prompt=prompt,
                system_instruction=self.system_prompt
            )
            
            # Parse JSON response into L2Output
            l2_output = self.parse_llm_json(
                llm_response=llm_response,
                output_model=L2Output,
                strict=False  # Allow fallback
            )
            
            # If parsing failed, use fallback
            if not isinstance(l2_output, L2Output):
                logger.warning("L2 JSON parsing failed, using fallback")
                l2_output = self._fallback_refinement(state)
            
            # Extract entities from user input
            extracted_entities = self._extract_entities_from_text(
                state.speech_text or "",
                l2_output.intent_name
            )
            
            # Merge extracted entities with LLM entities
            l2_output.entities.update(extracted_entities)
            
            # Identify required and filled slots
            l2_output = self._identify_slots(l2_output, state)
            
            # Validate extracted entities
            l2_output = self._validate_slots(l2_output)
            
            # Adjust confidence with context
            l2_output.confidence = self.adjust_confidence_with_context(
                base_confidence=l2_output.confidence,
                has_caller_profile=state.caller_profile is not None,
                conversation_turn=state.turn_count + 1,
                has_previous_context=len(state.conversation_history) > 0
            )
            
            # Determine routing decision
            l2_output.routing_decision = self._determine_l2_routing(
                l2_output,
                state
            )
            
            # Generate clarification if needed
            if l2_output.routing_decision == RoutingDecision.CLARIFY:
                l2_output = await self._generate_clarification(l2_output, state)
            
            # Select L3 agent if routing forward
            if l2_output.routing_decision == RoutingDecision.ROUTE_TO_L3:
                l2_output.suggested_l3_agent = get_l3_agent_for_intent(
                    l2_output.intent_name,
                    is_refined=True
                )
            
            # Update state with L2 results
            state = self._update_state_with_l2_output(state, l2_output)
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Log execution
            self.log_agent_execution(
                state=state,
                output=l2_output,
                processing_time_ms=processing_time_ms,
                success=True
            )
            
            logger.info(
                f"L2 completed: intent={l2_output.intent_name}, "
                f"confidence={l2_output.confidence:.2f}, "
                f"filled_slots={len(l2_output.filled_slots)}/{len(l2_output.required_slots)}, "
                f"routing={l2_output.routing_decision.value}, "
                f"time={processing_time_ms:.0f}ms"
            )
            
            return state
        
        except Exception as e:
            logger.error(f"L2 processing failed: {e}")
            
            # Use fallback on error
            fallback_output = self._fallback_refinement(state)
            state = self._update_state_with_l2_output(state, fallback_output)
            state.error_message = f"L2 processing error: {str(e)}"
            
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
        Build L2 refinement prompt.
        
        Args:
            state: Current workflow state
        
        Returns:
            Formatted prompt string
        """
        # Get L1 intent
        l1_intent = state.intent_l1.name if state.intent_l1 else "unknown"
        l1_confidence = state.intent_l1.confidence if state.intent_l1 else 0.0
        
        # Get possible L2 intents for this L1 intent
        intent_mappings = self.get_intent_mappings()
        possible_intents = intent_mappings.get(l1_intent, [l1_intent])
        
        # Get user input
        user_input = self.sanitize_input(state.speech_text or "")
        
        # Build context
        context_parts = [f"Caller type: {self.caller_type}"]
        
        if state.caller_profile:
            context_parts.append("Known customer with profile")
        
        if state.conversation_history:
            context_parts.append(f"Turn {len(state.conversation_history) + 1}")
            # Add last user message for context
            if len(state.conversation_history) > 0:
                last_msg = state.conversation_history[-1]
                if last_msg.role == "user":
                    context_parts.append(f"Previous: '{last_msg.text[:50]}...'")
        
        context_str = " | ".join(context_parts)
        
        # Get specialized prompts
        specialized = self.get_specialized_prompts()
        
        prompt = f"""Refine the user's intent and extract all relevant information.

L1 Classification: {l1_intent} (confidence: {l1_confidence:.2f})
Possible Refined Intents: {', '.join(possible_intents)}

User Input: "{user_input}"
Context: {context_str}

{specialized}

Your Task:
1. Determine the SPECIFIC refined intent from the possible intents
2. Extract ALL relevant entities (dates, times, addresses, names, etc.)
3. Identify which required slots are filled vs. missing
4. Assign a confidence score (0.0-1.0)

Entity Extraction Guidelines:
- Dates: Look for "today", "tomorrow", day names, or date formats (MM/DD, MM/DD/YY)
- Times: Look for time formats (3pm, 3:00 PM, 15:00)
- Addresses: Look for street numbers and street names
- Phone: Look for 10-digit phone numbers
- Service types: "cleaning", "deep clean", "maintenance", etc.
- Special requests: Any specific instructions or preferences

Slot Identification:
- Determine which slots are REQUIRED for this intent
- Mark slots as filled if you found the information
- Mark slots as missing if not found in user input

Output Format (JSON only):
{{
    "intent_name": "specific_refined_intent",
    "intent_subcategory": "optional subcategory",
    "confidence": 0.0-1.0,
    "entities": {{
        "date": "extracted date or null",
        "time": "extracted time or null",
        "address": "extracted address or null",
        "service_type": "extracted service or null",
        // ... other entities
    }},
    "required_slots": ["slot1", "slot2", ...],
    "filled_slots": ["slot1", ...],
    "reasoning": "brief explanation of classification"
}}

Respond ONLY with valid JSON, no additional text."""
        
        return prompt
    
    # ============ Entity Extraction Methods ============
    
    def _extract_entities_from_text(
        self,
        text: str,
        intent: str
    ) -> Dict[str, Any]:
        """
        Extract entities from text using pattern matching.
        
        Args:
            text: User input text
            intent: Refined intent name
        
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        text_lower = text.lower()
        
        # Extract phone numbers
        phone_match = re.search(self.SLOT_PATTERNS["phone"], text)
        if phone_match:
            entities["contact_number"] = phone_match.group()
        
        # Extract email addresses
        email_match = re.search(self.SLOT_PATTERNS["email"], text, re.IGNORECASE)
        if email_match:
            entities["email"] = email_match.group()
        
        # Extract dates
        date_match = re.search(self.SLOT_PATTERNS["date"], text_lower)
        if date_match:
            entities["preferred_date"] = self._normalize_date(date_match.group())
        
        # Extract times
        time_match = re.search(self.SLOT_PATTERNS["time"], text_lower)
        if time_match:
            entities["preferred_time"] = self._normalize_time(time_match.group())
        
        # Extract addresses
        address_match = re.search(self.SLOT_PATTERNS["address_number"], text, re.IGNORECASE)
        if address_match:
            entities["address"] = address_match.group()
        
        # Extract service types (intent-specific)
        service_keywords = ["cleaning", "deep clean", "maintenance", "repair", "inspection"]
        for keyword in service_keywords:
            if keyword in text_lower:
                entities["service_type"] = keyword
                break
        
        logger.debug(f"Extracted {len(entities)} entities from text: {list(entities.keys())}")
        return entities
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to consistent format."""
        date_lower = date_str.lower().strip()
        
        # Today/Tomorrow
        if date_lower == "today":
            return datetime.now().strftime("%Y-%m-%d")
        elif date_lower == "tomorrow":
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Day names
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if date_lower in days:
            # Return the day name for now, L3 will convert to actual date
            return date_lower
        
        # Return as-is if date format
        return date_str
    
    def _normalize_time(self, time_str: str) -> str:
        """Normalize time string to consistent format."""
        time_lower = time_str.lower().strip()
        
        # Convert to 12-hour format with AM/PM if not present
        if "am" not in time_lower and "pm" not in time_lower:
            # Default to PM for common hours
            if ":" in time_lower:
                hour = int(time_lower.split(":")[0])
                if 9 <= hour <= 12:
                    time_lower += " am"
                else:
                    time_lower += " pm"
        
        return time_lower
    
    # ============ Slot Management Methods ============
    
    def _identify_slots(
        self,
        l2_output: L2Output,
        state: WorkflowState
    ) -> L2Output:
        """
        Identify required and filled slots for the intent.
        
        Args:
            l2_output: L2 output with entities
            state: Workflow state
        
        Returns:
            Updated L2Output with slot information
        """
        # Get required slots for this intent
        required_slots = get_required_slots_for_intent(l2_output.intent_name)
        l2_output.required_slots = required_slots
        
        # Identify filled slots
        filled_slots = []
        for slot in required_slots:
            # Check if entity exists and is not empty
            if slot in l2_output.entities and l2_output.entities[slot]:
                filled_slots.append(slot)
            # Also check state context for pre-filled data
            elif slot in state.entities and state.entities[slot]:
                l2_output.entities[slot] = state.entities[slot]
                filled_slots.append(slot)
            # Check caller profile for some slots
            elif state.caller_profile:
                profile_value = self._get_from_profile(slot, state.caller_profile)
                if profile_value:
                    l2_output.entities[slot] = profile_value
                    filled_slots.append(slot)
        
        l2_output.filled_slots = filled_slots
        
        # Missing slots are auto-calculated by L2Output validator
        logger.debug(
            f"Slots: {len(filled_slots)}/{len(required_slots)} filled "
            f"(missing: {l2_output.missing_slots})"
        )
        
        return l2_output
    
    def _get_from_profile(
        self,
        slot: str,
        profile: Dict[str, Any]
    ) -> Optional[Any]:
        """Get slot value from caller profile."""
        # Map slot names to profile fields
        profile_mappings = {
            "contact_number": "phone",
            "email": "email",
            "address": "address",
            "name": "name"
        }
        
        profile_field = profile_mappings.get(slot)
        if profile_field and profile_field in profile:
            return profile[profile_field]
        
        return None
    
    def _validate_slots(self, l2_output: L2Output) -> L2Output:
        """
        Validate extracted slot values.
        
        Args:
            l2_output: L2 output with filled slots
        
        Returns:
            Updated L2Output with validation errors
        """
        validation_errors = {}
        
        for slot, value in l2_output.entities.items():
            if not value:
                continue
            
            # Validate phone numbers
            if "phone" in slot or "contact" in slot:
                if not re.match(r'^\d{3}[-.]?\d{3}[-.]?\d{4}$', str(value)):
                    validation_errors[slot] = "Invalid phone number format"
            
            # Validate email
            if "email" in slot:
                if not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', str(value)):
                    validation_errors[slot] = "Invalid email format"
            
            # Add more validation rules as needed
        
        l2_output.slot_validation_errors = validation_errors
        
        if validation_errors:
            logger.warning(f"Slot validation errors: {validation_errors}")
        
        return l2_output
    
    # ============ Routing and Clarification Methods ============
    
    def _determine_l2_routing(
        self,
        l2_output: L2Output,
        state: WorkflowState
    ) -> RoutingDecision:
        """
        Determine routing decision for L2.
        
        Args:
            l2_output: L2 refinement output
            state: Current workflow state
        
        Returns:
            RoutingDecision enum
        """
        has_missing_slots = len(l2_output.missing_slots) > 0
        
        routing_decision = determine_routing_decision(
            confidence=l2_output.confidence,
            has_missing_slots=has_missing_slots,
            clarification_count=state.clarification_count,
            user_text=state.speech_text
        )
        
        logger.info(
            f"L2 routing decision: {routing_decision.value} "
            f"(confidence={l2_output.confidence:.2f}, "
            f"missing_slots={len(l2_output.missing_slots)})"
        )
        
        return routing_decision
    
    async def _generate_clarification(
        self,
        l2_output: L2Output,
        state: WorkflowState
    ) -> L2Output:
        """
        Generate clarification question for missing information.
        
        Args:
            l2_output: L2 output needing clarification
            state: Workflow state
        
        Returns:
            Updated L2Output with clarification question
        """
        try:
            # Load clarification prompt
            clarification_prompt_template = await self.db_service.find_agent_action_prompt(
                agent="receptionist",
                action="l2_clarification",
                level=1
            )
            
            if not clarification_prompt_template:
                # Fallback question
                l2_output.clarification_question = self._fallback_clarification(l2_output)
                l2_output.needs_clarification = True
                return l2_output
            
            # Format prompt with context
            prompt = clarification_prompt_template.format(
                user_input=state.speech_text,
                intent_name=l2_output.intent_name,
                confidence=l2_output.confidence,
                missing_slots=", ".join(l2_output.missing_slots),
                filled_entities=l2_output.entities
            )
            
            # Call LLM to generate question
            response = await self.call_llm(prompt=prompt)
            
            # Parse response
            import json
            try:
                clarification_data = json.loads(self._extract_json_from_response(response))
                l2_output.clarification_question = clarification_data.get("question", "")
                l2_output.needs_clarification = True
                
                # Store options if multiple choice
                if "options" in clarification_data:
                    l2_output.clarification_options = clarification_data["options"]
                
            except:
                # Fallback
                l2_output.clarification_question = self._fallback_clarification(l2_output)
                l2_output.needs_clarification = True
            
        except Exception as e:
            logger.error(f"Clarification generation failed: {e}")
            l2_output.clarification_question = self._fallback_clarification(l2_output)
            l2_output.needs_clarification = True
        
        return l2_output
    
    def _fallback_clarification(self, l2_output: L2Output) -> str:
        """Generate fallback clarification question."""
        if len(l2_output.missing_slots) == 1:
            slot = l2_output.missing_slots[0]
            slot_readable = slot.replace("_", " ")
            return f"Could you please provide your {slot_readable}?"
        else:
            slots_readable = ", ".join([s.replace("_", " ") for s in l2_output.missing_slots])
            return f"I need a bit more information. Could you provide: {slots_readable}?"
    
    # ============ State Update and Fallback Methods ============
    
    def _update_state_with_l2_output(
        self,
        state: WorkflowState,
        l2_output: L2Output
    ) -> WorkflowState:
        """Update workflow state with L2 output."""
        # Update intent L2
        state.intent_l2 = IntentL2(
            name=l2_output.intent_name,
            confidence=l2_output.confidence,
            subcategory=l2_output.intent_subcategory,
            parent_intent_l1=state.intent_l1.name if state.intent_l1 else None,
            timestamp=datetime.utcnow()
        )
        
        # Update entities and slots
        state.entities.update(l2_output.entities)
        state.required_slots = l2_output.required_slots
        state.missing_slots = l2_output.missing_slots
        
        # Update routing info
        state.current_tier = "L2"
        state.current_agent = self.agent_name
        state.routing_confidence = l2_output.confidence
        state.routing_reason = l2_output.reasoning or f"L2 refined as {l2_output.intent_name}"
        state.selected_l3_agent = l2_output.suggested_l3_agent.value if l2_output.suggested_l3_agent else None
        
        # Update clarification info
        if l2_output.needs_clarification:
            state.awaiting_clarification = True
            state.clarification_question = l2_output.clarification_question
            state.clarification_context = {
                "missing_slots": l2_output.missing_slots,
                "filled_slots": l2_output.filled_slots,
                "intent": l2_output.intent_name
            }
        
        # Add to routing history
        from config.routing_config import add_routing_step
        add_routing_step(
            state=state,
            from_tier="L1",
            to_tier="L2",
            reason=f"Refined intent: {l2_output.intent_name}",
            confidence=l2_output.confidence
        )
        
        return state
    
    def _fallback_refinement(self, state: WorkflowState) -> L2Output:
        """Fallback refinement when LLM fails."""
        logger.info("Using L2 fallback refinement")
        
        l1_intent = state.intent_l1.name if state.intent_l1 else "general"
        
        # Use L1 intent as L2 intent (no refinement)
        return L2Output(
            intent_name=l1_intent,
            confidence=0.50,
            entities={},
            required_slots=[],
            filled_slots=[],
            routing_decision=RoutingDecision.ROUTE_TO_L3,
            reasoning="Fallback: using L1 intent as L2 intent"
        )
    
    async def _load_system_prompt(self):
        """Load system prompt from database."""
        try:
            prompt_doc = await self.db_service.find_agent_action_prompt(
                agent="receptionist",
                action=f"l2_refinement_{self.caller_type}",
                level=1
            )
            
            if prompt_doc:
                self.system_prompt = prompt_doc
                logger.info(f"L2 system prompt loaded for {self.caller_type}")
            else:
                self.system_prompt = self._get_default_system_prompt()
                logger.warning(f"Using default L2 system prompt for {self.caller_type}")
        
        except Exception as e:
            logger.error(f"Failed to load L2 system prompt: {e}")
            self.system_prompt = self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for L2."""
        return f"""You are an intent refinement specialist for {self.caller_type} callers.
Your job is to take a broad intent and refine it into a specific, actionable intent.
Extract all relevant information from the user's input.
Always respond with valid JSON only, no additional text.
Be thorough in entity extraction but fast in processing."""