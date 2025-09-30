# ==================== src/workflow/ai_receptionist_workflow.py ====================
"""LangGraph workflow for AI Receptionist analysis."""
import logging
# Get a logger instance for your module
logger = logging.getLogger(__name__)
# Set the logging level (e.g., INFO, DEBUG, WARNING, ERROR, CRITICAL)
logger.setLevel(logging.INFO)

from langgraph.graph import StateGraph, END

from src.models.workflow_models import WorkflowState
from src.services.database_service import DatabaseService
from src.services.context_service import ContextService
from src.nodes.identity_checker import IdentityChecker
from src.nodes.context_builder import ContextBuilder
from src.nodes.intent_analyzer import IntentAnalyzer
from src.nodes.response_generator import ResponseGenerator


class AIReceptionistWorkflow:
    """LangGraph workflow for AI receptionist processing."""
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.context_service = ContextService(self.db_service)
        
        # Initialize nodes
        self.identity_checker = IdentityChecker(self.db_service)
        self.context_builder = ContextBuilder(self.context_service)
        self.intent_analyzer = IntentAnalyzer(self.db_service)
        self.response_generator = ResponseGenerator()
        
        # Build workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("identity_check", self.identity_checker)
        #workflow.add_node("context_build", self.context_builder)
        workflow.add_node("intent_analysis", self.intent_analyzer)
        workflow.add_node("response_generation", self.response_generator)
        
        # Define edges
        workflow.set_entry_point("identity_check")
        workflow.add_edge("identity_check", "intent_analysis")
        #workflow.add_edge("context_build", "intent_analysis")
        workflow.add_edge("intent_analysis", "response_generation")
        workflow.add_edge("response_generation", END)
        
        return workflow.compile()
    
    async def initialize(self):
        """Initialize the workflow (connect to database)."""
        await self.db_service.connect()
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.db_service.disconnect()
    
    async def process_call(self, call_data: dict) -> WorkflowState:
        logger.info("Processing the call.")
        # Create initial state

        initial_state = WorkflowState(
            call_sid=call_data.get("call_sid"),
            caller_phone=call_data.get("caller_phone"),
            speech_text=call_data.get("speech_text")
        )
        
        # Run workflow
        result = await self.workflow.ainvoke(initial_state)
        return result