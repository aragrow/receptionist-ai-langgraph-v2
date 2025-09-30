# ==================== src/agents/l2_agent_factory.py ====================
"""
L2 Agent Factory - Creates appropriate L2 agent based on caller type.
Provides a unified interface for instantiating specialized L2 agents.
"""

import logging
from typing import Optional

from src.models.workflow_models import CallerType
from src.services.database_service import DatabaseService

# Import all L2 agents
from src.agents.receptionist_l2_base import ReceptionistL2Base
from src.agents.client_receptionist_l2 import ClientReceptionistL2
from src.agents.prospect_receptionist_l2 import ProspectReceptionistL2
from src.agents.partner_receptionist_l2 import PartnerReceptionistL2
from src.agents.general_receptionist_l2 import GeneralReceptionistL2

logger = logging.getLogger(__name__)


class L2AgentFactory:
    """
    Factory for creating L2 agents based on caller type.
    Maintains a registry of agent types and handles instantiation.
    """
    
    # Registry mapping caller types to agent classes
    AGENT_REGISTRY = {
        CallerType.CLIENT: ClientReceptionistL2,
        CallerType.PROSPECT: ProspectReceptionistL2,
        CallerType.LEAD: ProspectReceptionistL2,  # Leads treated as prospects
        CallerType.PARTNER: PartnerReceptionistL2,
        CallerType.VENDOR: PartnerReceptionistL2,  # Vendors treated as partners
        CallerType.UNKNOWN: GeneralReceptionistL2,
    }
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize L2 Agent Factory.
        
        Args:
            db_service: Database service for agent initialization
        """
        self.db_service = db_service
        self._agent_cache = {}  # Cache instantiated agents
        
        logger.info("L2AgentFactory initialized")
    
    def create_agent(
        self,
        caller_type: CallerType,
        use_cache: bool = True
    ) -> ReceptionistL2Base:
        """
        Create (or retrieve cached) L2 agent for the given caller type.
        
        Args:
            caller_type: Type of caller
            use_cache: Whether to use cached agent instance (default: True)
        
        Returns:
            Appropriate L2 agent instance
        
        Raises:
            ValueError: If caller type is not supported
        """
        # Check cache first if enabled
        if use_cache and caller_type in self._agent_cache:
            logger.debug(f"Using cached L2 agent for {caller_type.value}")
            return self._agent_cache[caller_type]
        
        # Get agent class from registry
        agent_class = self.AGENT_REGISTRY.get(caller_type)
        
        if not agent_class:
            logger.warning(
                f"No L2 agent registered for caller type: {caller_type.value}, "
                f"defaulting to GeneralReceptionistL2"
            )
            agent_class = GeneralReceptionistL2
        
        # Instantiate agent
        try:
            agent = agent_class(db_service=self.db_service)
            
            # Cache if enabled
            if use_cache:
                self._agent_cache[caller_type] = agent
            
            logger.info(f"Created L2 agent: {agent.agent_name} for {caller_type.value}")
            return agent
        
        except Exception as e:
            logger.error(f"Failed to create L2 agent for {caller_type.value}: {e}")
            raise
    
    def get_agent_by_name(self, agent_name: str) -> Optional[ReceptionistL2Base]:
        """
        Get cached agent by name.
        
        Args:
            agent_name: Name of the agent
        
        Returns:
            Agent instance if found in cache, None otherwise
        """
        for agent in self._agent_cache.values():
            if agent.agent_name == agent_name:
                return agent
        return None
    
    def clear_cache(self):
        """Clear the agent cache."""
        self._agent_cache.clear()
        logger.info("L2 agent cache cleared")
    
    def get_supported_caller_types(self) -> list[CallerType]:
        """
        Get list of supported caller types.
        
        Returns:
            List of CallerType enums
        """
        return list(self.AGENT_REGISTRY.keys())
    
    def get_agent_info(self) -> dict[str, str]:
        """
        Get information about registered agents.
        
        Returns:
            Dictionary mapping caller type to agent class name
        """
        return {
            caller_type.value: agent_class.__name__
            for caller_type, agent_class in self.AGENT_REGISTRY.items()
        }


# ============ Convenience Functions ============

def create_l2_agent_for_caller(
    caller_type: CallerType,
    db_service: DatabaseService
) -> ReceptionistL2Base:
    """
    Convenience function to create an L2 agent.
    
    Args:
        caller_type: Type of caller
        db_service: Database service
    
    Returns:
        Appropriate L2 agent instance
    """
    factory = L2AgentFactory(db_service)
    return factory.create_agent(caller_type)


def get_l2_agent_class(caller_type: CallerType) -> type:
    """
    Get the agent class for a caller type without instantiating.
    
    Args:
        caller_type: Type of caller
    
    Returns:
        Agent class (not instance)
    """
    return L2AgentFactory.AGENT_REGISTRY.get(
        caller_type,
        GeneralReceptionistL2
    )