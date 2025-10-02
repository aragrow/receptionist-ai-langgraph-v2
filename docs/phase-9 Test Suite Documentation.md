# Testing Suite for 3-Tier Agent Routing System

Comprehensive test suite for the AI receptionist workflow with L1→L2→L3 routing architecture.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Coverage Requirements](#coverage-requirements)
- [CI/CD Integration](#cicd-integration)

---

## 🎯 Overview

This test suite validates the complete 3-tier routing system including:

- **L1 Receptionist**: Intent classification and caller type detection
- **L2 Receptionists**: Slot extraction and clarification handling
- **L3 Domain Agents**: Action execution and confirmation generation
- **Routing Logic**: Decision-making between tiers
- **Session Management**: Multi-turn conversation handling
- **Performance**: Latency, throughput, and scalability

### Test Coverage Goals

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: All critical flows
- **E2E Tests**: All user scenarios
- **Performance Tests**: Latency < 2s P95

---

## 📁 Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                     # Pytest configuration
├── test_agents/
│   ├── test_l1_agent.py          # L1 receptionist tests
│   ├── test_l2_agents.py         # L2 receptionist tests
│   └── test_l3_agents.py         # L3 domain agent tests
├── test_integration/
│   └── test_integration.py       # Multi-tier flow tests
├── test_e2e_scenarios.py         # Real-world scenario tests
└── test_performance.py           # Performance and load tests
```

---

## 🚀 Running Tests

### Quick Start

```bash
# Run all tests
./run_tests.sh --all

# Run specific test categories
./run_tests.sh --unit
./run_tests.sh --integration
./run_tests.sh --e2e
./run_tests.sh --performance
```

### Using pytest Directly

```bash
# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_agents/test_l1_agent.py -v

# Run tests matching a pattern
pytest tests/ -k "test_booking" -v

# Run tests with specific marker
pytest tests/ -m "unit" -v

# Run in parallel (faster)
pytest tests/ -n auto

# Run with verbose output
pytest tests/ -vv --tb=short
```

### Test Markers

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# E2E tests only
pytest -m e2e

# Performance tests (excluding slow tests)
pytest -m "performance and not slow"

# Tests for specific tier
pytest -m l1  # or l2, l3
```

---

## 🧪 Test Categories

### 1. Unit Tests (`tests/test_agents/`)

Test individual components in isolation with mocked dependencies.

**test_l1_agent.py** - L1 Receptionist Tests
- ✅ Intent classification accuracy
- ✅ Confidence threshold handling
- ✅ Caller type detection
- ✅ Error handling
- ✅ Logging functionality
- ✅ Performance characteristics

**test_l2_agents.py** - L2 Receptionist Tests
- ✅ Slot extraction (complete and incomplete)
- ✅ Clarification question generation
- ✅ L3 agent selection
- ✅ Confidence handling
- ✅ Slot validation

**test_l3_agents.py** - L3 Domain Agent Tests
- ✅ Booking creation and management
- ✅ Support ticket generation
- ✅ Payment processing
- ✅ Confirmation message formatting
- ✅ Next steps generation
- ✅ Error handling

**Example: Running L1 Tests**
```bash
pytest tests/test_agents/test_l1_agent.py -v
```

Expected Output:
```
test_l1_agent.py::TestL1Classification::test_classify_scheduling_intent PASSED
test_l1_agent.py::TestL1Classification::test_classify_support_intent PASSED
test_l1_agent.py::TestL1ConfidenceThresholds::test_high_confidence_routes_immediately PASSED
...
==================== 25 passed in 2.34s ====================
```

### 2. Integration Tests (`tests/test_integration/`)

Test complete flows across multiple tiers.

**test_integration.py** - Multi-Tier Flow Tests
- ✅ Complete booking flow (L1→L2→L3)
- ✅ Booking with clarification loops
- ✅ Support ticket creation
- ✅ Billing inquiry and payment
- ✅ Routing decision logic
- ✅ Multi-turn conversations
- ✅ Human escalation scenarios

**Example: Running Integration Tests**
```bash
pytest tests/test_integration/ -v
```

### 3. End-to-End Tests (`tests/test_e2e_scenarios.py`)

Test real-world user scenarios from start to finish.

**Scenarios Covered:**
- ✅ New customer booking first cleaning
- ✅ Existing client rescheduling
- ✅ Gradual information collection
- ✅ Support ticket with clarifications
- ✅ Unknown caller identification
- ✅ Emergency escalation
- ✅ Complex multi-turn conversations
- ✅ User changing mind mid-conversation
- ✅ Partner/vendor check-ins

**Example: Running E2E Tests**
```bash
pytest tests/test_e2e_scenarios.py -v --tb=short
```

### 4. Performance Tests (`tests/test_performance.py`)

Test system performance under various loads.

**Performance Metrics:**
- ✅ L1 classification latency (< 1s average)
- ✅ End-to-end flow latency (< 3s average)
- ✅ Throughput (> 5 req/s)
- ✅ Concurrent session handling (100+ sessions)
- ✅ Session storage performance
- ✅ Memory usage patterns

**Example: Running Performance Tests**
```bash
# Run quick performance tests
pytest tests/test_performance.py -v -m "not slow"

# Run all performance tests (including slow ones)
pytest tests/test_performance.py -v
```

---

## ✍️ Writing Tests

### Test Structure Template

```python
import pytest
from unittest.mock import Mock, AsyncMock

class TestFeatureName:
    """Test description"""
    
    @pytest.mark.asyncio
    async def test_specific_behavior(self, fixture_name):
        """Test what happens when..."""
        # Arrange
        test_data = {...}
        mock_service.method.return_value = expected_result
        
        # Act
        result = await function_under_test(test_data)
        
        # Assert
        assert result.success is True
        assert result.value == expected_value
```

### Using Fixtures

```python
def test_with_mocked_services(
    mock_llm_service,
    mock_booking_service,
    sample_entities
):
    """Fixtures are automatically injected"""
    # Use fixtures directly
    mock_llm_service.generate_json.return_value = {...}
    assert sample_entities['address'] == "123 Main St"
```

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_function(performance_workflow):
    """Test async code"""
    result = await performance_workflow.run("Test prompt")
    assert result.success is True
```

### Parameterized Tests

```python
@pytest.mark.parametrize("intent,confidence,expected", [
    ("scheduling", 0.95, "route_to_l2"),
    ("support", 0.60, "clarify"),
    ("unknown", 0.20, "escalate_to_human")
])
async def test_routing_decisions(intent, confidence, expected):
    """Test multiple scenarios with one test"""
    result = await classify(intent, confidence)
    assert result.routing_decision == expected
```

---

## 📊 Coverage Requirements

### Minimum Coverage Targets

| Component | Target Coverage |
|-----------|----------------|
| L1 Agents | 90% |
| L2 Agents | 85% |
| L3 Agents | 85% |
| Routing Logic | 95% |
| Session Management | 80% |
| Overall | 80% |

### Generating Coverage Reports

```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Interpreting Coverage

```bash
# Terminal coverage summary
pytest tests/ --cov=src --cov-report=term-missing

# Output example:
Name                          Stmts   Miss  Cover   Missing
-----------------------------------------------------------
src/agents/receptionist_l1.py    145     12    92%   67-70, 145-150
src/agents/receptionist_l2_base.py  180     25    86%   ...
-----------------------------------------------------------