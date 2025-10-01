# ==================== src/agents/l3_agent_factory.py ====================
"""
L3 Agent Factory - Creates appropriate L3 domain specialist agents.
Routes to the correct agent based on refined intent from L2.
"""

import logging
from typing import Optional

from src.agents.l3_base_agent import L3BaseAgent
from src.agents.sales_agent_l3 import SalesAgentL3
from src.agents.support_agent_l3 import SupportAgentL3
from src.agents.scheduling_agent_l3 import SchedulingAgentL3
from src.agents.billing_agent_l3 import BillingAgentL3
from src.agents.partner_agent_l3 import PartnerAgentL3
from src.agents.general_agent_l3 import GeneralAgentL3
from src.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class L3AgentFactory:
    """
    Factory for creating L3 domain specialist agents.
    
    Maps refined intents to appropriate L3 agents:
    - Sales intents -> SalesAgentL3
    - Support intents -> SupportAgentL3
    - Scheduling intents -> SchedulingAgentL3
    - Billing intents -> BillingAgentL3
    - Partner intents -> PartnerAgentL3
    - General intents -> GeneralAgentL3
    """
    
    # Intent to L3 agent mapping
    INTENT_TO_AGENT_MAP = {
        # Sales/Booking intents
        "book_first_service": SalesAgentL3,
        "book_additional_service": SalesAgentL3,
        "request_quote": SalesAgentL3,
        "check_availability": SalesAgentL3,
        "service_inquiry": SalesAgentL3,
        
        # Support intents
        "service_complaint": SupportAgentL3,
        "service_issue": SupportAgentL3,
        "technical_problem": SupportAgentL3,
        "request_callback": SupportAgentL3,
        "general_complaint": SupportAgentL3,
        
        # Scheduling intents
        "reschedule_service": SchedulingAgentL3,
        "cancel_service": SchedulingAgentL3,
        "view_appointments": SchedulingAgentL3,
        "find_available_slot": SchedulingAgentL3,
        
        # Billing intents
        "check_account_balance": BillingAgentL3,
        "payment_inquiry": BillingAgentL3,
        "invoice_request": BillingAgentL3,
        "payment_plan_request": BillingAgentL3,
        "billing_dispute": BillingAgentL3,
        
        # Partner/Vendor intents
        "vendor_checkin": PartnerAgentL3,
        "vendor_checkout": PartnerAgentL3,
        "assignment_update": PartnerAgentL3,
        "report_completion": PartnerAgentL3,
        "supply_request": PartnerAgentL3,
        
        # General intents
        "business_hours_inquiry": GeneralAgentL3,
        "service_info_inquiry": GeneralAgentL3,
        "location_inquiry": GeneralAgentL3,
        "faq": GeneralAgentL3,
        "general_inquiry": GeneralAgentL3,
    }
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize L3 Agent Factory.
        
        Args:
            db_service: Database service for agent initialization
        """
        self.db_service = db_service
        self._agent_cache = {}
        
        logger.info("L3AgentFactory initialized")
    
    def create_agent(self, intent_name: str) -> L3BaseAgent:
        """
        Create appropriate L3 agent based on refined intent.
        
        Args:
            intent_name: Refined intent from L2 agent
        
        Returns:
            L3BaseAgent instance
        
        Raises:
            ValueError: If intent is unknown
        """
        # Check cache first
        agent_class = self.INTENT_TO_AGENT_MAP.get(intent_name)
        
        if not agent_class:
            logger.warning(f"Unknown intent '{intent_name}', defaulting to GeneralAgentL3")
            agent_class = GeneralAgentL3
        
        # Check if agent is already cached
        agent_class_name = agent_class.__name__
        if agent_class_name not in self._agent_cache:
            logger.info(f"Creating new L3 agent: {agent_class_name}")
            self._agent_cache[agent_class_name] = agent_class(self.db_service)
        else:
            logger.debug(f"Using cached L3 agent: {agent_class_name}")
        
        return self._agent_cache[agent_class_name]
    
    def get_agent_for_domain(self, domain: str) -> L3BaseAgent:
        """
        Create agent based on domain name.
        
        Args:
            domain: Domain name (sales, support, scheduling, billing, partner, general)
        
        Returns:
            L3BaseAgent instance
        """
        domain_to_agent = {
            "sales": SalesAgentL3,
            "support": SupportAgentL3,
            "scheduling": SchedulingAgentL3,
            "billing": BillingAgentL3,
            "partner": PartnerAgentL3,
            "general": GeneralAgentL3,
        }
        
        agent_class = domain_to_agent.get(domain.lower(), GeneralAgentL3)
        agent_class_name = agent_class.__name__
        
        if agent_class_name not in self._agent_cache:
            self._agent_cache[agent_class_name] = agent_class(self.db_service)
        
        return self._agent_cache[agent_class_name]
    
    def clear_cache(self):
        """Clear the agent cache."""
        self._agent_cache.clear()
        logger.info("L3 agent cache cleared")
    
    def get_supported_intents(self) -> list[str]:
        """
        Get list of all supported intents.
        
        Returns:
            List of intent names
        """
        return list(self.INTENT_TO_AGENT_MAP.keys())
    
    def get_agent_info(self) -> dict[str, str]:
        """
        Get information about registered agents.
        
        Returns:
            Dictionary mapping intent to agent class name
        """
        return {
            intent: agent_class.__name__
            for intent, agent_class in self.INTENT_TO_AGENT_MAP.items()
        }


# ============ Convenience Functions ============

def create_l3_agent_for_intent(
    intent_name: str,
    db_service: DatabaseService
) -> L3BaseAgent:
    """
    Convenience function to create an L3 agent for a specific intent.
    
    Args:
        intent_name: Refined intent name
        db_service: Database service
    
    Returns:
        L3BaseAgent instance
    """
    factory = L3AgentFactory(db_service)
    return factory.create_agent(intent_name)


def get_l3_agent_class(intent_name: str) -> type:
    """
    Get the agent class for an intent without instantiating.
    
    Args:
        intent_name: Refined intent name
    
    Returns:
        Agent class (not instance)
    """
    return L3AgentFactory.INTENT_TO_AGENT_MAP.get(
        intent_name,
        GeneralAgentL3
    )