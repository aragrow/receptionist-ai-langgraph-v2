# ==================== src/nodes/identity_checker.py ====================
"""Identity checker node for caller identification."""
import logging
# Get a logger instance for your module
logger = logging.getLogger(__name__)
# Set the logging level (e.g., INFO, DEBUG, WARNING, ERROR, CRITICAL)
logger.setLevel(logging.INFO)
import re
from src.models.workflow_models import WorkflowState, CallerType
from src.services.database_service import DatabaseService

class IdentityChecker:
    """Node for identifying callers."""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    async def __call__(self, state: WorkflowState) -> WorkflowState:
        logger.info('Executing IdentityChecker')
        logger.info(f"Inital state: {state}")
        """Check caller identity."""
        if not state.caller_phone:
            state.caller_type = CallerType.LEAD
            return state
        
        caller_phone = self.normalize_phone(state.caller_phone)
        
        try:
            # Check if caller is a client
            logger.info('Checking if caller is a client')
            client = await self.db_service.find_client_by_phone(caller_phone)
            logger.info('Checking Done')
            if client:
                logger.info('Caller is a client')
                state.caller_type = CallerType.CLIENT
                state.client = client
                state.caller_profile = client.dict()
                logger.info(state)
                return state
            else:
                logger.info('Caller is not a client')
            # Check if caller is a vendor
            vendor = await self.db_service.find_vendor_by_phone(caller_phone)
            if vendor:
                state.caller_type = CallerType.VENDOR
                state.vendor = vendor
                state.caller_profile = vendor.dict()
                return state
            else:
                logger.info('Caller is not a vendor')
            # Default to lead
            state.caller_type = CallerType.LEAD
            
        except Exception as e:
            state.error_message = f"Identity check failed: {str(e)}"
            state.caller_type = CallerType.LEAD
        
        return state
    
    def normalize_phone(self, number: str) -> str:
        digits = re.sub(r"\D", "", number)  # Remove all non-digits
        if len(digits) == 10:
            return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
        elif len(digits) == 11 and digits[0] == "1":  # +1 prefix
                return f"{digits[1:4]}-{digits[4:7]}-{digits[7:11]}"
        raise ValueError("Phone must have 10 or 11 digits")