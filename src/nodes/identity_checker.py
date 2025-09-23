# ==================== src/nodes/identity_checker.py ====================
"""Identity checker node for caller identification."""

from src.models.workflow_models import WorkflowState, CallerType
from src.services.database_service import DatabaseService


class IdentityChecker:
    """Node for identifying callers."""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def __call__(self, state: WorkflowState) -> WorkflowState:
        """Check caller identity."""
        if not state.caller_phone:
            state.caller_type = CallerType.LEAD
            return state
        
        try:
            # Check if caller is a client
            client = await self.db_service.find_client_by_phone(state.caller_phone)
            if client:
                state.caller_type = CallerType.CLIENT
                state.client = client
                state.caller_profile = client.dict()
                return state
            
            # Check if caller is a vendor
            vendor = await self.db_service.find_vendor_by_phone(state.caller_phone)
            if vendor:
                state.caller_type = CallerType.VENDOR
                state.vendor = vendor
                state.caller_profile = vendor.dict()
                return state
            
            # Default to lead
            state.caller_type = CallerType.LEAD
            
        except Exception as e:
            state.error_message = f"Identity check failed: {str(e)}"
            state.caller_type = CallerType.LEAD
        
        return state