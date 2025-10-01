# ==================== src/agents/sales_agent_l3.py ====================
"""
Sales Agent L3 - Domain specialist for sales/booking operations.
Handles: new bookings, quotes, service inquiries, availability checks.
"""

import logging
from typing import Dict, Any, List

from src.agents.l3_base_agent import L3BaseAgent
from src.models.workflow_models import WorkflowState
from src.services.database_service import DatabaseService
from src.actions.booking_actions import BookingActions

logger = logging.getLogger(__name__)


class SalesAgentL3(L3BaseAgent):
    """
    Sales domain specialist - handles all sales and booking operations.
    
    Supported Actions:
    - create_booking: Book a new service
    - request_quote: Generate a price quote
    - check_availability: Check if a time slot is available
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize Sales Agent L3.
        
        Args:
            db_service: Database service for data access
        """
        super().__init__(
            agent_name="sales_agent_l3",
            domain="sales",
            db_service=db_service
        )
        
        # Initialize action handler
        self.booking_actions = BookingActions(db_service)
        
        logger.info("SalesAgentL3 initialized")
    
    def get_supported_actions(self) -> List[str]:
        """
        Get list of actions this agent can perform.
        
        Returns:
            List of action names
        """
        return [
            "create_booking",
            "request_quote",
            "check_availability"
        ]
    
    async def validate_prerequisites(
        self,
        action_name: str,
        state: WorkflowState
    ) -> tuple[bool, str | None]:
        """
        Validate that all prerequisites are met for the action.
        
        Args:
            action_name: Name of action to validate
            state: Current workflow state
        
        Returns:
            (is_valid, error_message)
        """
        entities = state.entities
        
        if action_name == "create_booking":
            # Required: service_type, scheduled_date, address, contact_number
            required_slots = ["service_type", "scheduled_date", "address", "contact_number"]
            return self._check_required_slots(state, required_slots)
        
        elif action_name == "request_quote":
            # Required: service_type, contact_number
            # Optional but helpful: address, property_details
            required_slots = ["service_type", "contact_number"]
            return self._check_required_slots(state, required_slots)
        
        elif action_name == "check_availability":
            # Required: requested_date, service_type
            required_slots = ["requested_date", "service_type"]
            return self._check_required_slots(state, required_slots)
        
        else:
            return False, f"Unknown action: {action_name}"
    
    async def execute_action(
        self,
        action_name: str,
        state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Execute the sales action.
        
        Args:
            action_name: Name of action to execute
            state: Current workflow state with all required information
        
        Returns:
            Dictionary with action results
        """
        entities = state.entities
        
        try:
            if action_name == "create_booking":
                return await self._create_booking(state)
            
            elif action_name == "request_quote":
                return await self._request_quote(state)
            
            elif action_name == "check_availability":
                return await self._check_availability(state)
            
            else:
                return {
                    "success": False,
                    "error_code": "UNKNOWN_ACTION",
                    "error_message": f"Unknown action: {action_name}"
                }
        
        except Exception as e:
            logger.error(f"Action execution failed: {action_name} - {e}")
            return {
                "success": False,
                "error_code": "EXECUTION_ERROR",
                "error_message": str(e)
            }
    
    # ============ Action Implementations ============
    
    async def _create_booking(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Create a new booking.
        
        Args:
            state: Workflow state with booking details
        
        Returns:
            Booking result dictionary
        """
        entities = state.entities
        
        # Extract booking details
        client_id = str(state.client.id) if state.client else None
        property_id = entities.get("property_id")
        service_type = entities.get("service_type")
        scheduled_date = entities.get("scheduled_date")
        address = entities.get("address")
        contact_number = entities.get("contact_number") or state.caller_phone
        contact_email = entities.get("contact_email")
        special_instructions = entities.get("special_instructions")
        recurrence = entities.get("recurrence", "one-time")
        
        # Create booking
        result = await self.booking_actions.create_booking(
            client_id=client_id,
            property_id=property_id,
            service_type=service_type,
            scheduled_date=scheduled_date,
            address=address,
            contact_number=contact_number,
            contact_email=contact_email,
            special_instructions=special_instructions,
            recurrence=recurrence
        )
        
        return result
    
    async def _request_quote(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Generate a price quote.
        
        Args:
            state: Workflow state with quote details
        
        Returns:
            Quote result dictionary
        """
        entities = state.entities
        
        # Extract quote details
        service_type = entities.get("service_type")
        contact_number = entities.get("contact_number") or state.caller_phone
        contact_email = entities.get("contact_email")
        
        # Build property details
        property_details = {
            "bedrooms": entities.get("bedrooms", 3),
            "bathrooms": entities.get("bathrooms", 2),
            "square_feet": entities.get("square_feet", 2000),
            "property_type": entities.get("property_type", "house")
        }
        
        # If address provided, could look up property details
        if entities.get("address"):
            property_details["address"] = entities.get("address")
        
        # Generate quote
        result = await self.booking_actions.request_quote(
            service_type=service_type,
            property_details=property_details,
            contact_number=contact_number,
            contact_email=contact_email
        )
        
        return result
    
    async def _check_availability(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Check availability for a requested time slot.
        
        Args:
            state: Workflow state with requested date
        
        Returns:
            Availability result dictionary
        """
        entities = state.entities
        
        # Extract availability check details
        requested_date = entities.get("requested_date") or entities.get("scheduled_date")
        service_type = entities.get("service_type")
        duration_hours = entities.get("duration_hours", 2)
        
        # Check availability
        result = await self.booking_actions.check_availability(
            requested_date=requested_date,
            service_type=service_type,
            duration_hours=duration_hours
        )
        
        return result