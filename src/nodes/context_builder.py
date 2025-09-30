# ==================== src/nodes/context_builder.py ====================
"""Context builder node."""

from src.models.workflow_models import WorkflowState, CallerType
from src.services.context_service import ContextService


class ContextBuilder:
    """Node for building caller context."""
    
    def __init__(self, context_service: ContextService):
        self.context_service = context_service
    
    async def __call__(self, state: WorkflowState) -> WorkflowState:
        print("""Build context based on caller type.""")
        try:
            if state.caller_type == CallerType.CLIENT and state.client:
                state.context_data = await self.context_service.build_client_context(state.client)
            
            elif state.caller_type == CallerType.VENDOR and state.vendor:
                state.context_data = await self.context_service.build_vendor_context(state.vendor)
            
            else:  # LEAD
                state.context_data = await self.context_service.build_lead_context()
        
        except Exception as e:
            state.error_message = f"Context building failed: {str(e)}"
            state.context_data = {}
        
        return state