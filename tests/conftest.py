# ==================== tests/conftest.py ====================
"""
Shared pytest fixtures and configuration for all tests
Provides common setup, mocks, and utilities
"""
import pytest
import asyncio
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings"""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for multi-component flows"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end scenario tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add markers based on test file location
        if "test_l1" in item.nodeid:
            item.add_marker(pytest.mark.l1)
        elif "test_l2" in item.nodeid:
            item.add_marker(pytest.mark.l2)
        elif "test_l3" in item.nodeid:
            item.add_marker(pytest.mark.l3)
        elif "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
        elif "test_performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)


# ============================================================================
# Event Loop Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing"""
    with patch('src.services.llm_service.LLMService') as mock:
        mock_instance = Mock()
        mock_instance.generate_json = AsyncMock()
        mock_instance.generate_text = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_database_service():
    """Mock database service for testing"""
    with patch('src.services.database_service.DatabaseService') as mock:
        mock_instance = Mock()
        mock_instance.find_agent_action_prompt = AsyncMock()
        mock_instance.save_conversation = AsyncMock()
        mock_instance.get_user_info = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_booking_service():
    """Mock booking service for testing"""
    with patch('src.actions.booking_actions.BookingService') as mock:
        mock_instance = Mock()
        mock_instance.create_booking = AsyncMock()
        mock_instance.reschedule_booking = AsyncMock()
        mock_instance.cancel_booking = AsyncMock()
        mock_instance.check_availability = AsyncMock()
        mock_instance.calculate_price = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_support_service():
    """Mock support service for testing"""
    with patch('src.actions.support_actions.SupportService') as mock:
        mock_instance = Mock()
        mock_instance.create_ticket = AsyncMock()
        mock_instance.update_job_status = AsyncMock()
        mock_instance.resolve_ticket = AsyncMock()
        mock_instance.escalate_issue = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_billing_service():
    """Mock billing service for testing"""
    with patch('src.actions.billing_actions.BillingService') as mock:
        mock_instance = Mock()
        mock_instance.generate_invoice = AsyncMock()
        mock_instance.process_payment = AsyncMock()
        mock_instance.get_invoice = AsyncMock()
        mock_instance.send_receipt = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_session_service():
    """Mock session service for testing"""
    with patch('src.services.session_service.SessionService') as mock:
        mock_instance = Mock()
        mock_instance.create_session = AsyncMock()
        mock_instance.save_state = AsyncMock()
        mock_instance.load_state = AsyncMock()
        mock_instance.append_message = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_all_services(
    mock_llm_service,
    mock_database_service,
    mock_booking_service,
    mock_support_service,
    mock_billing_service,
    mock_session_service
):
    """Fixture providing all mocked services"""
    return {
        'llm': mock_llm_service,
        'database': mock_database_service,
        'booking': mock_booking_service,
        'support': mock_support_service,
        'billing': mock_billing_service,
        'session': mock_session_service
    }


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_user_message():
    """Sample user message for testing"""
    return {
        "role": "user",
        "text": "I want to book a cleaning",
        "timestamp": datetime.now(UTC).isoformat()
    }


@pytest.fixture
def sample_agent_message():
    """Sample agent message for testing"""
    return {
        "role": "assistant",
        "text": "I'd be happy to help you book a cleaning. Could you provide the address?",
        "timestamp": datetime.now(UTC).isoformat()
    }


@pytest.fixture
def sample_entities():
    """Sample extracted entities for testing"""
    return {
        "service_type": "house cleaning",
        "address": "123 Main St, Minneapolis, MN",
        "preferred_date": "2025-10-15T14:00:00-05:00",
        "contact_number": "(555) 123-4567",
        "recurrence": "one-time"
    }


@pytest.fixture
def sample_booking_response():
    """Sample booking response for testing"""
    return {
        "success": True,
        "booking_id": "BOOK-TEST-12345",
        "confirmation_code": "CONF-ABC123",
        "scheduled_time": "2025-10-15T14:00:00-05:00",
        "total_price": 150.00
    }


@pytest.fixture
def sample_ticket_response():
    """Sample support ticket response for testing"""
    return {
        "success": True,
        "ticket_id": "TICKET-TEST-98765",
        "priority": "high",
        "assigned_to": "support_team",
        "estimated_response_time": "2 hours"
    }


# ============================================================================
# WorkflowState Fixtures
# ============================================================================

@pytest.fixture
def basic_workflow_state():
    """Basic workflow state for testing"""
    from src.models.workflow_models import WorkflowState
    
    return WorkflowState(
        session_id="test-session-001",
        user_id="test-user-001",
        caller_type="client",
        raw_prompt="Test prompt",
        current_tier="L1",
        messages=[],
        entities={},
        required_slots=[],
        clarification_count=0,
        requires_human_escalation=False
    )


@pytest.fixture
def l1_complete_state():
    """Workflow state after L1 completion"""
    from src.models.workflow_models import WorkflowState, IntentL1
    
    return WorkflowState(
        session_id="test-session-002",
        user_id="test-user-002",
        caller_type="client",
        raw_prompt="I need a cleaning",
        current_tier="L1",
        intent_l1=IntentL1(name="scheduling", confidence=0.92),
        messages=[],
        entities={},
        required_slots=[],
        clarification_count=0
    )


@pytest.fixture
def l2_complete_state():
    """Workflow state after L2 completion"""
    from src.models.workflow_models import WorkflowState, IntentL1, IntentL2
    
    return WorkflowState(
        session_id="test-session-003",
        user_id="test-user-003",
        caller_type="client",
        raw_prompt="Book cleaning at 123 Main St on Oct 15",
        current_tier="L2",
        intent_l1=IntentL1(name="scheduling", confidence=0.92),
        intent_l2=IntentL2(name="book_home_cleaning", confidence=0.95),
        entities={
            "address": "123 Main St",
            "preferred_date": "2025-10-15T14:00:00-05:00"
        },
        required_slots=[],
        selected_l3_agent="SalesAgentL3",
        messages=[],
        clarification_count=0
    )


# ============================================================================
# Helper Functions
# ============================================================================

@pytest.fixture
def create_mock_llm_response():
    """Factory for creating mock LLM responses"""
    def _create_response(
        intent: str,
        confidence: float,
        caller_type: str = "client",
        entities: Dict[str, Any] = None,
        required_slots: List[str] = None
    ) -> Dict[str, Any]:
        response = {
            "intent": intent,
            "confidence": confidence,
            "caller_type": caller_type
        }
        
        if entities is not None:
            response["entities"] = entities
        
        if required_slots is not None:
            response["required_slots"] = required_slots
        
        return response
    
    return _create_response


@pytest.fixture
def assert_workflow_state_valid():
    """Helper to validate workflow state structure"""
    def _validate(state):
        from src.models.workflow_models import WorkflowState
        
        assert isinstance(state, WorkflowState)
        assert state.session_id is not None
        assert state.current_tier in ["L1", "L2", "L3"]
        assert isinstance(state.messages, list)
        assert isinstance(state.entities, dict)
        assert isinstance(state.clarification_count, int)
        assert state.clarification_count >= 0
        
        return True
    
    return _validate


# ============================================================================
# Test Utilities
# ============================================================================

@pytest.fixture
def capture_logs():
    """Capture log messages during test"""
    import logging
    from io import StringIO
    
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    
    logger = logging.getLogger()
    logger.addHandler(handler)
    
    yield log_stream
    
    logger.removeHandler(handler)


@pytest.fixture
def measure_time():
    """Measure execution time of code block"""
    import time
    from contextlib import contextmanager
    
    @contextmanager
    def _measure():
        start = time.perf_counter()
        timings = {'start': start}
        yield timings
        timings['end'] = time.perf_counter()
        timings['elapsed'] = timings['end'] - timings['start']
        timings['elapsed_ms'] = timings['elapsed'] * 1000
    
    return _measure


@pytest.fixture
def random_test_data():
    """Generate random test data"""
    import random
    import string
    
    def _generate(data_type: str, **kwargs):
        if data_type == "session_id":
            return f"test-session-{''.join(random.choices(string.ascii_letters + string.digits, k=8))}"
        
        elif data_type == "user_id":
            return f"test-user-{''.join(random.choices(string.digits, k=6))}"
        
        elif data_type == "booking_id":
            return f"BOOK-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        
        elif data_type == "phone":
            return f"({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"
        
        elif data_type == "address":
            num = random.randint(100, 9999)
            streets = ["Main St", "Oak Ave", "Elm Street", "Pine Road", "Maple Drive"]
            return f"{num} {random.choice(streets)}, Minneapolis, MN"
        
        elif data_type == "confidence":
            min_val = kwargs.get('min', 0.0)
            max_val = kwargs.get('max', 1.0)
            return round(random.uniform(min_val, max_val), 2)
        
        else:
            raise ValueError(f"Unknown data type: {data_type}")
    
    return _generate


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests"""
    yield
    # Add any singleton reset logic here if needed


@pytest.fixture(autouse=True)
def cleanup_temp_data():
    """Clean up temporary test data after each test"""
    yield
    # Add cleanup logic here if needed


# ============================================================================
# Async Test Helpers
# ============================================================================

@pytest.fixture
def run_async():
    """Helper to run async functions in sync tests"""
    def _run(coro):
        return asyncio.run(coro)
    return _run


@pytest.fixture
async def async_context():
    """Provide async context for testing"""
    context = {
        'tasks': [],
        'results': []
    }
    yield context
    
    # Cleanup any remaining tasks
    for task in context['tasks']:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def performance_tracker():
    """Track performance metrics during tests"""
    class PerformanceTracker:
        def __init__(self):
            self.metrics = {
                'latencies': [],
                'throughputs': [],
                'errors': []
            }
        
        def record_latency(self, latency_ms: float):
            self.metrics['latencies'].append(latency_ms)
        
        def record_throughput(self, throughput: float):
            self.metrics['throughputs'].append(throughput)
        
        def record_error(self, error: str):
            self.metrics['errors'].append(error)
        
        def get_stats(self):
            from statistics import mean, median, stdev
            
            stats = {}
            
            if self.metrics['latencies']:
                stats['latency'] = {
                    'mean': mean(self.metrics['latencies']),
                    'median': median(self.metrics['latencies']),
                    'min': min(self.metrics['latencies']),
                    'max': max(self.metrics['latencies'])
                }
                if len(self.metrics['latencies']) > 1:
                    stats['latency']['stdev'] = stdev(self.metrics['latencies'])
            
            if self.metrics['throughputs']:
                stats['throughput'] = {
                    'mean': mean(self.metrics['throughputs']),
                    'max': max(self.metrics['throughputs'])
                }
            
            stats['error_count'] = len(self.metrics['errors'])
            
            return stats
    
    return PerformanceTracker()


# ============================================================================
# Database Testing Fixtures
# ============================================================================

@pytest.fixture
async def test_database():
    """Provide test database connection"""
    # This would connect to a test database
    # For now, we'll use mocks
    from unittest.mock import AsyncMock
    
    db = AsyncMock()
    db.sessions = AsyncMock()
    db.conversations = AsyncMock()
    db.tickets = AsyncMock()
    
    yield db
    
    # Cleanup test data
    await db.sessions.delete_many({})
    await db.conversations.delete_many({})
    await db.tickets.delete_many({})


# ============================================================================
# Scenario Testing Fixtures
# ============================================================================

@pytest.fixture
def booking_scenario_data():
    """Complete booking scenario test data"""
    return {
        'prompt': "I want to book a house cleaning at 123 Main St on October 15th at 2pm",
        'expected_intent': "scheduling",
        'expected_caller_type': "client",
        'expected_entities': {
            'address': "123 Main St",
            'preferred_date': "2025-10-15T14:00:00",
            'service_type': "house cleaning"
        },
        'expected_l3_agent': "SalesAgentL3"
    }


@pytest.fixture
def support_scenario_data():
    """Complete support scenario test data"""
    return {
        'prompt': "The cleaners didn't show up and I'm very upset",
        'expected_intent': "support",
        'expected_caller_type': "client",
        'expected_entities': {
            'issue_type': "missed_appointment",
            'sentiment': "upset"
        },
        'expected_l3_agent': "SupportAgentL3"
    }


@pytest.fixture
def billing_scenario_data():
    """Complete billing scenario test data"""
    return {
        'prompt': "I need to pay invoice 12345",
        'expected_intent': "billing",
        'expected_caller_type': "client",
        'expected_entities': {
            'invoice_number': "12345",
            'action': "payment"
        },
        'expected_l3_agent': "BillingAgentL3"
    }


# ============================================================================
# Assertion Helpers
# ============================================================================

@pytest.fixture
def assert_valid_l1_output():
    """Validate L1 output structure"""
    def _validate(output):
        from src.models.agent_models import L1Output
        
        assert isinstance(output, L1Output)
        assert output.intent_name is not None
        assert 0.0 <= output.confidence <= 1.0
        assert output.caller_type in ["client", "prospect", "partner", "unknown"]
        assert output.routing_decision in ["route_to_l2", "clarify", "escalate_to_human"]
        
        if output.routing_decision == "clarify":
            assert output.clarification_question is not None
        
        return True
    
    return _validate


@pytest.fixture
def assert_valid_l2_output():
    """Validate L2 output structure"""
    def _validate(output):
        from src.models.agent_models import L2Output
        
        assert isinstance(output, L2Output)
        assert output.refined_intent is not None
        assert 0.0 <= output.confidence <= 1.0
        assert isinstance(output.entities, dict)
        assert isinstance(output.required_slots, list)
        
        if len(output.required_slots) > 0:
            assert output.clarification_question is not None
        else:
            assert output.suggested_l3_agent is not None
        
        return True
    
    return _validate


@pytest.fixture
def assert_valid_l3_output():
    """Validate L3 output structure"""
    def _validate(output):
        from src.models.agent_models import L3Output
        
        assert isinstance(output, L3Output)
        assert isinstance(output.success, bool)
        assert output.confirmation_message is not None
        
        if output.success:
            assert output.next_steps is not None
            # Should have either booking_id or ticket_id
            assert output.booking_id is not None or output.ticket_id is not None
        
        return True
    
    return _validate


# ============================================================================
# Mock Response Builders
# ============================================================================

@pytest.fixture
def build_l1_response():
    """Builder for L1 mock responses"""
    def _build(
        intent: str = "scheduling",
        confidence: float = 0.90,
        caller_type: str = "client"
    ):
        return {
            "intent": intent,
            "confidence": confidence,
            "caller_type": caller_type
        }
    
    return _build


@pytest.fixture
def build_l2_response():
    """Builder for L2 mock responses"""
    def _build(
        refined_intent: str = "book_home_cleaning",
        confidence: float = 0.92,
        entities: dict = None,
        required_slots: list = None,
        suggested_l3_agent: str = "SalesAgentL3"
    ):
        return {
            "refined_intent": refined_intent,
            "confidence": confidence,
            "entities": entities or {},
            "required_slots": required_slots or [],
            "suggested_l3_agent": suggested_l3_agent
        }
    
    return _build


@pytest.fixture
def build_l3_response():
    """Builder for L3 mock responses"""
    def _build(
        success: bool = True,
        booking_id: str = None,
        ticket_id: str = None,
        confirmation_message: str = "Operation completed successfully"
    ):
        response = {
            "success": success,
            "confirmation_message": confirmation_message
        }
        
        if booking_id:
            response["booking_id"] = booking_id
        
        if ticket_id:
            response["ticket_id"] = ticket_id
        
        return response
    
    return _build


# ============================================================================
# Integration Test Helpers
# ============================================================================

@pytest.fixture
def full_workflow_mocks(mock_all_services):
    """Configure mocks for full workflow testing"""
    # Configure L1 mock
    mock_all_services['llm'].generate_json.return_value = {
        "intent": "scheduling",
        "confidence": 0.92,
        "caller_type": "client"
    }
    
    # Configure booking mock
    mock_all_services['booking'].create_booking.return_value = {
        "success": True,
        "booking_id": "BOOK-TEST-123"
    }
    
    # Configure support mock
    mock_all_services['support'].create_ticket.return_value = {
        "success": True,
        "ticket_id": "TICKET-TEST-456"
    }
    
    # Configure billing mock
    mock_all_services['billing'].process_payment.return_value = {
        "success": True,
        "transaction_id": "TXN-TEST-789"
    }
    
    return mock_all_services


# ============================================================================
# Custom Markers
# ============================================================================

def pytest_collection_finish(session):
    """Print test collection summary"""
    print(f"\n{'='*70}")
    print(f"Collected {len(session.items)} tests")
    print(f"{'='*70}\n")


# ============================================================================
# Test Report Customization
# ============================================================================

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Customize test reports"""
    outcome = yield
    report = outcome.get_result()
    
    # Add custom properties to report
    if report.when == "call":
        report.test_type = None
        
        # Identify test type from markers
        if hasattr(item, 'own_markers'):
            for marker in item.own_markers:
                if marker.name in ['unit', 'integration', 'e2e', 'performance']:
                    report.test_type = marker.name
                    break


if __name__ == "__main__":
    # This file is imported by pytest, not run directly
    pass