# ============================== tests/test_integration.py ==============================
"""
End-to-end scenario tests for real-world use cases
Tests complete user journeys from start to finish
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC, timedelta
from src.workflow.ai_receptionist_workflow import AIReceptionistWorkflow


@pytest.fixture
def workflow_with_real_prompts():
    """Create workflow with realistic mock responses"""
    with patch('src.services.llm_service.LLMService') as mock_llm, \
         patch('src.actions.booking_actions.BookingService') as mock_booking, \
         patch('src.actions.support_actions.SupportService') as mock_support, \
         patch('src.actions.billing_actions.BillingService') as mock_billing:
        
        workflow = AIReceptionistWorkflow()
        yield workflow, {
            'llm': mock_llm,
            'booking': mock_booking,
            'support': mock_support,
            'billing': mock_billing
        }


class TestHappyPathScenarios:
    """Test ideal user journeys with no issues"""
    
    @pytest.mark.asyncio
    async def test_new_customer_books_first_cleaning(self, workflow_with_real_prompts):
        """
        Scenario: New prospect books their first cleaning service
        Expected: Smooth booking with pricing info and confirmation
        """
        workflow, mocks = workflow_with_real_prompts
        
        # Configure mocks for prospect flow
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1: Identify as prospect with sales intent
            {
                "intent": "sales",
                "confidence": 0.91,
                "caller_type": "prospect"
            },
            # L2: Extract booking details
            {
                "refined_intent": "request_quote_and_book",
                "confidence": 0.93,
                "entities": {
                    "service_type": "house cleaning",
                    "property_type": "3-bedroom house",
                    "address": "456 Elm Street, Minneapolis, MN 55401",
                    "preferred_date": "2025-10-12T10:00:00-05:00",
                    "contact_email": "newcustomer@email.com"
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        mocks['booking'].return_value.calculate_price.return_value = {
            "base_price": 150.00,
            "tax": 13.50,
            "total": 163.50
        }
        
        mocks['booking'].return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-FIRST-001",
            "confirmation_code": "CONF-WELCOME",
            "total_price": 163.50,
            "scheduled_time": "2025-10-12T10:00:00-05:00"
        }
        
        # Act
        result = await workflow.run(
            "Hi! I'm interested in getting my house cleaned. "
            "I have a 3-bedroom house at 456 Elm Street in Minneapolis. "
            "Can you come this Saturday around 10am?",
            user_id=None  # New prospect, no user_id
        )
        
        # Assert
        assert result.success is True
        assert result.booking_id == "BOOK-FIRST-001"
        assert "$163.50" in result.final_message or "163.50" in result.final_message
        assert "welcome" in result.final_message.lower() or "first" in result.final_message.lower()
        assert result.clarification_count == 0
    
    @pytest.mark.asyncio
    async def test_existing_client_reschedules_recurring_cleaning(self, workflow_with_real_prompts):
        """
        Scenario: Existing client reschedules their weekly cleaning
        Expected: Quick identification and modification
        """
        workflow, mocks = workflow_with_real_prompts
        
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1: Existing client, scheduling intent
            {
                "intent": "scheduling",
                "confidence": 0.94,
                "caller_type": "client"
            },
            # L2: Reschedule intent with booking reference
            {
                "refined_intent": "reschedule_booking",
                "confidence": 0.96,
                "entities": {
                    "booking_id": "BOOK-RECURRING-555",
                    "new_date": "2025-10-15T14:00:00-05:00",
                    "reason": "conflict"
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        mocks['booking'].return_value.reschedule_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-RECURRING-555",
            "old_date": "2025-10-10T14:00:00-05:00",
            "new_date": "2025-10-15T14:00:00-05:00"
        }
        
        # Act
        result = await workflow.run(
            "I need to reschedule my cleaning from Thursday to next Tuesday at 2pm. "
            "My booking number is 555.",
            user_id="existing-client-123"
        )
        
        # Assert
        assert result.success is True
        assert "October 15" in result.final_message or "rescheduled" in result.final_message.lower()
        assert result.clarification_count == 0
    
    @pytest.mark.asyncio
    async def test_client_pays_invoice_immediately(self, workflow_with_real_prompts):
        """
        Scenario: Client pays their invoice right away
        Expected: Quick payment processing and receipt
        """
        workflow, mocks = workflow_with_real_prompts
        
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1: Billing intent
            {
                "intent": "billing",
                "confidence": 0.92,
                "caller_type": "client"
            },
            # L2: Payment intent
            {
                "refined_intent": "make_payment",
                "confidence": 0.94,
                "entities": {
                    "invoice_number": "67890",
                    "payment_method": "credit_card"
                },
                "required_slots": [],
                "suggested_l3_agent": "BillingAgentL3"
            }
        ]
        
        mocks['billing'].return_value.get_invoice.return_value = {
            "invoice_id": "INV-67890",
            "amount": 175.00,
            "status": "unpaid"
        }
        
        mocks['billing'].return_value.process_payment.return_value = {
            "success": True,
            "transaction_id": "TXN-PAID-123",
            "amount": 175.00,
            "status": "completed",
            "receipt_url": "https://example.com/receipts/TXN-PAID-123"
        }
        
        # Act
        result = await workflow.run(
            "I'd like to pay invoice 67890 with my credit card",
            user_id="client-456"
        )
        
        # Assert
        assert result.success is True
        assert "TXN-PAID-123" in result.final_message
        assert "175.00" in result.final_message or "$175" in result.final_message
        assert "receipt" in result.final_message.lower()


class TestMissingSlotsScenarios:
    """Test scenarios where users provide incomplete information"""
    
    @pytest.mark.asyncio
    async def test_booking_with_gradual_info_collection(self, workflow_with_real_prompts):
        """
        Scenario: User books but provides info piece by piece
        Expected: System asks clarifying questions until complete
        """
        workflow, mocks = workflow_with_real_prompts
        
        # Turn 1: Vague initial request
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1
            {"intent": "scheduling", "confidence": 0.88, "caller_type": "client"},
            # L2 - missing address and date
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.85,
                "entities": {"service_type": "house cleaning"},
                "required_slots": ["address", "preferred_date"],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        result1 = await workflow.run("I want a house cleaning", user_id="user-789")
        
        assert result1.requires_clarification is True
        assert any(word in result1.clarification_question.lower() 
                  for word in ["address", "where", "location"])
        
        # Turn 2: Provide address
        mocks['llm'].return_value.generate_json.side_effect = [
            # L2 - now has address, still needs date
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.89,
                "entities": {
                    "service_type": "house cleaning",
                    "address": "123 Oak Lane"
                },
                "required_slots": ["preferred_date"],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        result2 = await workflow.continue_conversation(result1.session_id, "123 Oak Lane")
        
        assert result2.requires_clarification is True
        assert any(word in result2.clarification_question.lower() 
                  for word in ["date", "when", "time"])
        
        # Turn 3: Provide date - now complete
        mocks['llm'].return_value.generate_json.side_effect = [
            # L2 - all slots filled
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.93,
                "entities": {
                    "service_type": "house cleaning",
                    "address": "123 Oak Lane",
                    "preferred_date": "2025-10-18T09:00:00-05:00"
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        mocks['booking'].return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-GRADUAL-789"
        }
        
        result3 = await workflow.continue_conversation(
            result2.session_id, 
            "Next Friday at 9am"
        )
        
        # Assert
        assert result3.success is True
        assert result3.clarification_count == 2
        assert result3.booking_id == "BOOK-GRADUAL-789"
    
    @pytest.mark.asyncio
    async def test_support_ticket_needs_clarification(self, workflow_with_real_prompts):
        """
        Scenario: User reports issue but unclear what happened
        Expected: Agent asks for details before creating ticket
        """
        workflow, mocks = workflow_with_real_prompts
        
        # Turn 1: Vague complaint
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1
            {"intent": "support", "confidence": 0.86, "caller_type": "client"},
            # L2 - needs more details
            {
                "refined_intent": "report_issue",
                "confidence": 0.75,
                "entities": {"sentiment": "unhappy"},
                "required_slots": ["issue_type", "booking_id"],
                "suggested_l3_agent": "SupportAgentL3"
            }
        ]
        
        result1 = await workflow.run("I'm not happy with the service", user_id="user-complaint")
        
        assert result1.requires_clarification is True
        assert "what happened" in result1.clarification_question.lower() or \
               "issue" in result1.clarification_question.lower()
        
        # Turn 2: Provide details
        mocks['llm'].return_value.generate_json.side_effect = [
            # L2 - now has details
            {
                "refined_intent": "report_quality_issue",
                "confidence": 0.91,
                "entities": {
                    "issue_type": "quality_concern",
                    "booking_id": "BOOK-888",
                    "details": "Kitchen not cleaned properly"
                },
                "required_slots": [],
                "suggested_l3_agent": "SupportAgentL3"
            }
        ]
        
        mocks['support'].return_value.create_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-QUALITY-101",
            "priority": "medium"
        }
        
        result2 = await workflow.continue_conversation(
            result1.session_id,
            "The kitchen wasn't cleaned properly on booking 888"
        )
        
        assert result2.success is True
        assert result2.ticket_id == "TICKET-QUALITY-101"


class TestAmbiguousCallerScenarios:
    """Test scenarios with unknown or ambiguous caller types"""
    
    @pytest.mark.asyncio
    async def test_unknown_caller_gets_identified(self, workflow_with_real_prompts):
        """
        Scenario: Unknown caller needs to be identified
        Expected: System asks if existing client or new prospect
        """
        workflow, mocks = workflow_with_real_prompts
        
        # Turn 1: Ambiguous caller
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1 - unknown caller
            {
                "intent": "scheduling",
                "confidence": 0.65,
                "caller_type": "unknown"
            }
        ]
        
        result1 = await workflow.run("I need a cleaning", user_id=None)
        
        # Should ask for clarification about caller type
        assert result1.requires_clarification is True
        assert any(word in result1.clarification_question.lower() 
                  for word in ["existing", "new", "client", "customer"])
        
        # Turn 2: Identify as existing client
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1 after clarification
            {
                "intent": "scheduling",
                "confidence": 0.88,
                "caller_type": "client"
            },
            # L2 - proceed with booking
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.90,
                "entities": {"service_type": "cleaning"},
                "required_slots": ["address", "preferred_date"],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        result2 = await workflow.continue_conversation(
            result1.session_id,
            "Yes, I'm an existing customer"
        )
        
        assert result2.caller_type == "client"
        assert result2.current_tier in ["L2", "L3"]


class TestConflictingIntentsScenarios:
    """Test scenarios where user asks for multiple things"""
    
    @pytest.mark.asyncio
    async def test_user_asks_two_questions(self, workflow_with_real_prompts):
        """
        Scenario: User asks about two different things
        Expected: System handles primary intent first, offers to help with second
        """
        workflow, mocks = workflow_with_real_prompts
        
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1 - detects multiple intents
            {
                "intent": "scheduling",  # Primary
                "confidence": 0.80,
                "caller_type": "client",
                "secondary_intent": "billing"
            },
            # L2 - focus on primary
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.85,
                "entities": {
                    "address": "789 Main St",
                    "preferred_date": "2025-10-20T10:00:00-05:00"
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        mocks['booking'].return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-MULTI-111"
        }
        
        result = await workflow.run(
            "I want to book a cleaning for 789 Main St on October 20th at 10am, "
            "and also I have a question about my last invoice",
            user_id="user-multi"
        )
        
        # Should complete booking and mention billing question
        assert result.success is True
        assert result.booking_id == "BOOK-MULTI-111"
        # Should offer to help with billing in next_steps
        assert "invoice" in result.next_steps.lower() or "billing" in result.next_steps.lower()


class TestUrgentSituationScenarios:
    """Test scenarios requiring immediate attention"""
    
    @pytest.mark.asyncio
    async def test_emergency_escalation(self, workflow_with_real_prompts):
        """
        Scenario: Customer reports emergency situation
        Expected: Immediate escalation with high priority
        """
        workflow, mocks = workflow_with_real_prompts
        
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1 - detect emergency
            {
                "intent": "support",
                "confidence": 0.97,
                "caller_type": "client"
            },
            # L2 - emergency handling
            {
                "refined_intent": "report_emergency",
                "confidence": 0.98,
                "entities": {
                    "issue_type": "emergency",
                    "urgency": "critical",
                    "details": "chemical spill"
                },
                "required_slots": [],
                "suggested_l3_agent": "SupportAgentL3"
            }
        ]
        
        mocks['support'].return_value.create_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-EMERGENCY-999",
            "priority": "critical",
            "escalated": True,
            "response_time": "immediate"
        }
        
        result = await workflow.run(
            "URGENT: One of your cleaning products spilled and created harmful fumes!",
            user_id="user-emergency"
        )
        
        assert result.success is True
        assert result.escalated is True
        assert "TICKET-EMERGENCY-999" in result.final_message
        assert result.clarification_count == 0  # No time for clarifications
    
    @pytest.mark.asyncio
    async def test_angry_customer_gets_priority(self, workflow_with_real_prompts):
        """
        Scenario: Very upset customer needs immediate attention
        Expected: High priority ticket with human assignment
        """
        workflow, mocks = workflow_with_real_prompts
        
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1
            {"intent": "support", "confidence": 0.94, "caller_type": "client"},
            # L2
            {
                "refined_intent": "report_complaint",
                "confidence": 0.95,
                "entities": {
                    "issue_type": "service_failure",
                    "sentiment": "very_angry",
                    "booking_id": "BOOK-777"
                },
                "required_slots": [],
                "suggested_l3_agent": "SupportAgentL3"
            }
        ]
        
        mocks['support'].return_value.create_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-ANGRY-555",
            "priority": "high",
            "assigned_to": "senior_support_manager"
        }
        
        result = await workflow.run(
            "This is absolutely unacceptable! Your team completely ruined my carpet "
            "and I want this fixed NOW! Booking 777!",
            user_id="user-angry"
        )
        
        assert result.success is True
        assert result.ticket_id == "TICKET-ANGRY-555"
        # Should acknowledge urgency
        assert any(word in result.final_message.lower() 
                  for word in ["priority", "immediately", "manager"])


class TestEdgeCaseScenarios:
    """Test unusual or edge case scenarios"""
    
    @pytest.mark.asyncio
    async def test_user_changes_mind_mid_conversation(self, workflow_with_real_prompts):
        """
        Scenario: User starts booking then switches to cancellation
        Expected: System adapts to new intent
        """
        workflow, mocks = workflow_with_real_prompts
        
        # Turn 1: Start booking
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1
            {"intent": "scheduling", "confidence": 0.88, "caller_type": "client"},
            # L2
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.85,
                "entities": {},
                "required_slots": ["address", "preferred_date"],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        result1 = await workflow.run("I want to book a cleaning", user_id="user-mind-change")
        
        # Turn 2: Change mind to cancellation
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1 - detect intent change
            {"intent": "scheduling", "confidence": 0.90, "caller_type": "client"},
            # L2 - new intent
            {
                "refined_intent": "cancel_booking",
                "confidence": 0.92,
                "entities": {"booking_id": "BOOK-999"},
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        mocks['booking'].return_value.cancel_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-999",
            "refund_amount": 100.00
        }
        
        result2 = await workflow.continue_conversation(
            result1.session_id,
            "Actually, I need to cancel booking 999 instead"
        )
        
        assert result2.success is True
        assert "cancel" in result2.final_message.lower()
    
    @pytest.mark.asyncio
    async def test_user_provides_invalid_date(self, workflow_with_real_prompts):
        """
        Scenario: User provides date in the past
        Expected: System validates and asks for valid date
        """
        workflow, mocks = workflow_with_real_prompts
        
        past_date = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1
            {"intent": "scheduling", "confidence": 0.89, "caller_type": "client"},
            # L2 - detects past date
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.87,
                "entities": {
                    "address": "555 Test St",
                    "preferred_date": past_date
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3",
                "validation_error": "date_in_past"
            }
        ]
        
        result = await workflow.run(
            f"Book cleaning at 555 Test St for last Monday",
            user_id="user-invalid-date"
        )
        
        # Should detect validation error and ask for clarification
        assert result.requires_clarification is True
        assert "date" in result.clarification_question.lower()
        assert "past" in result.clarification_question.lower() or \
               "future" in result.clarification_question.lower()
    
    @pytest.mark.asyncio
    async def test_partner_vendor_check_in(self, workflow_with_real_prompts):
        """
        Scenario: Vendor/partner calls to check schedule
        Expected: Routes to partner agent, provides schedule info
        """
        workflow, mocks = workflow_with_real_prompts
        
        mocks['llm'].return_value.generate_json.side_effect = [
            # L1 - detect partner
            {
                "intent": "general",
                "confidence": 0.83,
                "caller_type": "partner"
            },
            # L2 - partner intent
            {
                "refined_intent": "check_schedule",
                "confidence": 0.89,
                "entities": {
                    "partner_name": "ABC Cleaning Supplies",
                    "inquiry_type": "delivery_schedule"
                },
                "required_slots": [],
                "suggested_l3_agent": "PartnerAgentL3"
            }
        ]
        
        result = await workflow.run(
            "Hi, this is ABC Cleaning Supplies. What's your schedule for deliveries this week?",
            user_id="partner-abc"
        )
        
        assert result.caller_type == "partner"
        assert result.success is True


class TestComplexMultiTurnScenarios:
    """Test complex multi-turn conversations"""
    
    @pytest.mark.asyncio
    async def test_booking_with_modifications_and_questions(self, workflow_with_real_prompts):
        """
        Scenario: User books, asks questions, modifies, then confirms
        Expected: System handles complex back-and-forth gracefully
        """
        workflow, mocks = workflow_with_real_prompts
        
        # Turn 1: Initial booking request
        mocks['llm'].return_value.generate_json.side_effect = [
            {"intent": "scheduling", "confidence": 0.87, "caller_type": "prospect"},
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.84,
                "entities": {"service_type": "house cleaning"},
                "required_slots": ["address", "preferred_date", "property_size"],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        result1 = await workflow.run("I want to book a house cleaning")
        assert result1.requires_clarification is True
        
        # Turn 2: Provide partial info
        mocks['llm'].return_value.generate_json.side_effect = [
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.86,
                "entities": {
                    "service_type": "house cleaning",
                    "address": "321 Birch Ave"
                },
                "required_slots": ["preferred_date", "property_size"],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        result2 = await workflow.continue_conversation(result1.session_id, "321 Birch Ave")
        assert result2.requires_clarification is True
        
        # Turn 3: Ask about pricing before completing
        mocks['llm'].return_value.generate_json.side_effect = [
            {
                "refined_intent": "inquire_pricing",
                "confidence": 0.90,
                "entities": {"property_size": "2000 sq ft"},
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        mocks['booking'].return_value.calculate_price.return_value = {
            "base_price": 180.00,
            "tax": 16.20,
            "total": 196.20
        }
        
        result3 = await workflow.continue_conversation(
            result2.session_id,
            "Actually, how much would it cost for a 2000 sq ft house?"
        )
        
        assert "196.20" in result3.final_message or "$196" in result3.final_message
        
        # Turn 4: Proceed with booking
        mocks['llm'].return_value.generate_json.side_effect = [
            {
                "refined_intent": "book_home_cleaning",
                "confidence": 0.94,
                "entities": {
                    "service_type": "house cleaning",
                    "address": "321 Birch Ave",
                    "property_size": "2000 sq ft",
                    "preferred_date": "2025-10-25T13:00:00-05:00"
                },
                "required_slots": [],
                "suggested_l3_agent": "SalesAgentL3"
            }
        ]
        
        mocks['booking'].return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-COMPLEX-999",
            "total_price": 196.20
        }
        
        result4 = await workflow.continue_conversation(
            result3.session_id,
            "Okay, let's book it for October 25th at 1pm"
        )
        
        assert result4.success is True
        assert result4.booking_id == "BOOK-COMPLEX-999"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])