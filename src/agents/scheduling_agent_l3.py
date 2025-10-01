# ==================== src/agents/scheduling_agent_l3.py ====================
"""
Scheduling Agent L3 - Domain specialist for appointment management.
Handles: rescheduling, cancellations, viewing appointments.
"""

import logging
from typing import Dict, Any, List

from src.agents.l3_base_agent import L3BaseAgent
from src.models.workflow_models import WorkflowState
from src.services.database_service import DatabaseService
from src.actions.scheduling_actions import SchedulingActions

logger = logging.getLogger(__name__)


class SchedulingAgentL3(L3BaseAgent):
    """
    Scheduling domain specialist - handles all appointment management.
    
    Supported Actions:
    - reschedule_appointment: Reschedule an existing appointment
    - cancel_appointment: Cancel an appointment
    - get_upcoming_appointments: View upcoming appointments
    - find_next_available_slot: Find next available time slot
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize Scheduling Agent L3.
        
        Args:
            db_service: Database service for data access
        """
        super().__init__(
            agent_name="scheduling_agent_l3",
            domain="scheduling",
            db_service=db_service
        )
        
        # Initialize action handler
        self.scheduling_actions = SchedulingActions(db_service)
        
        logger.info("SchedulingAgentL3 initialized")
    
    def get_supported_actions(self) -> List[str]:
        """
        Get list of actions this agent can perform.
        
        Returns:
            List of action names
        """
        return [
            "reschedule_appointment",
            "cancel_appointment",
            "get_upcoming_appointments",
            "find_next_available_slot"
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
        
        if action_name == "reschedule_appointment":
            # Required: job_id, new_date
            required_slots = ["job_id", "new_date"]
            return self._check_required_slots(state, required_slots)
        
        elif action_name == "cancel_appointment":
            # Required: job_id
            required_slots = ["job_id"]
            return self._check_required_slots(state, required_slots)
        
        elif action_name == "get_upcoming_appointments":
            # Required: client_id (from state.client)
            if not state.client:
                return False, "Client identification required to view appointments"
            return True, None
        
        elif action_name == "find_next_available_slot":
            # Required: service_type
            required_slots = ["service_type"]
            return self._check_required_slots(state, required_slots)
        
        else:
            return False, f"Unknown action: {action_name}"
    
    async def execute_action(
        self,
        action_name: str,
        state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Execute the scheduling action.
        
        Args:
            action_name: Name of action to execute
            state: Current workflow state with all required information
        
        Returns:
            Dictionary with action results
        """
        try:
            if action_name == "reschedule_appointment":
                return await self._reschedule_appointment(state)
            
            elif action_name == "cancel_appointment":
                return await self._cancel_appointment(state)
            
            elif action_name == "get_upcoming_appointments":
                return await self._get_upcoming_appointments(state)
            
            elif action_name == "find_next_available_slot":
                return await self._find_next_available_slot(state)
            
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
    
    async def _reschedule_appointment(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Reschedule an existing appointment.
        
        Args:
            state: Workflow state with reschedule details
        
        Returns:
            Reschedule result dictionary
        """
        entities = state.entities
        
        # Extract reschedule details
        job_id = entities.get("job_id")
        new_date = entities.get("new_date")
        reason = entities.get("reason")
        
        # Reschedule
        result = await self.scheduling_actions.reschedule_appointment(
            job_id=job_id,
            new_date=new_date,
            reason=reason
        )
        
        return result
    
    async def _cancel_appointment(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Cancel an appointment.
        
        Args:
            state: Workflow state with cancellation details
        
        Returns:
            Cancellation result dictionary
        """
        entities = state.entities
        
        # Extract cancellation details
        job_id = entities.get("job_id")
        reason = entities.get("reason")
        refund_requested = entities.get("refund_requested", False)
        
        # Cancel
        result = await self.scheduling_actions.cancel_appointment(
            job_id=job_id,
            reason=reason,
            refund_requested=refund_requested
        )
        
        return result
    
    async def _get_upcoming_appointments(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Get upcoming appointments for the client.
        
        Args:
            state: Workflow state with client info
        
        Returns:
            Appointments list result dictionary
        """
        # Extract client ID
        client_id = str(state.client.id) if state.client else None
        
        if not client_id:
            return {
                "success": False,
                "error_code": "CLIENT_NOT_FOUND",
                "error_message": "Client identification required"
            }
        
        # Get appointments
        result = await self.scheduling_actions.get_upcoming_appointments(
            client_id=client_id,
            limit=10
        )
        
        return result
    
    async def _find_next_available_slot(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Find the next available appointment slot.
        
        Args:
            state: Workflow state with service type
        
        Returns:
            Available slot result dictionary
        """
        entities = state.entities
        
        # Extract availability search details
        service_type = entities.get("service_type")
        preferred_date = entities.get("preferred_date")
        duration_hours = entities.get("duration_hours", 2)
        
        # Find slot
        result = await self.scheduling_actions.find_next_available_slot(
            service_type=service_type,
            preferred_date=preferred_date,
            duration_hours=duration_hours
        )
        
        return result