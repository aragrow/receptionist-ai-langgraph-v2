# ============================== tests/test_l3_agent.py ==============================
"""
Unit tests for Level 3 Domain Specialist Agents
Tests action execution, confirmation generation, and error handling
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, UTC
from src.agents.l3_sales_agent import SalesAgentL3
from src.agents.l3_support_agent import SupportAgentL3
from src.agents.l3_billing_agent import BillingAgentL3
from src.models.agent_models import L3Output, IntentL2
from src.models.workflow_models import WorkflowState


@pytest.fixture
def mock_booking_service():
    """Mock booking service for testing"""
    with patch('src.actions.booking_actions.BookingService') as mock:
        yield mock


@pytest.fixture
def mock_support_service():
    """Mock support service for testing"""
    with patch('src.actions.support_actions.SupportService') as mock:
        yield mock


@pytest.fixture
def mock_billing_service():
    """Mock billing service for testing"""
    with patch('src.actions.billing_actions.BillingService') as mock:
        yield mock


@pytest.fixture
def sales_agent(mock_booking_service):
    """Create SalesAgentL3 instance"""
    return SalesAgentL3()


@pytest.fixture
def support_agent(mock_support_service):
    """Create SupportAgentL3 instance"""
    return SupportAgentL3()


@pytest.fixture
def billing_agent(mock_billing_service):
    """Create BillingAgentL3 instance"""
    return BillingAgentL3()


@pytest.fixture
def complete_booking_state():
    """Workflow state with complete booking information"""
    return WorkflowState(
        session_id="test-session-abc",
        user_id="user-123",
        caller_type="client",
        raw_prompt="Book cleaning at 123 Main St on Oct 10 at 2pm",
        current_tier="L3",
        intent_l2=IntentL2(name="book_home_cleaning", confidence=0.95),
        entities={
            "service_type": "house cleaning",
            "address": "123 Main St, Minneapolis, MN",
            "preferred_date": "2025-10-10T14:00:00-05:00",
            "contact_number": "(555) 123-4567",
            "recurrence": "one-time"
        },
        required_slots=[],
        messages=[]
    )


@pytest.fixture
def complete_support_state():
    """Workflow state with complete support request"""
    return WorkflowState(
        session_id="test-session-def",
        user_id="user-456",
        caller_type="client",
        raw_prompt="The cleaners didn't show up",
        current_tier="L3",
        intent_l2=IntentL2(name="report_missed_appointment", confidence=0.93),
        entities={
            "issue_type": "missed_appointment",
            "address": "456 Oak Ave",
            "incident_date": "2025-10-01",
            "booking_id": "BOOK-789"
        },
        required_slots=[],
        messages=[]
    )


class TestSalesAgentL3:
    """Test SalesAgentL3 booking actions"""
    
    @pytest.mark.asyncio
    async def test_create_booking_success(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test successful booking creation"""
        # Arrange
        mock_booking_service.return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-12345",
            "confirmation_code": "CONF-ABC123",
            "scheduled_time": "2025-10-10T14:00:00-05:00"
        }
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        assert isinstance(result, L3Output)
        assert result.success is True
        assert result.booking_id == "BOOK-12345"
        assert result.confirmation_message is not None
        assert "BOOK-12345" in result.confirmation_message
        assert result.next_steps is not None
    
    @pytest.mark.asyncio
    async def test_check_availability_before_booking(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test that availability is checked before booking"""
        # Arrange
        mock_booking_service.return_value.check_availability.return_value = True
        mock_booking_service.return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-12345"
        }
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        mock_booking_service.return_value.check_availability.assert_called_once()
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_booking_unavailable_slot(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test handling when requested slot is unavailable"""
        # Arrange
        mock_booking_service.return_value.check_availability.return_value = False
        mock_booking_service.return_value.get_alternative_slots.return_value = [
            "2025-10-10T15:00:00-05:00",
            "2025-10-11T14:00:00-05:00"
        ]
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        assert result.success is False
        assert "unavailable" in result.confirmation_message.lower()
        assert result.next_steps is not None
        assert "alternative" in result.next_steps.lower()
    
    @pytest.mark.asyncio
    async def test_send_confirmation_email(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test that confirmation email is sent"""
        # Arrange
        mock_booking_service.return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-12345"
        }
        mock_booking_service.return_value.send_confirmation.return_value = True
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        mock_booking_service.return_value.send_confirmation.assert_called_once()
        assert "confirmation" in result.confirmation_message.lower()
    
    @pytest.mark.asyncio
    async def test_calculate_pricing(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test that pricing is calculated correctly"""
        # Arrange
        mock_booking_service.return_value.calculate_price.return_value = {
            "base_price": 120.00,
            "tax": 10.80,
            "total": 130.80,
            "currency": "USD"
        }
        mock_booking_service.return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-12345",
            "total_price": 130.80
        }
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        assert result.success is True
        assert "$130.80" in result.confirmation_message or "130.80" in result.confirmation_message
    
    @pytest.mark.asyncio
    async def test_recurring_booking(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test creation of recurring booking"""
        # Arrange
        complete_booking_state.entities["recurrence"] = "weekly"
        complete_booking_state.entities["recurrence_end_date"] = "2025-12-31"
        
        mock_booking_service.return_value.create_recurring_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-REC-123",
            "occurrences": 12
        }
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        assert result.success is True
        assert "recurring" in result.confirmation_message.lower() or "weekly" in result.confirmation_message.lower()


class TestSupportAgentL3:
    """Test SupportAgentL3 issue handling"""
    
    @pytest.mark.asyncio
    async def test_create_support_ticket(self, support_agent, mock_support_service, complete_support_state):
        """Test successful support ticket creation"""
        # Arrange
        mock_support_service.return_value.create_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-98765",
            "priority": "high",
            "assigned_to": "support_team_lead"
        }
        
        # Act
        result = await support_agent.execute(complete_support_state)
        
        # Assert
        assert result.success is True
        assert result.ticket_id == "TICKET-98765"
        assert "TICKET-98765" in result.confirmation_message
        assert result.next_steps is not None
    
    @pytest.mark.asyncio
    async def test_escalate_urgent_issue(self, support_agent, mock_support_service, complete_support_state):
        """Test escalation of urgent issues"""
        # Arrange
        complete_support_state.entities["urgency"] = "urgent"
        complete_support_state.entities["issue_type"] = "emergency"
        
        mock_support_service.return_value.create_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-99999",
            "priority": "urgent",
            "escalated": True
        }
        
        # Act
        result = await support_agent.execute(complete_support_state)
        
        # Assert
        assert result.success is True
        assert "urgent" in result.confirmation_message.lower() or "priority" in result.confirmation_message.lower()
    
    @pytest.mark.asyncio
    async def test_update_job_status(self, support_agent, mock_support_service, complete_support_state):
        """Test updating job status"""
        # Arrange
        complete_support_state.intent_l2 = IntentL2(name="update_job_status", confidence=0.91)
        complete_support_state.entities["new_status"] = "in_progress"
        
        mock_support_service.return_value.update_job_status.return_value = {
            "success": True,
            "booking_id": "BOOK-789",
            "old_status": "scheduled",
            "new_status": "in_progress"
        }
        
        # Act
        result = await support_agent.execute(complete_support_state)
        
        # Assert
        assert result.success is True
        assert "updated" in result.confirmation_message.lower()
    
    @pytest.mark.asyncio
    async def test_issue_resolution(self, support_agent, mock_support_service, complete_support_state):
        """Test marking issue as resolved"""
        # Arrange
        complete_support_state.intent_l2 = IntentL2(name="resolve_issue", confidence=0.94)
        complete_support_state.entities["resolution"] = "Rescheduled for next day"
        
        mock_support_service.return_value.resolve_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-98765",
            "resolution_time": "2025-10-01T16:30:00"
        }
        
        # Act
        result = await support_agent.execute(complete_support_state)
        
        # Assert
        assert result.success is True
        assert "resolved" in result.confirmation_message.lower()


class TestBillingAgentL3:
    """Test BillingAgentL3 financial actions"""
    
    @pytest.mark.asyncio
    async def test_generate_invoice(self, billing_agent, mock_billing_service):
        """Test invoice generation"""
        # Arrange
        state = WorkflowState(
            session_id="test-billing-1",
            user_id="user-789",
            caller_type="client",
            raw_prompt="I need an invoice for my last service",
            current_tier="L3",
            intent_l2=IntentL2(name="request_invoice", confidence=0.92),
            entities={
                "booking_id": "BOOK-555"
            },
            required_slots=[],
            messages=[]
        )
        
        mock_billing_service.return_value.generate_invoice.return_value = {
            "success": True,
            "invoice_id": "INV-12345",
            "amount": 130.80,
            "due_date": "2025-10-15",
            "pdf_url": "https://example.com/invoices/INV-12345.pdf"
        }
        
        # Act
        result = await billing_agent.execute(state)
        
        # Assert
        assert result.success is True
        assert "INV-12345" in result.confirmation_message
        assert result.next_steps is not None
    
    @pytest.mark.asyncio
    async def test_process_payment(self, billing_agent, mock_billing_service):
        """Test payment processing"""
        # Arrange
        state = WorkflowState(
            session_id="test-billing-2",
            user_id="user-789",
            caller_type="client",
            raw_prompt="I want to pay my invoice",
            current_tier="L3",
            intent_l2=IntentL2(name="make_payment", confidence=0.94),
            entities={
                "invoice_id": "INV-12345",
                "payment_method": "credit_card",
                "amount": 130.80
            },
            required_slots=[],
            messages=[]
        )
        
        mock_billing_service.return_value.process_payment.return_value = {
            "success": True,
            "transaction_id": "TXN-98765",
            "amount": 130.80,
            "status": "completed"
        }
        
        # Act
        result = await billing_agent.execute(state)
        
        # Assert
        assert result.success is True
        assert "TXN-98765" in result.confirmation_message
        assert "completed" in result.confirmation_message.lower() or "successful" in result.confirmation_message.lower()
    
    @pytest.mark.asyncio
    async def test_payment_failure(self, billing_agent, mock_billing_service):
        """Test handling of payment failure"""
        # Arrange
        state = WorkflowState(
            session_id="test-billing-3",
            user_id="user-789",
            caller_type="client",
            current_tier="L3",
            intent_l2=IntentL2(name="make_payment", confidence=0.92),
            entities={"invoice_id": "INV-12345", "amount": 130.80},
            required_slots=[],
            messages=[]
        )
        
        mock_billing_service.return_value.process_payment.return_value = {
            "success": False,
            "error": "insufficient_funds",
            "error_message": "Payment declined - insufficient funds"
        }
        
        # Act
        result = await billing_agent.execute(state)
        
        # Assert
        assert result.success is False
        assert "declined" in result.confirmation_message.lower() or "failed" in result.confirmation_message.lower()
        assert result.next_steps is not None
    
    @pytest.mark.asyncio
    async def test_invoice_inquiry(self, billing_agent, mock_billing_service):
        """Test invoice inquiry/lookup"""
        # Arrange
        state = WorkflowState(
            session_id="test-billing-4",
            user_id="user-789",
            caller_type="client",
            current_tier="L3",
            intent_l2=IntentL2(name="invoice_inquiry", confidence=0.89),
            entities={"invoice_number": "12345"},
            required_slots=[],
            messages=[]
        )
        
        mock_billing_service.return_value.get_invoice.return_value = {
            "success": True,
            "invoice_id": "INV-12345",
            "amount": 130.80,
            "status": "paid",
            "paid_date": "2025-09-25"
        }
        
        # Act
        result = await billing_agent.execute(state)
        
        # Assert
        assert result.success is True
        assert "130.80" in result.confirmation_message or "$130.80" in result.confirmation_message
        assert "paid" in result.confirmation_message.lower()


class TestL3ErrorHandling:
    """Test error handling across L3 agents"""
    
    @pytest.mark.asyncio
    async def test_handle_service_unavailable(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test handling when backend service is unavailable"""
        # Arrange
        mock_booking_service.return_value.create_booking.side_effect = ConnectionError("Service unavailable")
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        assert result.success is False
        assert "error" in result.confirmation_message.lower() or "unavailable" in result.confirmation_message.lower()
        assert result.requires_human_escalation is True
    
    @pytest.mark.asyncio
    async def test_handle_invalid_data(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test handling of invalid input data"""
        # Arrange
        complete_booking_state.entities["preferred_date"] = "invalid-date"
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        assert result.success is False
        assert "invalid" in result.confirmation_message.lower() or "error" in result.confirmation_message.lower()
    
    @pytest.mark.asyncio
    async def test_handle_missing_required_entity(self, support_agent, mock_support_service, complete_support_state):
        """Test handling when required entity is missing"""
        # Arrange
        del complete_support_state.entities["issue_type"]
        
        # Act
        result = await support_agent.execute(complete_support_state)
        
        # Assert
        assert result.success is False
        assert result.requires_clarification is True


class TestL3ConfirmationMessages:
    """Test confirmation message generation"""
    
    @pytest.mark.asyncio
    async def test_booking_confirmation_format(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test booking confirmation message format"""
        # Arrange
        mock_booking_service.return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-12345",
            "scheduled_time": "2025-10-10T14:00:00-05:00",
            "address": "123 Main St"
        }
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        message = result.confirmation_message
        assert "BOOK-12345" in message
        assert "123 Main St" in message
        assert "October" in message or "10" in message
    
    @pytest.mark.asyncio
    async def test_ticket_confirmation_format(self, support_agent, mock_support_service, complete_support_state):
        """Test support ticket confirmation format"""
        # Arrange
        mock_support_service.return_value.create_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-98765",
            "priority": "high"
        }
        
        # Act
        result = await support_agent.execute(complete_support_state)
        
        # Assert
        message = result.confirmation_message
        assert "TICKET-98765" in message
        assert len(message) > 20  # Should be informative


class TestL3NextSteps:
    """Test next steps generation"""
    
    @pytest.mark.asyncio
    async def test_booking_next_steps(self, sales_agent, mock_booking_service, complete_booking_state):
        """Test next steps for successful booking"""
        # Arrange
        mock_booking_service.return_value.create_booking.return_value = {
            "success": True,
            "booking_id": "BOOK-12345"
        }
        
        # Act
        result = await sales_agent.execute(complete_booking_state)
        
        # Assert
        assert result.next_steps is not None
        assert len(result.next_steps) > 0
        # Should mention calendar invite or confirmation email
        assert any(word in result.next_steps.lower() for word in ["email", "calendar", "confirm", "reminder"])
    
    @pytest.mark.asyncio
    async def test_support_ticket_next_steps(self, support_agent, mock_support_service, complete_support_state):
        """Test next steps for support ticket"""
        # Arrange
        mock_support_service.return_value.create_ticket.return_value = {
            "success": True,
            "ticket_id": "TICKET-98765",
            "estimated_response_time": "2 hours"
        }
        
        # Act
        result = await support_agent.execute(complete_support_state)
        
        # Assert
        assert result.next_steps is not None
        # Should mention follow-up or response time
        assert any(word in result.next_steps.lower() for word in ["contact", "follow", "response", "hours"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])