# ============================== tests/test_integration.py ==============================
"""
Integration tests for complete L1->L2->L3 routing flows
Tests full end-to-end workflows with all tiers
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, UTC
from src.workflow.ai_receptionist_workflow import AIReceptionistWorkflow
from src.services.routing_service import RoutingService
from src.models.workflow_models import WorkflowState


@pytest.fixture
def mock_all_services():
    """Mock all external services"""
    with patch('src.services.llm_service.LLMService') as mock_llm, \
         patch('src.services.database_service.DatabaseService') as mock_db, \
         patch('src.actions.booking_actions.BookingService') as mock_booking, \
         patch('src.actions.support_actions.SupportService') as mock_support, \
         patch('src.actions.billing_actions.BillingService') as mock_billing:
        
        yield {
            'llm': mock_llm,
            'db': mock_db,
            'booking': mock_booking,
            'support': mock_support,
            'billing': mock_billing
        }


@pytest.fixture
def workflow(mock_all_services):
    """Create workflow instance with mocked services"""
    return AIReceptionistWorkflow()


@pytest.fixture
def routing_service():
    """Create routing service instance"""
    return RoutingService()


class TestCompleteBookingFlow:
    """Test complete booking flow from L1 to L3"""
    
    @pytest.mark.asyncio
    async def test_booking_with_complete_info(self, workflow, mock_all_services):
        """Test booking when user provides all information upfront"""
        # Arrange - User provides complete booking info
        initial_prompt = "I want to book a house cleaning at 123 Main St, Minneapolis on October 10th at 2pm"
        
        # Mock L1 response
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1 classification
            {
                "intent": "scheduling",
                "confidence": 0.94,
                "caller_type": "client"
            },
            # L2 slot extraction
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.96,
                "entities": {
                    "service_type": "house cleaning",
                    "address": "123 Main St, Minneapolis",
                    "preferred_date": "2025-10-10T14:00:00-05:00",
                    "recurrence": "one-time"
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        # Mock L3 booking action
        mock_all_services['booking'].return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-12345",
            "confirmation_code": "CONF-ABC"
        }
        
        # Act
        result = await workflow.run(initial_prompt, user_id="user-123")
        
        # Assert
        assert result.success is True
        assert result.booking_id == "BOOK-12345"
        assert result.current_tier == "L3"
        assert "BOOK-12345" in result.final_message
        # Should route directly L1->L2->L3 without clarifications
        assert result.clarification_count == 0
    
    @pytest.mark.asyncio
    async def test_booking_with_missing_slots(self, workflow, mock_all_services):
        """Test booking when user provides incomplete information"""
        # Arrange - User provides partial info
        initial_prompt = "I need a house cleaning"
        
        # Mock L1 response
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1 classification
            {
                "intent": "scheduling",
                "confidence": 0.90,
                "caller_type": "client"
            },
            # L2 slot extraction - missing slots
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.88,
                "entities": {
                    "service_type": "house cleaning"
                },
                "required_slots": ["address", "preferred_date"],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        # Act
        result = await workflow.run(initial_prompt, user_id="user-123")
        
        # Assert
        assert result.current_tier == "L2"  # Stuck at L2 for clarification
        assert result.requires_clarification is True
        assert result.clarification_question is not None
        assert any(slot in result.clarification_question.lower() for slot in ["address", "date"])
    
    @pytest.mark.asyncio
    async def test_booking_clarification_loop(self, workflow, mock_all_services):
        """Test booking with clarification loop"""
        # Arrange - Initial request
        initial_prompt = "I need a cleaning"
        
        # Mock responses for multi-turn conversation
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1 classification
            {"intent": "scheduling", "confidence": 0.89, "caller_type": "client"},
            # L2 first pass - missing slots
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.87,
                "entities": {"service_type": "house cleaning"},
                "required_slots": ["address", "preferred_date"],
                "suggested_l3_agent": "SalesAgentL3"
            },
            # L2 after clarification - still missing date
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.90,
                "entities": {
                    "service_type": "house cleaning",
                    "address": "456 Oak Ave"
                },
                "required_slots": ["preferred_date"],
                "suggested_l3_agent": "SalesAgentL3"
            },
            # L2 after second clarification - complete
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.93,
                "entities": {
                    "service_type": "house cleaning",
                    "address": "456 Oak Ave",
                    "preferred_date": "2025-10-15T10:00:00-05:00"
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        mock_all_services['booking'].return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-67890"
        }
        
        # Act - Simulate multi-turn conversation
        # Turn 1: Initial request
        result1 = await workflow.run(initial_prompt, user_id="user-123")
        assert result1.requires_clarification is True
        
        # Turn 2: Provide address
        result2 = await workflow.continue_conversation(
            result1.session_id,
            "456 Oak Ave"
        )
        assert result2.requires_clarification is True  # Still needs date
        
        # Turn 3: Provide date
        result3 = await workflow.continue_conversation(
            result2.session_id,
            "October 15th at 10am"
        )
        
        # Assert final result
        assert result3.success is True
        assert result3.booking_id == "BOOK-67890"
        assert result3.clarification_count == 2


class TestCompleteSupportFlow:
    """Test complete support flow from L1 to L3"""
    
    @pytest.mark.asyncio
    async def test_support_ticket_creation(self, workflow, mock_all_services):
        """Test creating support ticket for complaint"""
        # Arrange
        initial_prompt = "The cleaners didn't show up today at 789 Elm Street and I'm very upset"
        
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1 classification
            {
                "intent": "support",
                "confidence": 0.93,
                "caller_type": "client"
            },
            # L2 slot extraction
            {
                "refined_intent": "report_missed_appointment",
                "confidence": 0.95,
                "entities": {
                    "issue_type": "missed_appointment",
                    "address": "789 Elm Street",
                    "incident_date": "2025-10-01",
                    "sentiment": "upset"
                },
                "required_slots": [],
                "suggested_l3_agent": "SupportAgentL3"
            }
        ]
        
        # Mock support ticket creation
        mock_all_services['support'].return_value.create_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-55555",
            "priority": "high",
            "assigned_to": "support_team"
        }
        
        # Act
        result = await workflow.run(initial_prompt, user_id="user-456")
        
        # Assert
        assert result.success is True
        assert result.ticket_id == "TICKET-55555"
        assert "TICKET-55555" in result.final_message
        # Urgent sentiment should be reflected
        assert result.clarification_count == 0
    
    @pytest.mark.asyncio
    async def test_support_escalation(self, workflow, mock_all_services):
        """Test automatic escalation for urgent issues"""
        # Arrange
        initial_prompt = "EMERGENCY: There's a fire hazard from your cleaning chemicals!"
        
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1 classification
            {
                "intent": "support",
                "confidence": 0.96,
                "caller_type": "client"
            },
            # L2 slot extraction
            {
                "refined_intent": "report_emergency",
                "confidence": 0.98,
                "entities": {
                    "issue_type": "emergency",
                    "urgency": "critical"
                },
                "required_slots": [],
                "suggested_l3_agent": "SupportAgentL3"
            }
        ]
        
        mock_all_services['support'].return_value.create_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-URGENT-999",
            "priority": "critical",
            "escalated": True
        }
        
        # Act
        result = await workflow.run(initial_prompt, user_id="user-789")
        
        # Assert
        assert result.success is True
        assert result.ticket_id == "TICKET-URGENT-999"
        assert result.escalated is True


class TestCompleteBillingFlow:
    """Test complete billing flow from L1 to L3"""
    
    @pytest.mark.asyncio
    async def test_invoice_request(self, workflow, mock_all_services):
        """Test invoice request flow"""
        # Arrange
        initial_prompt = "I need a copy of invoice 12345"
        
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1 classification
            {
                "intent": "billing",
                "confidence": 0.91,
                "caller_type": "client"
            },
            # L2 slot extraction
            {
                "refined_intent": "request_invoice",
                "confidence": 0.93,
                "entities": {
                    "invoice_number": "12345"
                },
                "required_slots": [],
                "suggested_l3_agent": "BillingAgentL3"
            }
        ]
        
        mock_all_services['billing'].return_value.get_invoice.return_value = {
            "success": True,
            "invoice_id": "INV-12345",
            "amount": 150.00,
            "status": "paid",
            "pdf_url": "https://example.com/inv-12345.pdf"
        }
        
        # Act
        result = await workflow.run(initial_prompt, user_id="user-321")
        
        # Assert
        assert result.success is True
        assert "INV-12345" in result.final_message
        assert "150.00" in result.final_message or "$150" in result.final_message
    
    @pytest.mark.asyncio
    async def test_payment_processing(self, workflow, mock_all_services):
        """Test payment processing flow"""
        # Arrange
        initial_prompt = "I want to pay my invoice"
        
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1 classification
            {"intent": "billing", "confidence": 0.89, "caller_type": "client"},
            # L2 slot extraction - missing invoice ID
            {
                "refined_intent": "make_payment",
                "confidence": 0.88,
                "entities": {},
                "required_slots": ["invoice_id"],
                "suggested_l3_agent": "BillingAgentL3"
            },
            # L2 after clarification - complete
            {
                "refined_intent": "make_payment",
                "confidence": 0.92,
                "entities": {
                    "invoice_id": "INV-54321",
                    "amount": 200.00
                },
                "required_slots": [],
                "suggested_l3_agent": "BillingAgentL3"
            }
        ]
        
        mock_all_services['billing'].return_value.process_payment.return_value = {
            "success": True,
            "transaction_id": "TXN-99999",
            "amount": 200.00,
            "status": "completed"
        }
        
        # Act - Multi-turn
        result1 = await workflow.run(initial_prompt, user_id="user-654")
        assert result1.requires_clarification is True
        
        result2 = await workflow.continue_conversation(
            result1.session_id,
            "Invoice 54321"
        )
        
        # Assert
        assert result2.success is True
        assert "TXN-99999" in result2.final_message


class TestRoutingLogic:
    """Test routing decision logic"""
    
    @pytest.mark.asyncio
    async def test_l1_to_correct_l2_agent(self, routing_service):
        """Test L1 routes to correct L2 agent based on caller type"""
        # Test client routing
        state_client = WorkflowState(
            session_id="test-1",
            caller_type="client",
            intent_l1={"name": "scheduling", "confidence": 0.90},
            current_tier="L1",
            messages=[]
        )
        next_agent = routing_service.route_from_l1(state_client)
        assert next_agent == "ClientReceptionistL2"
        
        # Test prospect routing
        state_prospect = WorkflowState(
            session_id="test-2",
            caller_type="prospect",
            intent_l1={"name": "sales", "confidence": 0.88},
            current_tier="L1",
            messages=[]
        )
        next_agent = routing_service.route_from_l1(state_prospect)
        assert next_agent == "ProspectReceptionistL2"
        
        # Test partner routing
        state_partner = WorkflowState(
            session_id="test-3",
            caller_type="partner",
            intent_l1={"name": "general", "confidence": 0.85},
            current_tier="L1",
            messages=[]
        )
        next_agent = routing_service.route_from_l1(state_partner)
        assert next_agent == "PartnerReceptionistL2"
    
    @pytest.mark.asyncio
    async def test_l2_to_correct_l3_agent(self, routing_service):
        """Test L2 routes to correct L3 agent based on intent"""
        # Test booking intent
        state_booking = WorkflowState(
            session_id="test-4",
            intent_l2={"name": "book_home_cleaning", "confidence": 0.95},
            current_tier="L2",
            messages=[]
        )
        next_agent = routing_service.route_from_l2(state_booking)
        assert next_agent == "SalesAgentL3"
        
        # Test support intent
        state_support = WorkflowState(
            session_id="test-5",
            intent_l2={"name": "report_issue", "confidence": 0.92},
            current_tier="L2",
            messages=[]
        )
        next_agent = routing_service.route_from_l2(state_support)
        assert next_agent == "SupportAgentL3"
        
        # Test billing intent
        state_billing = WorkflowState(
            session_id="test-6",
            intent_l2={"name": "invoice_inquiry", "confidence": 0.90},
            current_tier="L2",
            messages=[]
        )
        next_agent = routing_service.route_from_l2(state_billing)
        assert next_agent == "BillingAgentL3"


class TestClarificationHandling:
    """Test clarification logic across tiers"""
    
    @pytest.mark.asyncio
    async def test_max_clarifications_exceeded(self, workflow, mock_all_services):
        """Test escalation after max clarifications"""
        # Arrange - Simulate user giving unclear responses
        initial_prompt = "I need help"
        
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1 - low confidence
            {"intent": "general", "confidence": 0.55, "caller_type": "unknown"},
            # After clarification 1
            {"intent": "support", "confidence": 0.60, "caller_type": "client"},
            # L2 - still unclear
            {
                "refined_intent": "unknown",
                "confidence": 0.50,
                "entities": {},
                "required_slots": ["issue_type"],
                "suggested_l3_agent": "GeneralAgentL3"
            },
            # After clarification 2
            {
                "refined_intent": "general_inquiry",
                "confidence": 0.55,
                "entities": {},
                "required_slots": ["topic"],
                "suggested_l3_agent": "GeneralAgentL3"
            }
        ]
        
        # Act
        result1 = await workflow.run(initial_prompt)
        result2 = await workflow.continue_conversation(result1.session_id, "something")
        result3 = await workflow.continue_conversation(result2.session_id, "I don't know")
        
        # Assert - Should escalate after 2 clarifications
        assert result3.clarification_count >= 2
        assert result3.requires_human_escalation is True
    
    @pytest.mark.asyncio
    async def test_successful_clarification_resolution(self, workflow, mock_all_services):
        """Test successful resolution after clarification"""
        # Arrange
        initial_prompt = "I need to change my appointment"
        
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1
            {"intent": "scheduling", "confidence": 0.87, "caller_type": "client"},
            # L2 - needs clarification
            {
                "refined_intent": "modify_booking",
                "confidence": 0.85,
                "entities": {},
                "required_slots": ["booking_id", "change_type"],
                "suggested_l3_agent": "SalesAgentL3"
            },
            # L2 after clarification - complete
            {
                "refined_intent": "reschedule_booking",
                "confidence": 0.92,
                "entities": {
                    "booking_id": "BOOK-111",
                    "new_date": "2025-10-20T14:00:00-05:00"
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        mock_all_services['booking'].return_value.reschedule_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-111",
            "new_date": "2025-10-20T14:00:00-05:00"
        }
        
        # Act
        result1 = await workflow.run(initial_prompt, user_id="user-999")
        result2 = await workflow.continue_conversation(
            result1.session_id,
            "Booking 111, reschedule to Oct 20 at 2pm"
        )
        
        # Assert
        assert result2.success is True
        assert result2.clarification_count == 1


class TestHumanEscalation:
    """Test human escalation scenarios"""
    
    @pytest.mark.asyncio
    async def test_low_confidence_escalation(self, workflow, mock_all_services):
        """Test escalation on very low confidence"""
        # Arrange
        initial_prompt = "asdfghjkl zxcvbnm"
        
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1 - very low confidence
            {
                "intent": "unknown",
                "confidence": 0.15,
                "caller_type": "unknown"
            }
        ]
        
        # Act
        result = await workflow.run(initial_prompt)
        
        # Assert
        assert result.requires_human_escalation is True
        assert result.ticket_id is not None
    
    @pytest.mark.asyncio
    async def test_explicit_agent_request_escalation(self, workflow, mock_all_services):
        """Test escalation when user explicitly asks for human"""
        # Arrange
        initial_prompt = "I want to speak to a real person"
        
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # L1
            {
                "intent": "request_human_agent",
                "confidence": 0.95,
                "caller_type": "unknown"
            }
        ]
        
        # Act
        result = await workflow.run(initial_prompt)
        
        # Assert
        assert result.requires_human_escalation is True
        assert "human" in result.final_message.lower() or "agent" in result.final_message.lower()


class TestMultiTurnConversations:
    """Test multi-turn conversation handling"""
    
    @pytest.mark.asyncio
    async def test_context_preservation(self, workflow, mock_all_services):
        """Test that context is preserved across turns"""
        # Arrange
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            # Turn 1: L1
            {"intent": "scheduling", "confidence": 0.88, "caller_type": "client"},
            # Turn 1: L2
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.90,
                "entities": {"service_type": "house cleaning"},
                "required_slots": ["address"],
                "suggested_l3_agent": "SalesAgentL3"
            },
            # Turn 2: L2 (should remember service_type)
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.92,
                "entities": {
                    "service_type": "house cleaning",  # Preserved
                    "address": "999 Pine St"
                },
                "required_slots": ["preferred_date"],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        # Act
        result1 = await workflow.run("I need a house cleaning", user_id="user-111")
        result2 = await workflow.continue_conversation(result1.session_id, "999 Pine St")
        
        # Assert
        assert "service_type" in result2.entities
        assert result2.entities["service_type"] == "house cleaning"
        assert result2.entities["address"] == "999 Pine St"
    
    @pytest.mark.asyncio
    async def test_conversation_history_tracking(self, workflow, mock_all_services):
        """Test that conversation history is properly tracked"""
        # Arrange
        mock_all_services['llm'].return_value.generate_json.side_effect = [
            {"intent": "general", "confidence": 0.80, "caller_type": "prospect"},
            {
                "refined_intent": "inquire_services",
                "confidence": 0.85,
                "entities": {},
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        # Act
        result1 = await workflow.run("Hello, what services do you offer?")
        result2 = await workflow.continue_conversation(result1.session_id, "Thanks for the info")
        
        # Assert
        assert len(result2.messages) >= 2
        assert result2.messages[0]["text"] == "Hello, what services do you offer?"
        assert result2.messages[1]["role"] in ["assistant", "agent"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])