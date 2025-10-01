# ============================== tests/test_l1_agent.py ==============================
"""
Unit tests for Receptionist L1 Agent
Tests classification accuracy, confidence calculation, and routing decisions
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, UTC
from src.agents.receptionist_l1 import ReceptionistL1
from src.models.agent_models import L1Output
from src.models.workflow_models import WorkflowState


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing"""
    with patch('src.agents.receptionist_l1.llm_service') as mock:
        yield mock


@pytest.fixture
def mock_database_service():
    """Mock database service for testing"""
    with patch('src.agents.receptionist_l1.database_service') as mock:
        yield mock


@pytest.fixture
def l1_agent(mock_llm_service, mock_database_service):
    """Create L1 agent instance with mocked dependencies"""
    agent = ReceptionistL1()
    return agent


@pytest.fixture
def sample_workflow_state():
    """Create a sample workflow state for testing"""
    return WorkflowState(
        session_id="test-session-123",
        user_id="user-456",
        caller_type="unknown",
        raw_prompt="I want to schedule a cleaning",
        current_tier="L1",
        messages=[],
        entities={},
        required_slots=[],
        clarification_count=0,
        requires_human_escalation=False
    )


class TestL1Classification:
    """Test L1 intent classification"""
    
    @pytest.mark.asyncio
    async def test_classify_scheduling_intent(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test classification of scheduling intent with high confidence"""
        # Arrange
        sample_workflow_state.raw_prompt = "I need to book a house cleaning for next Tuesday"
        
        mock_llm_response = {
            "intent": "scheduling",
            "confidence": 0.92,
            "caller_type": "client"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert isinstance(result, L1Output)
        assert result.intent_name == "scheduling"
        assert result.confidence >= 0.75
        assert result.caller_type == "client"
        assert result.routing_decision == "route_to_l2"
    
    @pytest.mark.asyncio
    async def test_classify_support_intent(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test classification of support/complaint intent"""
        # Arrange
        sample_workflow_state.raw_prompt = "The cleaners didn't show up today and I'm very upset"
        
        mock_llm_response = {
            "intent": "support",
            "confidence": 0.88,
            "caller_type": "client"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert result.intent_name == "support"
        assert result.confidence >= 0.75
        assert result.routing_decision == "route_to_l2"
    
    @pytest.mark.asyncio
    async def test_classify_billing_intent(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test classification of billing intent"""
        # Arrange
        sample_workflow_state.raw_prompt = "I have a question about my last invoice"
        
        mock_llm_response = {
            "intent": "billing",
            "confidence": 0.85,
            "caller_type": "client"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert result.intent_name == "billing"
        assert result.confidence >= 0.75
    
    @pytest.mark.asyncio
    async def test_classify_sales_intent(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test classification of sales/prospect intent"""
        # Arrange
        sample_workflow_state.raw_prompt = "I'm interested in your cleaning services. How much do you charge?"
        
        mock_llm_response = {
            "intent": "sales",
            "confidence": 0.90,
            "caller_type": "prospect"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert result.intent_name == "sales"
        assert result.caller_type == "prospect"
    
    @pytest.mark.asyncio
    async def test_classify_general_intent(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test classification of general inquiry"""
        # Arrange
        sample_workflow_state.raw_prompt = "What are your business hours?"
        
        mock_llm_response = {
            "intent": "general",
            "confidence": 0.78,
            "caller_type": "unknown"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert result.intent_name == "general"


class TestL1ConfidenceThresholds:
    """Test confidence threshold handling"""
    
    @pytest.mark.asyncio
    async def test_high_confidence_routes_immediately(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test that high confidence (>=0.75) routes to L2 immediately"""
        # Arrange
        mock_llm_response = {
            "intent": "scheduling",
            "confidence": 0.92,
            "caller_type": "client"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert result.confidence >= 0.75
        assert result.routing_decision == "route_to_l2"
        assert result.clarification_needed is False
    
    @pytest.mark.asyncio
    async def test_medium_confidence_requests_clarification(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test that medium confidence (0.4-0.75) requests clarification"""
        # Arrange
        sample_workflow_state.raw_prompt = "I need help"
        
        mock_llm_response = {
            "intent": "general",
            "confidence": 0.55,
            "caller_type": "unknown"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert 0.4 <= result.confidence < 0.75
        assert result.routing_decision == "clarify"
        assert result.clarification_needed is True
        assert result.clarification_question is not None
    
    @pytest.mark.asyncio
    async def test_low_confidence_escalates_to_human(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test that low confidence (<0.4) escalates to human"""
        # Arrange
        sample_workflow_state.raw_prompt = "asdfghjkl"
        
        mock_llm_response = {
            "intent": "unknown",
            "confidence": 0.15,
            "caller_type": "unknown"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert result.confidence < 0.4
        assert result.routing_decision == "escalate_to_human"


class TestCallerTypeDetection:
    """Test caller type identification"""
    
    @pytest.mark.asyncio
    async def test_detect_existing_client(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test detection of existing client"""
        # Arrange
        sample_workflow_state.raw_prompt = "I'm an existing customer and need to reschedule"
        sample_workflow_state.user_id = "user-123"  # Known user
        
        mock_llm_response = {
            "intent": "scheduling",
            "confidence": 0.90,
            "caller_type": "client"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert result.caller_type == "client"
    
    @pytest.mark.asyncio
    async def test_detect_prospect(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test detection of new prospect"""
        # Arrange
        sample_workflow_state.raw_prompt = "I've never used your service before. How does it work?"
        sample_workflow_state.user_id = None  # Unknown user
        
        mock_llm_response = {
            "intent": "sales",
            "confidence": 0.87,
            "caller_type": "prospect"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert result.caller_type == "prospect"
    
    @pytest.mark.asyncio
    async def test_detect_partner(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test detection of partner/vendor"""
        # Arrange
        sample_workflow_state.raw_prompt = "This is ABC Supplies calling about your order"
        
        mock_llm_response = {
            "intent": "general",
            "confidence": 0.80,
            "caller_type": "partner"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert
        assert result.caller_type == "partner"


class TestL1ErrorHandling:
    """Test error handling in L1 agent"""
    
    @pytest.mark.asyncio
    async def test_handle_llm_timeout(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test handling of LLM timeout"""
        # Arrange
        mock_llm_service.generate_json.side_effect = TimeoutError("LLM timeout")
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await l1_agent.classify(sample_workflow_state)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_handle_malformed_json(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test handling of malformed JSON from LLM"""
        # Arrange
        mock_llm_service.generate_json.return_value = {
            "intent": "scheduling"
            # Missing required fields
        }
        
        # Act & Assert
        with pytest.raises(ValueError):
            await l1_agent.classify(sample_workflow_state)
    
    @pytest.mark.asyncio
    async def test_handle_invalid_intent(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test handling of invalid intent name"""
        # Arrange
        mock_llm_response = {
            "intent": "invalid_intent_name",
            "confidence": 0.80,
            "caller_type": "client"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        result = await l1_agent.classify(sample_workflow_state)
        
        # Assert - should map to general or escalate
        assert result.routing_decision in ["escalate_to_human", "clarify"]


class TestL1Logging:
    """Test logging functionality"""
    
    @pytest.mark.asyncio
    async def test_log_classification_decision(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test that classification decisions are logged"""
        # Arrange
        mock_llm_response = {
            "intent": "scheduling",
            "confidence": 0.92,
            "caller_type": "client"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        with patch('src.agents.receptionist_l1.logger') as mock_logger:
            # Act
            await l1_agent.classify(sample_workflow_state)
            
            # Assert
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args[0][0]
            assert "L1" in call_args
            assert "scheduling" in call_args


class TestL1Performance:
    """Test performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_classification_speed(self, l1_agent, mock_llm_service, sample_workflow_state):
        """Test that L1 classification completes quickly"""
        # Arrange
        mock_llm_response = {
            "intent": "scheduling",
            "confidence": 0.92,
            "caller_type": "client"
        }
        mock_llm_service.generate_json.return_value = mock_llm_response
        
        # Act
        start_time = datetime.now(UTC)
        await l1_agent.classify(sample_workflow_state)
        end_time = datetime.now(UTC)
        
        # Assert - L1 should be very fast (under 2 seconds in test environment)
        duration = (end_time - start_time).total_seconds()
        assert duration < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])