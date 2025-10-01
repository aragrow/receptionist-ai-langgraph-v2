# ==================== src/nodes/identity_checker.py ====================
"""Identity checker node for caller identification with telemetry."""
import logging
import re
from datetime import datetime
from src.models.workflow_models import WorkflowState, CallerType
from src.services.database_service import DatabaseService

# Import telemetry services (with graceful fallback)
try:
    from src.services.metrics_service import get_metrics_service
    from src.services.logging_service import get_logging_service
    TELEMETRY_ENABLED = True
except ImportError:
    TELEMETRY_ENABLED = False

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IdentityChecker:
    """Node for identifying callers with telemetry tracking."""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        
        # Initialize telemetry services if available
        if TELEMETRY_ENABLED:
            self.metrics = get_metrics_service()
            self.telemetry_logger = get_logging_service()
        else:
            self.metrics = None
            self.telemetry_logger = None
            logger.warning("Telemetry services not available for IdentityChecker")
    
    async def __call__(self, state: WorkflowState) -> WorkflowState:
        """Check caller identity with metrics tracking."""
        start_time = datetime.now(datetime.UTC)
        logger.info('Executing IdentityChecker')
        logger.info(f"Initial state: {state}")
        
        # Log session start if telemetry enabled
        if self.telemetry_logger:
            self.telemetry_logger.log_session_start(
                session_id=state.session_id or "unknown",
                caller_type="unknown",
                initial_message=state.speech_text or "No speech text"
            )
        
        # Handle missing phone number
        if not state.caller_phone:
            state.caller_type = CallerType.LEAD
            
            # Log identity determination
            if self.telemetry_logger:
                self.telemetry_logger.log_l1_classification(
                    session_id=state.session_id or "unknown",
                    intent="identity_check",
                    confidence=1.0,
                    caller_type="lead",
                    processing_time_ms=0,
                    raw_output={"reason": "no_phone_provided"}
                )
            
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
                
                # Calculate processing time
                end_time = datetime.now(datetime.UTC)
                processing_time_ms = (end_time - start_time).total_seconds() * 1000
                
                # Log successful client identification
                if self.telemetry_logger:
                    self.telemetry_logger.log_l1_classification(
                        session_id=state.session_id or "unknown",
                        intent="identity_check",
                        confidence=1.0,
                        caller_type="client",
                        processing_time_ms=processing_time_ms,
                        raw_output={
                            "client_id": str(client.id),
                            "client_name": client.name,
                            "phone": caller_phone
                        }
                    )
                
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
                
                # Calculate processing time
                end_time = datetime.now(datetime.UTC)
                processing_time_ms = (end_time - start_time).total_seconds() * 1000
                
                # Log successful vendor identification
                if self.telemetry_logger:
                    self.telemetry_logger.log_l1_classification(
                        session_id=state.session_id or "unknown",
                        intent="identity_check",
                        confidence=1.0,
                        caller_type="vendor",
                        processing_time_ms=processing_time_ms,
                        raw_output={
                            "vendor_id": str(vendor.id),
                            "vendor_name": vendor.name,
                            "phone": caller_phone
                        }
                    )
                
                return state
            else:
                logger.info('Caller is not a vendor')
            
            # Default to lead
            state.caller_type = CallerType.LEAD
            
            # Calculate processing time
            end_time = datetime.now(datetime.UTC)
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log lead identification
            if self.telemetry_logger:
                self.telemetry_logger.log_l1_classification(
                    session_id=state.session_id or "unknown",
                    intent="identity_check",
                    confidence=0.8,  # Lower confidence for unknown callers
                    caller_type="lead",
                    processing_time_ms=processing_time_ms,
                    raw_output={
                        "phone": caller_phone,
                        "reason": "not_found_in_database"
                    }
                )
            
        except Exception as e:
            state.error_message = f"Identity check failed: {str(e)}"
            state.caller_type = CallerType.LEAD
            
            # Log error
            if self.telemetry_logger:
                self.telemetry_logger.log_system_error(
                    message="Identity check failed",
                    error=e,
                    context={
                        "session_id": state.session_id or "unknown",
                        "phone": caller_phone
                    }
                )
        
        return state
    
    def normalize_phone(self, number: str) -> str:
        """Normalize phone number to XXX-XXX-XXXX format."""
        digits = re.sub(r"\D", "", number)  # Remove all non-digits
        if len(digits) == 10:
            return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
        elif len(digits) == 11 and digits[0] == "1":  # +1 prefix
            return f"{digits[1:4]}-{digits[4:7]}-{digits[7:11]}"
        raise ValueError("Phone must have 10 or 11 digits")