# ==================== src/workflow/ai_receptionist_workflow.py ====================
"""
LangGraph workflow for AI Receptionist with 3-tier routing.
Updated to use RoutingService for intelligent routing decisions.
"""
import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from src.models.workflow_models import WorkflowState
from src.services.database_service import DatabaseService
from src.services.routing_service import RoutingService

# Import agents
from src.agents.receptionist_l1 import ReceptionistL1
from src.agents.l2_agent_factory import L2AgentFactory
from src.agents.l3_agent_factory import L3AgentFactory

from src.nodes.clarification_handler import ClarificationHandler
from src.nodes.human_escalation import HumanEscalationNode
from src.services.ticket_service import TicketService
from src.services.llm_service import LLMService

# Import routing conditions
from src.workflow.routing_conditions import (
    check_l1_confidence,
    check_l2_confidence,
    check_max_clarifications
)

logger = logging.getLogger(__name__)


class AIReceptionistWorkflow:
    """
    LangGraph workflow for AI receptionist with 3-tier routing.
    
    Workflow Stages:
    1. L1: Broad intent classification + caller type detection
    2. L2: Intent refinement + entity extraction + slot filling
    3. Clarification: Ask for missing information (if needed)
    4. L3: Action execution + confirmation generation
    5. Human Escalation: Transfer to human operator (if needed)
    """
    
    def __init__(self):
        """Initialize the workflow with all necessary services and agents."""
        self.db_service = DatabaseService()
        
        # Initialize routing service
        self.routing_service = RoutingService()

        # Initialize L1 agent
        self.receptionist_l1 = ReceptionistL1(self.db_service)
        
        # Initialize L2 factory
        self.l2_factory = L2AgentFactory(self.db_service)
        
        # Initialize L3 factory
        self.l3_factory = L3AgentFactory(self.db_service)
        
        # Initialize LLM service (if not already created)
        self.llm_service = LLMService()  # or get it from somewhere else
    
        # Initialize ticket service
        self.ticket_service = TicketService(db=self.db_service.db)
    
        self.clarification_handler = ClarificationHandler(llm_service=self.llm_service)
        self.human_escalation_node_handler = HumanEscalationNode(ticket_service=self.ticket_service)

        # Build workflow graph
        self.workflow = self._build_workflow()
        
        logger.info("AIReceptionistWorkflow initialized with RoutingService")
    
    # ============ Node Functions ============
    
    async def l1_classification_node(self, state: WorkflowState) -> WorkflowState:
        """
        L1 Node: Broad intent classification and caller type detection.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with L1 classification
        """
        logger.info("Executing L1 classification node")
        
        try:
            # Run L1 agent
            state = await self.receptionist_l1.process(state)
            
            # Update current tier
            state.current_tier = "L1"
            
            logger.info(
                f"L1 complete: intent={state.intent_l1.name if state.intent_l1 else 'none'}, "
                f"caller_type={state.caller_type.value if state.caller_type and hasattr(state.caller_type, 'value') else state.caller_type or 'unknown'}, "
                f"confidence={state.intent_l1.confidence if state.intent_l1 else 0.0:.2f}"
            )
            
            return state
        
        except Exception as e:
            logger.error(f"L1 node error: {e}")
            state.error_message = f"L1 classification failed: {str(e)}"
            state.requires_human_escalation = True
            state.escalation_reason = "technical_error"
            return state
    
    async def l2_processing_node(self, state: WorkflowState) -> WorkflowState:
        """
        L2 Node: Intent refinement and entity extraction.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with L2 refinement
        """
        logger.info("Executing L2 processing node")
        
        try:
            # Select appropriate L2 agent using routing service
            l2_agent_type = self.routing_service.select_l2_agent(state)
            state.selected_l2_agent = l2_agent_type
            
            logger.info(f"Selected L2 agent: {l2_agent_type}")
            
            # Get L2 agent from factory
            l2_agent = self.l2_factory.get_agent(l2_agent_type)
            
            # Process with L2 agent
            state = await l2_agent.process(state)
            
            # Update current tier
            state.current_tier = "L2"
            
            logger.info(
                f"L2 complete: intent={state.intent_l2.name if state.intent_l2 else 'none'}, "
                f"confidence={state.intent_l2.confidence if state.intent_l2 else 0.0:.2f}, "
                f"required_slots={len(state.required_slots)}, "
                f"filled_slots={len(state.entities)}"
            )
            
            return state
        
        except Exception as e:
            logger.error(f"L2 node error: {e}")
            state.error_message = f"L2 processing failed: {str(e)}"
            state.requires_human_escalation = True
            state.escalation_reason = "technical_error"
            return state
    
    async def l3_execution_node(self, state: WorkflowState) -> WorkflowState:
        """
        L3 Node: Execute domain-specific action.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with L3 execution result
        """
        logger.info("Executing L3 execution node")
        
        try:
            # Select appropriate L3 agent using routing service
            l3_agent_type = self.routing_service.select_l3_agent(state)
            state.selected_l3_agent = l3_agent_type
            
            logger.info(f"Selected L3 agent: {l3_agent_type}")
            
            # Get L3 agent from factory
            l3_agent = self.l3_factory.get_agent(l3_agent_type)
            
            # Process with L3 agent
            state = await l3_agent.process(state)
            
            # Update current tier
            state.current_tier = "L3"
            
            # Mark as processed
            state.processed = True
            
            logger.info(
                f"L3 complete: action={state.action_result.get('action_name', 'unknown') if state.action_result else 'none'}, "
                f"status={state.action_result.get('action_status', 'unknown') if state.action_result else 'none'}"
            )
            
            return state
        
        except Exception as e:
            logger.error(f"L3 node error: {e}")
            state.error_message = f"L3 execution failed: {str(e)}"
            state.requires_human_escalation = True
            state.escalation_reason = "technical_error"
            
            # Generate fallback response
            state.response_text = (
                "I apologize, but I encountered an issue processing your request. "
                "Let me connect you with a team member who can help."
            )
            
            return state
    
    async def clarification_node(self, state: WorkflowState) -> WorkflowState:
        """
        Clarification Node: Ask user for missing information using ClarificationHandler.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with clarification question
        """
        logger.info("Executing clarification node")
        
        try:
            # Use the Phase 6 ClarificationHandler
            state = await self.clarification_handler(state)
            
            logger.info(
                f"Clarification handled (attempt {state.clarification_count}/{state.max_clarifications}): "
                f"awaiting={state.awaiting_clarification}, "
                f"missing_slots={state.missing_slots}"
            )
            
            return state
        
        except Exception as e:
            logger.error(f"Clarification node error: {e}")
            state.error_message = f"Clarification generation failed: {str(e)}"
            state.requires_human_escalation = True
            state.escalation_reason = "clarification_handler_error"
            return state
    
    async def human_escalation_node(self, state: WorkflowState) -> WorkflowState:
        """
        Human Escalation Node: Transfer to human operator using HumanEscalationNode.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with escalation ticket and message
        """
        logger.info(f"Executing human escalation node: reason={state.escalation_reason}")
        
        try:
            # Ensure escalation reason is set
            if not state.escalation_reason:
                if state.error_message:
                    state.escalation_reason = "technical_error"
                elif state.clarification_count >= state.max_clarifications:
                    state.escalation_reason = f"Unable to collect required information after {state.clarification_count} attempts"
                else:
                    state.escalation_reason = "Low confidence in automated response"
            
            # Set escalation priority if not set
            if not state.escalation_priority:
                if "urgent" in state.escalation_reason.lower() or "emergency" in (state.speech_text or "").lower():
                    state.escalation_priority = "urgent"
                elif state.clarification_count >= state.max_clarifications:
                    state.escalation_priority = "high"
                else:
                    state.escalation_priority = "medium"
            
            # ✅ Call the Phase 6 HumanEscalationNode instance (not the method)
            state = await self.human_escalation_node_handler(state)
            
            logger.info(
                f"Escalation complete: ticket_id={state.ticket_id}, "
                f"priority={state.escalation_priority}"
            )
            
            return state
        
        except Exception as e:
            logger.error(f"Human escalation node error: {e}")
            
            # Fallback escalation if Phase 6 node fails
            from datetime import datetime, timezone
            state.ticket_id = f"FALLBACK-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            state.error_message = f"Escalation failed: {str(e)}"
            state.response_text = (
                "I apologize, but I'm experiencing technical difficulties. "
                f"Your reference number is {state.ticket_id}. "
                "Please call our main line for immediate assistance."
            )
            state.processed = True
            state.requires_human_escalation = True
            
            return state
    
    # ============ Routing Condition Methods ============
    
    def should_escalate_after_l1(self, state: WorkflowState) -> Literal["l2", "escalate"]:
        """
        Determine routing after L1 using routing service.
        
        Args:
            state: Current workflow state
        
        Returns:
            "l2" or "escalate"
        """
        decision = self.routing_service.route_from_l1(state)
        logger.info(f"L1 routing decision: {decision}")
        return decision
    
    def route_after_l2(self, state: WorkflowState) -> Literal["clarify", "l3", "escalate"]:
        """
        Determine routing after L2 using routing service.
        
        Args:
            state: Current workflow state
        
        Returns:
            "clarify", "l3", or "escalate"
        """
        decision = self.routing_service.route_from_l2(state)
        logger.info(f"L2 routing decision: {decision}")
        return decision
    
    def route_after_clarification(self, state: WorkflowState) -> Literal["l2", "escalate"]:
        """
        Determine routing after clarification using routing service.
        
        Args:
            state: Current workflow state
        
        Returns:
            "l2" or "escalate"
        """
        decision = self.routing_service.route_from_clarification(state)
        logger.info(f"Clarification routing decision: {decision}")
        return decision
    
    # ============ Workflow Builder ============
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow with 3-tier routing.
        
        Returns:
            Compiled workflow graph
        """
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("l1_classification", self.l1_classification_node)
        workflow.add_node("l2_processing", self.l2_processing_node)
        workflow.add_node("l3_execution", self.l3_execution_node)
        workflow.add_node("clarification", self.clarification_node)
        workflow.add_node("human_escalation", self.human_escalation_node)
        
        # Set entry point
        workflow.set_entry_point("l1_classification")
        
        # Define edges with conditional routing
        
        # After L1: go to L2 or escalate
        workflow.add_conditional_edges(
            "l1_classification",
            self.should_escalate_after_l1,
            {
                "l2": "l2_processing",
                "escalate": "human_escalation"
            }
        )
        
        # After L2: go to clarification, L3, or escalate
        workflow.add_conditional_edges(
            "l2_processing",
            self.route_after_l2,
            {
                "clarify": "clarification",
                "l3": "l3_execution",
                "escalate": "human_escalation"
            }
        )
        
        # After clarification: return to L2 or escalate
        workflow.add_conditional_edges(
            "clarification",
            self.route_after_clarification,
            {
                "l2": "l2_processing",
                "escalate": "human_escalation"
            }
        )
        
        # After L3: done
        workflow.add_edge("l3_execution", END)
        
        # After human escalation: done
        workflow.add_edge("human_escalation", END)
        
        logger.info("Workflow graph built with RoutingService integration")
        
        return workflow.compile()
    
    # ============ Workflow Execution ============
    
    async def initialize(self):
        """Initialize the workflow (connect to database)."""
        await self.db_service.connect()
        logger.info("Workflow initialized and connected to database")
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.db_service.disconnect()
        logger.info("Workflow cleanup complete")
    
    async def process_call(self, call_data: dict) -> WorkflowState:
        """
        Process an incoming call through the workflow.
        
        Args:
            call_data: Dictionary with call_sid, caller_phone, speech_text
        
        Returns:
            Final workflow state
        """
        logger.info(f"Processing call: {call_data.get('call_sid', 'unknown')}")
        
        # Create initial state
        from datetime import datetime, UTC
        initial_state = WorkflowState(
            call_sid=call_data.get("call_sid"),
            caller_phone=call_data.get("caller_phone"),
            speech_text=call_data.get("speech_text"),
            processing_start_time=datetime.now(UTC)
        )
        
        # Run workflow
        try:
            result = await self.workflow.ainvoke(initial_state)
            
            # Calculate total processing time
            if result.processing_start_time:
                from datetime import datetime, UTC
                elapsed = (datetime.now(UTC) - result.processing_start_time).total_seconds() * 1000
                result.total_processing_time_ms = elapsed
            
            # Get routing summary
            routing_summary = self.routing_service.get_routing_summary(result)
            
            logger.info(
                f"Call processing complete: "
                f"success={result.processed}, "
                f"tier={result.current_tier}, "
                f"path={routing_summary['routing_path']}, "
                f"time={result.total_processing_time_ms:.0f}ms"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            initial_state.error_message = f"Workflow failed: {str(e)}"
            initial_state.response_text = "I apologize, but I'm experiencing technical difficulties. Please try again later."
            initial_state.requires_human_escalation = True
            initial_state.escalation_reason = "technical_error"
            return initial_state