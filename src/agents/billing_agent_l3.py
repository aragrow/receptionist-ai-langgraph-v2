# ==================== src/agents/billing_agent_l3.py ====================
"""
Billing Agent L3 - Domain specialist for billing and payment operations.
Handles: invoices, payments, account balance, payment plans.
"""

import logging
from typing import Dict, Any, List

from src.agents.l3_base_agent import L3BaseAgent
from src.models.workflow_models import WorkflowState
from src.services.database_service import DatabaseService
from src.actions.billing_actions import BillingActions

logger = logging.getLogger(__name__)


class BillingAgentL3(L3BaseAgent):
    """
    Billing domain specialist - handles all billing and payment operations.
    
    Supported Actions:
    - get_account_balance: Get current account balance
    - send_invoice: Send an invoice for a job
    - process_payment: Process a payment
    - request_payment_plan: Set up a payment plan
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize Billing Agent L3.
        
        Args:
            db_service: Database service for data access
        """
        super().__init__(
            agent_name="billing_agent_l3",
            domain="billing",
            db_service=db_service
        )
        
        # Initialize action handler
        self.billing_actions = BillingActions(db_service)
        
        logger.info("BillingAgentL3 initialized")
    
    def get_supported_actions(self) -> List[str]:
        """
        Get list of actions this agent can perform.
        
        Returns:
            List of action names
        """
        return [
            "get_account_balance",
            "send_invoice",
            "process_payment",
            "request_payment_plan"
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
        
        if action_name == "get_account_balance":
            # Required: client_id (from state.client)
            if not state.client:
                return False, "Client identification required to view account balance"
            return True, None
        
        elif action_name == "send_invoice":
            # Required: job_id, amount
            required_slots = ["job_id", "amount"]
            return self._check_required_slots(state, required_slots)
        
        elif action_name == "process_payment":
            # Required: invoice_id, amount, payment_method
            required_slots = ["invoice_id", "amount", "payment_method"]
            return self._check_required_slots(state, required_slots)
        
        elif action_name == "request_payment_plan":
            # Required: total_amount, num_installments
            if not state.client:
                return False, "Client identification required for payment plans"
            required_slots = ["total_amount", "num_installments"]
            return self._check_required_slots(state, required_slots)
        
        else:
            return False, f"Unknown action: {action_name}"
    
    async def execute_action(
        self,
        action_name: str,
        state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Execute the billing action.
        
        Args:
            action_name: Name of action to execute
            state: Current workflow state with all required information
        
        Returns:
            Dictionary with action results
        """
        try:
            if action_name == "get_account_balance":
                return await self._get_account_balance(state)
            
            elif action_name == "send_invoice":
                return await self._send_invoice(state)
            
            elif action_name == "process_payment":
                return await self._process_payment(state)
            
            elif action_name == "request_payment_plan":
                return await self._request_payment_plan(state)
            
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
    
    async def _get_account_balance(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Get account balance for the client.
        
        Args:
            state: Workflow state with client info
        
        Returns:
            Account balance result dictionary
        """
        # Extract client ID
        client_id = str(state.client.id) if state.client else None
        
        if not client_id:
            return {
                "success": False,
                "error_code": "CLIENT_NOT_FOUND",
                "error_message": "Client identification required"
            }
        
        # Get balance
        result = await self.billing_actions.get_account_balance(
            client_id=client_id
        )
        
        return result
    
    async def _send_invoice(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Send an invoice for a job.
        
        Args:
            state: Workflow state with invoice details
        
        Returns:
            Invoice sending result dictionary
        """
        entities = state.entities
        
        # Extract invoice details
        job_id = entities.get("job_id")
        amount = float(entities.get("amount"))
        due_date = entities.get("due_date")
        items = entities.get("items")
        
        # Send invoice
        result = await self.billing_actions.send_invoice(
            job_id=job_id,
            amount=amount,
            due_date=due_date,
            items=items
        )
        
        return result
    
    async def _process_payment(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Process a payment.
        
        Args:
            state: Workflow state with payment details
        
        Returns:
            Payment processing result dictionary
        """
        entities = state.entities
        
        # Extract payment details
        invoice_id = entities.get("invoice_id")
        amount = float(entities.get("amount"))
        payment_method = entities.get("payment_method")
        confirmation_number = entities.get("confirmation_number")
        
        # Process payment
        result = await self.billing_actions.process_payment(
            invoice_id=invoice_id,
            amount=amount,
            payment_method=payment_method,
            confirmation_number=confirmation_number
        )
        
        return result
    
    async def _request_payment_plan(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Set up a payment plan.
        
        Args:
            state: Workflow state with payment plan details
        
        Returns:
            Payment plan result dictionary
        """
        entities = state.entities
        
        # Extract payment plan details
        client_id = str(state.client.id) if state.client else None
        total_amount = float(entities.get("total_amount"))
        num_installments = int(entities.get("num_installments"))
        
        # Create payment plan
        result = await self.billing_actions.request_payment_plan(
            client_id=client_id,
            total_amount=total_amount,
            num_installments=num_installments
        )
        
        return result