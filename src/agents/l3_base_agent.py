# ==================== src/agents/l3_base_agent.py ====================
"""
L3 Base Agent - Domain specialist base class.
All L3 agents (Sales, Support, Billing, etc.) extend this class.
"""

import logging
import time
import os
from typing import Optional, Dict, Any, List
from abc import abstractmethod
from datetime import datetime
from dotenv import load_dotenv

from src.agents.base_agent import BaseAgent
from src.models.workflow_models import WorkflowState
from src.models.agent_models import L3Output, ActionStatus
from src.services.database_service import DatabaseService

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class L3BaseAgent(BaseAgent):
    """
    Base class for Level 3 Domain Specialist agents.
    
    Responsibilities:
    - Validate all required information is present
    - Execute domain-specific actions (booking, support ticket, invoice, etc.)
    - Generate user-facing confirmation messages
    - Provide next steps for user
    - Handle errors gracefully
    
    Subclasses must implement:
    - get_supported_actions(): List of actions this agent can perform
    - execute_action(): Perform the domain-specific action
    - validate_prerequisites(): Check if action can be performed
    """
    
    def __init__(
        self,
        agent_name: str,
        domain: str,
        db_service: DatabaseService
    ):
        """
        Initialize L3 Base Agent.
        
        Args:
            agent_name: Name of the agent (e.g., "sales_agent_l3")
            domain: Domain this agent handles (e.g., "sales", "support")
            db_service: Database service for data access
        """
        super().__init__(
            agent_name=agent_name,
            agent_tier="L3",
            model_name="gemini-1.5-pro",  # More capable model for L3
            temperature=0.5,  # Balanced creativity for messaging
            max_tokens=1000   # L3 may need detailed responses
        )
        
        self.domain = domain
        self.db_service = db_service
        self.system_prompt: Optional[str] = None
        
        logger.info(f"L3BaseAgent initialized: {agent_name} for {domain}")
    
    # ============ Abstract Methods (must be implemented by subclasses) ============
    
    @abstractmethod
    def get_supported_actions(self) -> List[str]:
        """
        Get list of actions this agent can perform.
        
        Returns:
            List of action names (e.g., ["create_booking", "send_quote"])
        """
        pass
    
    @abstractmethod
    async def execute_action(
        self,
        action_name: str,
        state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Execute the domain-specific action.
        
        Args:
            action_name: Name of action to execute
            state: Current workflow state with all required information
        
        Returns:
            Dictionary with action results:
            {
                "success": bool,
                "result_data": {...},  # Action-specific data
                "error_code": str (if failed),
                "error_message": str (if failed)
            }
        """
        pass
    
    @abstractmethod
    async def validate_prerequisites(
        self,
        action_name: str,
        state: WorkflowState
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that all prerequisites are met for the action.
        
        Args:
            action_name: Name of action to validate
            state: Current workflow state
        
        Returns:
            Tuple of (is_valid, error_message)
            If valid: (True, None)
            If invalid: (False, "reason why invalid")
        """
        pass
    
    # ============ Main Processing Method ============
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """
        Process state with L3 action execution.
        
        Args:
            state: Current workflow state with L2 refinement
        
        Returns:
            Updated workflow state with L3 results
        """
        start_time = time.time()
        
        try:
            logger.info(
                f"L3 ({self.agent_name}) processing: "
                f"intent={state.intent_l2.name if state.intent_l2 else 'none'}, "
                f"domain={self.domain}"
            )
            
            # Determine which action to execute
            action_name = self._determine_action(state)
            
            if not action_name:
                raise ValueError("Could not determine action from state")
            
            logger.info(f"L3 action determined: {action_name}")
            
            # Validate prerequisites
            is_valid, error_msg = await self.validate_prerequisites(action_name, state)
            
            if not is_valid:
                logger.warning(f"Prerequisites not met: {error_msg}")
                l3_output = self._create_prerequisite_error_output(action_name, error_msg)
                state = self._update_state_with_l3_output(state, l3_output)
                return state
            
            # Execute the action
            action_result = await self.execute_action(action_name, state)
            
            # Generate user-facing confirmation message
            confirmation = await self._generate_confirmation_message(
                action_name,
                action_result,
                state
            )
            
            # Determine next steps
            next_steps = self._determine_next_steps(action_name, action_result, state)
            
            # Create L3 output
            l3_output = L3Output(
                action_name=action_name,
                action_status=ActionStatus.SUCCESS if action_result["success"] else ActionStatus.FAILED,
                success=action_result["success"],
                action_result=action_result.get("result_data", {}),
                confirmation_message=confirmation,
                next_steps=next_steps,
                error_code=action_result.get("error_code"),
                error_message=action_result.get("error_message"),
                agent_type=self.agent_name
            )
            
            # Update state with L3 results
            state = self._update_state_with_l3_output(state, l3_output)
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Log execution
            self.log_agent_execution(
                state=state,
                output=l3_output,
                processing_time_ms=processing_time_ms,
                success=action_result["success"]
            )
            
            logger.info(
                f"L3 completed: action={action_name}, "
                f"status={l3_output.action_status.value}, "
                f"time={processing_time_ms:.0f}ms"
            )
            
            return state
        
        except Exception as e:
            logger.error(f"L3 processing failed: {e}")
            
            # Create error output
            error_output = L3Output(
                action_name="unknown",
                action_status=ActionStatus.FAILED,
                success=False,
                confirmation_message="I apologize, but I encountered an error processing your request.",
                error_message=str(e),
                agent_type=self.agent_name
            )
            
            state = self._update_state_with_l3_output(state, error_output)
            state.error_message = f"L3 processing error: {str(e)}"
            
            processing_time_ms = (time.time() - start_time) * 1000
            self.log_agent_execution(
                state=state,
                output=error_output,
                processing_time_ms=processing_time_ms,
                success=False,
                error=str(e)
            )
            
            return state
    
    def build_prompt(self, state: WorkflowState) -> str:
        """
        Build L3 confirmation message prompt.
        
        Args:
            state: Current workflow state
        
        Returns:
            Formatted prompt string
        """
        # L3 uses LLM primarily for generating user-facing messages
        # The actual action execution is done in code
        pass
    
    # ============ Action Determination ============
    
    def _determine_action(self, state: WorkflowState) -> Optional[str]:
        """
        Determine which action to execute based on state.
        
        Args:
            state: Current workflow state
        
        Returns:
            Action name or None if cannot determine
        """
        # Get intent from L2
        if not state.intent_l2:
            logger.warning("No L2 intent found in state")
            return None
        
        intent_name = state.intent_l2.name
        
        # Map intent to action (subclasses can override this mapping)
        action_map = self._get_intent_to_action_map()
        action = action_map.get(intent_name)
        
        if not action:
            # Try to infer from intent name
            # e.g., "book_home_cleaning" → "create_booking"
            if "book" in intent_name or "schedule" in intent_name:
                action = "create_booking"
            elif "quote" in intent_name:
                action = "send_quote"
            elif "complaint" in intent_name:
                action = "create_ticket"
            elif "invoice" in intent_name:
                action = "retrieve_invoice"
            elif "payment" in intent_name:
                action = "process_payment"
        
        # Validate action is supported
        if action and action not in self.get_supported_actions():
            logger.warning(f"Action '{action}' not supported by {self.agent_name}")
            return None
        
        return action
    
    def _get_intent_to_action_map(self) -> Dict[str, str]:
        """
        Get mapping from L2 intents to L3 actions.
        Subclasses should override this for specific mappings.
        
        Returns:
            Dictionary mapping intent names to action names
        """
        return {}
    
    # ============ Confirmation Message Generation ============
    
    async def _generate_confirmation_message(
        self,
        action_name: str,
        action_result: Dict[str, Any],
        state: WorkflowState
    ) -> str:
        """
        Generate user-facing confirmation message using LLM.
        
        Args:
            action_name: Action that was executed
            action_result: Results from action execution
            state: Workflow state
        
        Returns:
            Confirmation message string
        """
        try:
            # Load system prompt if not cached
            if not self.system_prompt:
                await self._load_system_prompt()
            
            # Build prompt for confirmation
            prompt = self._build_confirmation_prompt(action_name, action_result, state)
            
            # Call LLM
            response = await self.call_llm(
                prompt=prompt,
                system_instruction=self.system_prompt
            )
            
            return response.strip()
        
        except Exception as e:
            logger.error(f"Failed to generate confirmation message: {e}")
            # Return fallback confirmation
            return self._get_fallback_confirmation(action_name, action_result)
    
    def _build_confirmation_prompt(
        self,
        action_name: str,
        action_result: Dict[str, Any],
        state: WorkflowState
    ) -> str:
        """Build prompt for confirmation message generation."""
        success = action_result.get("success", False)
        result_data = action_result.get("result_data", {})
        
        prompt = f"""Generate a friendly, professional confirmation message for a customer.

Action Performed: {action_name}
Success: {success}
Result Data: {result_data}

Customer Context:
- Name: {state.caller_profile.get('name', 'Customer') if state.caller_profile else 'Customer'}
- Intent: {state.intent_l2.name if state.intent_l2 else 'unknown'}

Requirements:
1. Be warm and professional
2. Confirm what was done
3. Include key details (booking ID, date/time, etc.)
4. Set clear expectations
5. One paragraph, 2-3 sentences
6. Natural conversational tone

Generate ONLY the confirmation message, no additional text."""
        
        return prompt
    
    def _get_fallback_confirmation(
        self,
        action_name: str,
        action_result: Dict[str, Any]
    ) -> str:
        """Get fallback confirmation message if LLM fails."""
        if action_result.get("success"):
            return f"Your request has been processed successfully. Reference: {action_result.get('result_data', {}).get('id', 'N/A')}"
        else:
            return f"I apologize, but I was unable to complete your request: {action_result.get('error_message', 'Unknown error')}"
    
    # ============ Next Steps Determination ============
    
    def _determine_next_steps(
        self,
        action_name: str,
        action_result: Dict[str, Any],
        state: WorkflowState
    ) -> List[str]:
        """
        Determine next steps for the user.
        
        Args:
            action_name: Action that was executed
            action_result: Results from action execution
            state: Workflow state
        
        Returns:
            List of next step strings
        """
        next_steps = []
        
        if not action_result.get("success"):
            # Failed action - provide recovery steps
            next_steps.append("Please try again or contact support for assistance")
            return next_steps
        
        # Action-specific next steps (override in subclasses for specifics)
        if "booking" in action_name or "schedule" in action_name:
            next_steps.extend([
                "You'll receive a confirmation email shortly",
                "We'll send a reminder 24 hours before your appointment",
                "Need to make changes? Just give us a call"
            ])
        
        elif "quote" in action_name:
            next_steps.extend([
                "Review the quote at your convenience",
                "Ready to book? Just reply to confirm",
                "Questions? We're here to help"
            ])
        
        elif "ticket" in action_name or "complaint" in action_name:
            ticket_id = action_result.get("result_data", {}).get("ticket_id")
            if ticket_id:
                next_steps.append(f"Your ticket #{ticket_id} has been created")
            next_steps.extend([
                "A supervisor will review your case",
                "We'll contact you within 24 hours",
                "Track status anytime by calling us"
            ])
        
        elif "payment" in action_name or "invoice" in action_name:
            next_steps.extend([
                "Receipt sent to your email",
                "Questions about billing? We're here to help"
            ])
        
        return next_steps[:3]  # Limit to 3 next steps
    
    # ============ Validation Helpers ============
    
    def _check_required_slots(
        self,
        state: WorkflowState,
        required_slots: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if all required slots are filled.
        
        Args:
            state: Workflow state
            required_slots: List of required slot names
        
        Returns:
            Tuple of (all_filled, missing_slots_message)
        """
        missing = []
        
        for slot in required_slots:
            if slot not in state.entities or not state.entities[slot]:
                missing.append(slot)
        
        if missing:
            missing_readable = ", ".join([s.replace("_", " ") for s in missing])
            return False, f"Missing required information: {missing_readable}"
        
        return True, None
    
    def _validate_entity_format(
        self,
        entity_name: str,
        entity_value: Any,
        format_type: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate entity format.
        
        Args:
            entity_name: Name of entity
            entity_value: Value to validate
            format_type: Expected format (phone, email, date, etc.)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        import re
        
        if format_type == "phone":
            if not re.match(r'^\d{3}[-.]?\d{3}[-.]?\d{4}$', str(entity_value)):
                return False, f"Invalid phone number format for {entity_name}"
        
        elif format_type == "email":
            if not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', str(entity_value)):
                return False, f"Invalid email format for {entity_name}"
        
        elif format_type == "date":
            # Basic date validation - actual parsing done in action
            if not entity_value:
                return False, f"Missing date for {entity_name}"
        
        return True, None
    
    # ============ State Update and Error Handling ============
    
    def _update_state_with_l3_output(
        self,
        state: WorkflowState,
        l3_output: L3Output
    ) -> WorkflowState:
        """Update workflow state with L3 output."""
        # Update action results
        state.action_result = l3_output.action_result
        state.action_success = l3_output.success
        state.confirmation_message = l3_output.confirmation_message
        state.next_steps = l3_output.next_steps
        
        # Update routing info
        state.current_tier = "L3"
        state.current_agent = self.agent_name
        state.response_text = l3_output.confirmation_message
        
        # Mark as processed
        state.processed = True
        
        # Add to routing history
        from config.routing_config import add_routing_step
        add_routing_step(
            state=state,
            from_tier="L2",
            to_tier="L3",
            reason=f"Action executed: {l3_output.action_name}",
            confidence=1.0 if l3_output.success else 0.0
        )
        
        # Check if escalation needed
        if l3_output.requires_human_escalation:
            state.requires_human_escalation = True
            state.escalation_reason = l3_output.escalation_reason.value if l3_output.escalation_reason else "action_failed"
        
        return state
    
    def _create_prerequisite_error_output(
        self,
        action_name: str,
        error_message: str
    ) -> L3Output:
        """Create L3 output for prerequisite validation failure."""
        return L3Output(
            action_name=action_name,
            action_status=ActionStatus.FAILED,
            success=False,
            confirmation_message=f"I need some additional information before I can help with that. {error_message}",
            error_code="MISSING_PREREQUISITES",
            error_message=error_message,
            requires_human_escalation=False,
            agent_type=self.agent_name
        )
    
    async def _load_system_prompt(self):
        """Load system prompt from database."""
        try:
            prompt_doc = await self.db_service.find_agent_action_prompt(
                agent=self.domain,
                action="l3_confirmation",
                level=1
            )
            
            if prompt_doc:
                self.system_prompt = prompt_doc
                logger.info(f"L3 system prompt loaded for {self.domain}")
            else:
                self.system_prompt = self._get_default_system_prompt()
                logger.warning(f"Using default L3 system prompt for {self.domain}")
        
        except Exception as e:
            logger.error(f"Failed to load L3 system prompt: {e}")
            self.system_prompt = self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for L3."""
        return f"""You are a {self.domain} specialist generating customer confirmations.
Create warm, professional messages that confirm actions taken.
Include key details but keep it concise (2-3 sentences).
Set clear expectations for what happens next.
Always be positive and helpful in tone."""