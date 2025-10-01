# ==================== src/agents/general_agent_l3.py ====================
"""
General Agent L3 - Domain specialist for general information and FAQs.
Handles: business hours, service info, general inquiries, company information.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from src.agents.l3_base_agent import L3BaseAgent
from src.models.workflow_models import WorkflowState
from src.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class GeneralAgentL3(L3BaseAgent):
    """
    General domain specialist - handles general information and FAQs.
    
    Supported Actions:
    - provide_business_hours: Provide business hours information
    - provide_service_info: Provide information about services
    - provide_location_info: Provide location/coverage information
    - answer_faq: Answer frequently asked questions
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize General Agent L3.
        
        Args:
            db_service: Database service for data access
        """
        super().__init__(
            agent_name="general_agent_l3",
            domain="general",
            db_service=db_service
        )
        
        # Store common information (in production, load from database)
        self.business_hours = {
            "monday": "8:00 AM - 6:00 PM",
            "tuesday": "8:00 AM - 6:00 PM",
            "wednesday": "8:00 AM - 6:00 PM",
            "thursday": "8:00 AM - 6:00 PM",
            "friday": "8:00 AM - 6:00 PM",
            "saturday": "9:00 AM - 4:00 PM",
            "sunday": "Closed"
        }
        
        self.service_catalog = {
            "house cleaning": {
                "description": "Professional house cleaning services",
                "duration": "2-4 hours",
                "price_range": "$100-$300"
            },
            "lawn care": {
                "description": "Lawn mowing, trimming, and maintenance",
                "duration": "1-2 hours",
                "price_range": "$50-$150"
            },
            "window cleaning": {
                "description": "Interior and exterior window cleaning",
                "duration": "1-3 hours",
                "price_range": "$75-$200"
            }
        }
        
        logger.info("GeneralAgentL3 initialized")
    
    def get_supported_actions(self) -> List[str]:
        """
        Get list of actions this agent can perform.
        
        Returns:
            List of action names
        """
        return [
            "provide_business_hours",
            "provide_service_info",
            "provide_location_info",
            "answer_faq"
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
        # General actions typically don't require specific prerequisites
        # All can be executed with minimal information
        
        if action_name == "provide_service_info":
            # Optional: service_type for specific service info
            return True, None
        
        elif action_name in ["provide_business_hours", "provide_location_info", "answer_faq"]:
            return True, None
        
        else:
            return False, f"Unknown action: {action_name}"
    
    async def execute_action(
        self,
        action_name: str,
        state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Execute the general information action.
        
        Args:
            action_name: Name of action to execute
            state: Current workflow state with all required information
        
        Returns:
            Dictionary with action results
        """
        try:
            if action_name == "provide_business_hours":
                return await self._provide_business_hours(state)
            
            elif action_name == "provide_service_info":
                return await self._provide_service_info(state)
            
            elif action_name == "provide_location_info":
                return await self._provide_location_info(state)
            
            elif action_name == "answer_faq":
                return await self._answer_faq(state)
            
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
    
    async def _provide_business_hours(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Provide business hours information.
        
        Args:
            state: Workflow state
        
        Returns:
            Business hours result dictionary
        """
        entities = state.entities
        
        # Check if asking about a specific day
        specific_day = entities.get("day_of_week")
        
        if specific_day and specific_day.lower() in self.business_hours:
            hours = self.business_hours[specific_day.lower()]
            return {
                "success": True,
                "day": specific_day.capitalize(),
                "hours": hours,
                "is_open_today": specific_day.lower() != "sunday"
            }
        else:
            # Return all business hours
            return {
                "success": True,
                "business_hours": self.business_hours,
                "current_day": datetime.now(timezone.utc).strftime("%A").lower(),
                "is_open_now": self._is_currently_open()
            }
    
    async def _provide_service_info(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Provide information about services.
        
        Args:
            state: Workflow state
        
        Returns:
            Service information result dictionary
        """
        entities = state.entities
        
        # Check if asking about a specific service
        service_type = entities.get("service_type")
        
        if service_type and service_type.lower() in self.service_catalog:
            service_info = self.service_catalog[service_type.lower()]
            return {
                "success": True,
                "service_type": service_type,
                "description": service_info["description"],
                "duration": service_info["duration"],
                "price_range": service_info["price_range"]
            }
        else:
            # Return all services
            return {
                "success": True,
                "services": self.service_catalog,
                "total_services": len(self.service_catalog)
            }
    
    async def _provide_location_info(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Provide location and coverage information.
        
        Args:
            state: Workflow state
        
        Returns:
            Location information result dictionary
        """
        # In production, load from database
        location_info = {
            "service_areas": [
                "Minneapolis",
                "St. Paul",
                "Bloomington",
                "Eden Prairie",
                "Minnetonka"
            ],
            "office_address": "123 Main Street, Minneapolis, MN 55401",
            "phone": "555-123-4567",
            "email": "info@example.com"
        }
        
        return {
            "success": True,
            **location_info
        }
    
    async def _answer_faq(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Answer frequently asked questions.
        
        Args:
            state: Workflow state
        
        Returns:
            FAQ answer result dictionary
        """
        entities = state.entities
        question = entities.get("question") or state.speech_text
        
        # Simple FAQ matching (in production, use semantic search or LLM)
        faqs = {
            "payment": {
                "question": "What payment methods do you accept?",
                "answer": "We accept credit cards, debit cards, checks, and cash. Payment is due upon completion of service."
            },
            "cancellation": {
                "question": "What is your cancellation policy?",
                "answer": "Cancellations made more than 24 hours in advance receive a full refund. Cancellations within 24 hours are subject to a 50% cancellation fee."
            },
            "guarantee": {
                "question": "Do you have a satisfaction guarantee?",
                "answer": "Yes! We offer a 100% satisfaction guarantee. If you're not completely satisfied, we'll come back and make it right at no additional charge."
            },
            "insurance": {
                "question": "Are you insured?",
                "answer": "Yes, we are fully insured and bonded. All of our technicians are background-checked and professionally trained."
            }
        }
        
        # Try to match question to FAQ (simple keyword matching)
        question_lower = question.lower() if question else ""
        matched_faq = None
        
        for key, faq in faqs.items():
            if key in question_lower:
                matched_faq = faq
                break
        
        if matched_faq:
            return {
                "success": True,
                "question": matched_faq["question"],
                "answer": matched_faq["answer"]
            }
        else:
            # Return general help message
            return {
                "success": True,
                "message": "I'd be happy to help! Here are some topics I can assist with:",
                "available_topics": list(faqs.keys())
            }
    
    # ============ Helper Methods ============
    
    def _is_currently_open(self) -> bool:
        """Check if business is currently open."""
        now = datetime.now(timezone.utc)
        day_name = now.strftime("%A").lower()
        
        if day_name == "sunday":
            return False
        
        # Simple check (in production, parse hours and compare times)
        current_hour = now.hour
        
        if day_name == "saturday":
            return 9 <= current_hour < 16
        else:
            return 8 <= current_hour < 18