# ============================== tests/test_l2_agent.py ==============================
"""
Unit tests for Receptionist L2 Agents
Tests slot extraction, clarification generation, and L3 routing
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, UTC
from src.agents.receptionist_l2_client import ClientReceptionistL2
from src.agents.receptionist_l2_prospect import ProspectReceptionistL2
from src.models.agent_models import L2Output, IntentL1
from src.models.workflow_models import WorkflowState


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing"""
    with patch('src.agents.receptionist_l2_base.llm_service') as mock:
        yield mock


@pytest.fixture
def mock_slot_filling_service():
    """Mock slot filling service for testing"""
    with patch('src.agents.receptionist_l2_base.slot_filling_service') as mock:
        yield mock


@pytest.fixture
def client_l2_agent(mock_llm_service, mock_slot_filling_service):
    """Create ClientReceptionistL2 instance"""
    return ClientReceptionistL2()


@pytest.fixture
def prospect_l2_agent(mock_llm_service, mock_slot_filling_service):
    """Create ProspectReceptionistL2 instance"""
    return ProspectReceptionistL2()


@pytest.fixture
def sample_client_state():
    """Sample workflow state for existing client"""
    return WorkflowState(
        session_id="test-session-456",
        user_id="user-789",
        caller_type="client",
        raw_prompt="I want to reschedule my cleaning",
        current_tier="L2",
        intent_l1=IntentL1(name="scheduling", confidence=0.92),
        messages=[],
        entities={},
        required_slots=[],
        clarification_count=0
    )


@pytest.fixture
def sample_prospect_state():
    """Sample workflow state for prospect"""
    return WorkflowState(
        session_id="test-session-789",
        user_id=None,
        caller_type="prospect",
        raw_prompt="How much does a house cleaning cost?",
        current_tier="L2",
        intent_l1=IntentL1(name="sales", confidence=0.88),
        messages=[],
        entities={},
        required_slots=[],
        clarification_count=0
    )


class TestClientL2SlotExtraction:
    """Test slot extraction for client requests"""
    
    @pytest.mark.asyncio
    async def test_extract_booking_slots_complete(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test extraction when all required slots are present"""
        # Arrange
        sample_client_state.raw_prompt = "I need to book a house cleaning for 123 Main St on October 10th at 2pm"
        
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",
            "confidence": 0.93,
            "entities": {"address": "123 Main", "preferred_date": "2025-10-10"},
            "required_slots": [],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert result.suggested_l3_agent == "SalesAgentL3"
    
    @pytest.mark.asyncio
    async def test_select_support_agent_for_issue(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test selection of SupportAgentL3 for issue"""
        # Arrange
        sample_client_state.intent_l1 = IntentL1(name="support", confidence=0.90)
        
        mock_llm_response = {
            "refined_intent": "report_issue",
            "confidence": 0.91,
            "entities": {"issue_type": "quality_concern"},
            "required_slots": [],
            "suggested_l3_agent": "SupportAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert result.suggested_l3_agent == "SupportAgentL3"
    
    @pytest.mark.asyncio
    async def test_select_billing_agent_for_invoice(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test selection of BillingAgentL3 for billing"""
        # Arrange
        sample_client_state.intent_l1 = IntentL1(name="billing", confidence=0.89)
        
        mock_llm_response = {
            "refined_intent": "invoice_inquiry",
            "confidence": 0.92,
            "entities": {"invoice_number": "12345"},
            "required_slots": [],
            "suggested_l3_agent": "BillingAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert result.suggested_l3_agent == "BillingAgentL3"


class TestL2ErrorHandling:
    """Test error handling in L2 agents"""
    
    @pytest.mark.asyncio
    async def test_handle_slot_extraction_failure(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test handling when slot extraction fails"""
        # Arrange
        mock_llm_service.generate_json.side_effect = Exception("Extraction error")
        
        # Act & Assert
        with pytest.raises(Exception):
            await client_l2_agent.process(sample_client_state)
    
    @pytest.mark.asyncio
    async def test_handle_invalid_entity_format(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test handling of invalid entity format"""
        # Arrange
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",
            "confidence": 0.90,
            "entities": "invalid_format",  # Should be dict
            "required_slots": [],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act & Assert
        with pytest.raises(ValueError):
            await client_l2_agent.process(sample_client_state)


class TestL2SlotValidation:
    """Test slot value validation"""
    
    @pytest.mark.asyncio
    async def test_validate_date_format(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test validation of date format"""
        # Arrange
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",
            "confidence": 0.93,
            "entities": {
                "preferred_date": "2025-10-10T14:00:00",
                "address": "123 Main St"
            },
            "required_slots": [],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert "preferred_date" in result.entities
        # Should be valid ISO format
        datetime.fromisoformat(result.entities["preferred_date"].replace('Z', '+00:00'))
    
    @pytest.mark.asyncio
    async def test_validate_address_present(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test that address is properly extracted"""
        # Arrange
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",
            "confidence": 0.91,
            "entities": {
                "address": "123 Main St, Minneapolis, MN"
            },
            "required_slots": ["preferred_date"],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert "address" in result.entities
        assert len(result.entities["address"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
            "confidence": 0.95,
            "entities": {
                "service_type": "house cleaning",
                "address": "123 Main St",
                "preferred_date": "2025-10-10T14:00:00",
                "recurrence": "one-time"
            },
            "required_slots": [],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert isinstance(result, L2Output)
        assert result.refined_intent == "book_home_cleaning"
        assert result.confidence >= 0.75
        assert len(result.required_slots) == 0
        assert result.suggested_l3_agent == "SalesAgentL3"
        assert "address" in result.entities
        assert "preferred_date" in result.entities
    
    @pytest.mark.asyncio
    async def test_extract_booking_slots_incomplete(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test extraction when required slots are missing"""
        # Arrange
        sample_client_state.raw_prompt = "I need to schedule a cleaning"
        
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",
            "confidence": 0.90,
            "entities": {
                "service_type": "house cleaning"
            },
            "required_slots": ["address", "preferred_date"],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert len(result.required_slots) > 0
        assert "address" in result.required_slots
        assert "preferred_date" in result.required_slots
        assert result.clarification_question is not None
    
    @pytest.mark.asyncio
    async def test_extract_support_slots(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test extraction for support request"""
        # Arrange
        sample_client_state.raw_prompt = "The cleaners didn't show up today at 123 Oak Ave"
        sample_client_state.intent_l1 = IntentL1(name="support", confidence=0.89)
        
        mock_llm_response = {
            "refined_intent": "report_missed_appointment",
            "confidence": 0.93,
            "entities": {
                "issue_type": "missed_appointment",
                "address": "123 Oak Ave",
                "incident_date": "2025-10-01"
            },
            "required_slots": [],
            "suggested_l3_agent": "SupportAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert result.refined_intent == "report_missed_appointment"
        assert result.suggested_l3_agent == "SupportAgentL3"
        assert "issue_type" in result.entities
    
    @pytest.mark.asyncio
    async def test_extract_billing_slots(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test extraction for billing inquiry"""
        # Arrange
        sample_client_state.raw_prompt = "I have a question about invoice #12345"
        sample_client_state.intent_l1 = IntentL1(name="billing", confidence=0.91)
        
        mock_llm_response = {
            "refined_intent": "invoice_inquiry",
            "confidence": 0.94,
            "entities": {
                "invoice_number": "12345",
                "inquiry_type": "question"
            },
            "required_slots": [],
            "suggested_l3_agent": "BillingAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert result.refined_intent == "invoice_inquiry"
        assert result.suggested_l3_agent == "BillingAgentL3"


class TestProspectL2Processing:
    """Test L2 processing for prospects"""
    
    @pytest.mark.asyncio
    async def test_process_pricing_inquiry(self, prospect_l2_agent, mock_llm_service, sample_prospect_state):
        """Test processing of pricing inquiry from prospect"""
        # Arrange
        mock_llm_response = {
            "refined_intent": "request_pricing",
            "confidence": 0.89,
            "entities": {
                "service_interest": "house cleaning",
                "property_type": "house"
            },
            "required_slots": ["property_size", "location"],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await prospect_l2_agent.process(sample_prospect_state)
        
        # Assert
        assert result.refined_intent == "request_pricing"
        assert "property_size" in result.required_slots
        assert result.clarification_question is not None
    
    @pytest.mark.asyncio
    async def test_process_service_inquiry(self, prospect_l2_agent, mock_llm_service, sample_prospect_state):
        """Test processing of general service inquiry"""
        # Arrange
        sample_prospect_state.raw_prompt = "What services do you offer?"
        
        mock_llm_response = {
            "refined_intent": "inquire_services",
            "confidence": 0.87,
            "entities": {},
            "required_slots": [],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await prospect_l2_agent.process(sample_prospect_state)
        
        # Assert
        assert result.refined_intent == "inquire_services"
        assert len(result.required_slots) == 0


class TestL2ClarificationGeneration:
    """Test clarification question generation"""
    
    @pytest.mark.asyncio
    async def test_generate_single_slot_clarification(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test clarification for single missing slot"""
        # Arrange
        sample_client_state.raw_prompt = "I need a cleaning on October 10th"
        
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",
            "confidence": 0.92,
            "entities": {
                "preferred_date": "2025-10-10"
            },
            "required_slots": ["address"],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert result.clarification_question is not None
        assert "address" in result.clarification_question.lower()
    
    @pytest.mark.asyncio
    async def test_generate_multiple_slot_clarification(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test clarification for multiple missing slots"""
        # Arrange
        sample_client_state.raw_prompt = "I need a cleaning"
        
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",
            "confidence": 0.88,
            "entities": {},
            "required_slots": ["address", "preferred_date", "property_size"],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert result.clarification_question is not None
        # Should ask about multiple slots in one question
        clarification = result.clarification_question.lower()
        assert any(slot in clarification for slot in ["address", "date", "size"])
    
    @pytest.mark.asyncio
    async def test_no_clarification_when_slots_complete(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test that no clarification is generated when all slots present"""
        # Arrange
        sample_client_state.raw_prompt = "Book cleaning at 123 Main St on Oct 10 at 2pm"
        
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",
            "confidence": 0.96,
            "entities": {
                "address": "123 Main St",
                "preferred_date": "2025-10-10T14:00:00"
            },
            "required_slots": [],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert result.clarification_question is None


class TestL2ConfidenceHandling:
    """Test confidence threshold handling at L2"""
    
    @pytest.mark.asyncio
    async def test_high_confidence_routes_to_l3(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test high confidence with complete slots routes to L3"""
        # Arrange
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",
            "confidence": 0.94,
            "entities": {"address": "123 Main", "preferred_date": "2025-10-10"},
            "required_slots": [],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert result.confidence >= 0.75
        assert len(result.required_slots) == 0
        assert result.suggested_l3_agent is not None
    
    @pytest.mark.asyncio
    async def test_medium_confidence_with_slots_clarifies(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test medium confidence requests clarification"""
        # Arrange
        mock_llm_response = {
            "refined_intent": "modify_booking",
            "confidence": 0.62,
            "entities": {},
            "required_slots": ["booking_id", "change_type"],
            "suggested_l3_agent": "SalesAgentL3"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await client_l2_agent.process(sample_client_state)
        
        # Assert
        assert 0.4 <= result.confidence < 0.75
        assert result.clarification_question is not None


class TestL2AgentSelection:
    """Test L3 agent selection logic"""
    
    @pytest.mark.asyncio
    async def test_select_sales_agent_for_booking(self, client_l2_agent, mock_llm_service, sample_client_state):
        """Test selection of SalesAgentL3 for booking"""
        # Arrange
        mock_llm_response = {
            "refined_intent": "book_home_cleaning",