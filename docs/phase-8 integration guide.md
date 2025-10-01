# Phase 8: Telemetry & Monitoring - Integration Guide

## Overview
This guide shows how to integrate the metrics and logging services into your existing AI Receptionist workflow.

## Files Created

### 1. `src/services/metrics_service.py`
- **Purpose**: Track and aggregate performance metrics
- **Key Classes**: `MetricsService`, metric dataclasses for each tier
- **Usage**: Record events at each stage of the workflow

### 2. `src/services/logging_service.py`
- **Purpose**: Structured JSON logging with full context
- **Key Classes**: `LoggingService`, `StructuredLogger`
- **Usage**: Log all routing decisions, classifications, and errors

### 3. `src/api/analytics_endpoints.py`
- **Purpose**: REST API endpoints for viewing metrics
- **Endpoints**: `/analytics/dashboard`, `/analytics/l1/accuracy`, etc.
- **Usage**: Query metrics programmatically or view in dashboard

### 4. `templates/analytics_dashboard.html`
- **Purpose**: Web-based analytics dashboard
- **Features**: Real-time metrics, auto-refresh, time window selection
- **Usage**: Open in browser to view metrics

## Installation Steps

### Step 1: Create Directory Structure
```bash
# Create services directory if it doesn't exist
mkdir -p src/services

# Create API directory if it doesn't exist
mkdir -p src/api

# Create templates directory for HTML dashboard
mkdir -p templates

# Create logs directory
mkdir -p logs
```

### Step 2: Add the Service Files
Place the following files in your project:
- `src/services/metrics_service.py`
- `src/services/logging_service.py`
- `src/api/analytics_endpoints.py`
- `templates/analytics_dashboard.html`

### Step 3: Update main.py to Include Analytics Endpoints
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.api.analytics_endpoints import router as analytics_router

app = FastAPI(title="AI Receptionist")

# Include analytics router
app.include_router(analytics_router)

# Serve dashboard HTML
@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse("templates/analytics_dashboard.html")

# Your existing endpoints...
```

### Step 4: Initialize Services in Your Workflow

#### Option A: Initialize in Workflow File
```python
# In src/workflow/ai_receptionist_workflow.py

from src.services.metrics_service import get_metrics_service
from src.services.logging_service import get_logging_service

# Get global instances
metrics_service = get_metrics_service()
logging_service = get_logging_service(
    log_file="logs/ai_receptionist.log",
    console_output=True
)
```

#### Option B: Initialize in Each Node
```python
# In individual node files (e.g., src/nodes/receptionist_l1.py)

from src.services.metrics_service import get_metrics_service
from src.services.logging_service import get_logging_service

metrics = get_metrics_service()
logger = get_logging_service()
```

## Integration Examples

### Example 1: Recording L1 Classification Metrics

```python
# In your L1 Receptionist node
from datetime import datetime

def receptionist_l1_node(state: WorkflowState) -> WorkflowState:
    start_time = datetime.now(datetime.UTC)
    
    # ... your L1 classification logic ...
    intent = "scheduling"
    confidence = 0.92
    caller_type = "client"
    
    # Calculate processing time
    end_time = datetime.now(datetime.UTC)
    processing_time_ms = (end_time - start_time).total_seconds() * 1000
    
    # Record metrics
    metrics_service.record_l1_classification(
        session_id=state.session_id,
        intent_name=intent,
        confidence=confidence,
        caller_type=caller_type,
        processing_time_ms=processing_time_ms
    )
    
    # Log classification
    logging_service.log_l1_classification(
        session_id=state.session_id,
        intent=intent,
        confidence=confidence,
        caller_type=caller_type,
        processing_time_ms=processing_time_ms,
        raw_output={"full_llm_response": "..."}
    )
    
    # Update state
    state.intent_L1 = {"name": intent, "confidence": confidence}
    state.caller_type = caller_type
    
    return state
```

### Example 2: Recording L2 Refinement Metrics

```python
# In your L2 Receptionist node

def receptionist_l2_node(state: WorkflowState) -> WorkflowState:
    start_time = datetime.now(datetime.UTC)
    
    # ... your L2 refinement logic ...
    refined_intent = "book_home_cleaning"
    confidence = 0.95
    entities = {"service_type": "house cleaning", "address": "123 Main St"}
    required_slots = ["preferred_date", "address", "contact_number"]
    
    # Calculate processing time
    end_time = datetime.now(datetime.UTC)
    processing_time_ms = (end_time - start_time).total_seconds() * 1000
    
    # Determine if clarification needed
    clarification_needed = len(entities) < len(required_slots)
    
    # Record metrics
    metrics_service.record_l2_refinement(
        session_id=state.session_id,
        intent_name=refined_intent,
        confidence=confidence,
        slots_extracted=len(entities),
        slots_required=len(required_slots),
        processing_time_ms=processing_time_ms,
        clarification_needed=clarification_needed
    )
    
    # Log refinement
    logging_service.log_l2_refinement(
        session_id=state.session_id,
        refined_intent=refined_intent,
        confidence=confidence,
        slots_extracted=entities,
        required_slots=required_slots,
        processing_time_ms=processing_time_ms
    )
    
    # Update state
    state.intent_L2 = {"name": refined_intent, "confidence": confidence}
    state.entities = entities
    state.required_slots = required_slots
    
    return state
```

### Example 3: Recording Routing Decisions

```python
# In your routing logic

def route_l1_to_l2(state: WorkflowState) -> str:
    start_time = datetime.now(datetime.UTC)
    
    # Routing logic
    caller_type = state.caller_type
    confidence = state.intent_L1.get("confidence", 0.0)
    
    if caller_type == "client":
        next_agent = "client_receptionist_l2"
    elif caller_type == "prospect":
        next_agent = "sales_receptionist_l2"
    else:
        next_agent = "general_receptionist_l2"
    
    # Calculate routing time
    end_time = datetime.now(datetime.UTC)
    routing_time_ms = (end_time - start_time).total_seconds() * 1000
    
    # Record routing
    metrics_service.record_routing(
        session_id=state.session_id,
        from_tier="L1",
        to_tier="L2",
        routing_time_ms=routing_time_ms,
        confidence=confidence,
        routing_reason=f"Caller type: {caller_type}"
    )
    
    # Log routing decision
    logging_service.log_routing_decision(
        session_id=state.session_id,
        from_tier="L1",
        to_tier=f"L2-{next_agent}",
        confidence=confidence,
        reasoning=f"Routed based on caller_type={caller_type}",
        routing_time_ms=routing_time_ms
    )
    
    return next_agent
```

### Example 4: Recording Clarification Requests

```python
# In your clarification handler

def clarification_handler_node(state: WorkflowState) -> WorkflowState:
    missing_slots = [
        slot for slot in state.required_slots 
        if slot not in state.entities
    ]
    
    attempt_number = state.clarification_count + 1
    
    # Generate clarification question
    question = f"To complete your booking, I need: {', '.join(missing_slots)}"
    
    # Record clarification
    metrics_service.record_clarification(
        session_id=state.session_id,
        tier=state.current_tier,
        attempt_number=attempt_number,
        missing_slots=missing_slots,
        resolved=False  # Will be updated when user responds
    )
    
    # Log clarification request
    logging_service.log_clarification_request(
        session_id=state.session_id,
        tier=state.current_tier,
        attempt_number=attempt_number,
        missing_slots=missing_slots,
        question=question
    )
    
    state.clarification_count += 1
    state.messages.append({"role": "assistant", "content": question})
    
    return state
```

### Example 5: Recording Human Escalations

```python
# In your escalation node

def human_escalation_node(state: WorkflowState) -> WorkflowState:
    import uuid
    
    ticket_id = str(uuid.uuid4())
    reason = "max_clarifications_reached"
    
    # Create ticket (implementation depends on your ticket system)
    # create_ticket(session_id=state.session_id, ...)
    
    # Record escalation
    metrics_service.record_escalation(
        session_id=state.session_id,
        reason=reason,
        tier=state.current_tier,
        confidence=state.routing_confidence,
        clarification_attempts=state.clarification_count,
        ticket_id=ticket_id
    )
    
    # Log escalation
    logging_service.log_human_escalation(
        session_id=state.session_id,
        tier=state.current_tier,
        reason=reason,
        confidence=state.routing_confidence,
        clarification_attempts=state.clarification_count,
        ticket_id=ticket_id,
        context_data={
            "missing_slots": state.required_slots,
            "extracted_entities": state.entities
        }
    )
    
    state.requires_human_escalation = True
    state.ticket_id = ticket_id
    
    return state
```

### Example 6: Recording L3 Action Execution

```python
# In your L3 agent

def sales_agent_l3_node(state: WorkflowState) -> WorkflowState:
    start_time = datetime.now(datetime.UTC)
    
    agent_name = "SalesAgentL3"
    action = "create_booking"
    
    # Log action start
    logging_service.log_l3_action_start(
        session_id=state.session_id,
        agent_name=agent_name,
        action=action,
        parameters=state.entities
    )
    
    try:
        # Execute action
        result = create_booking(state.entities)
        success = True
        error_code = None
        
        # Calculate processing time
        end_time = datetime.now(datetime.UTC)
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Record success
        metrics_service.record_l3_execution(
            session_id=state.session_id,
            agent_name=agent_name,
            action=action,
            success=True,
            processing_time_ms=processing_time_ms
        )
        
        # Log success
        logging_service.log_l3_action_success(
            session_id=state.session_id,
            agent_name=agent_name,
            action=action,
            result=result,
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        # Calculate processing time
        end_time = datetime.now(datetime.UTC)
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        error_code = "BOOKING_FAILED"
        
        # Record failure
        metrics_service.record_l3_execution(
            session_id=state.session_id,
            agent_name=agent_name,
            action=action,
            success=False,
            processing_time_ms=processing_time_ms,
            error_code=error_code
        )
        
        # Log failure
        logging_service.log_l3_action_failure(
            session_id=state.session_id,
            agent_name=agent_name,
            action=action,
            error_code=error_code,
            error=e,
            processing_time_ms=processing_time_ms
        )
        
        raise  # Re-raise for error handling
    
    return state
```

### Example 7: Recording Complete Session

```python
# In your main workflow orchestrator

def run_workflow(initial_message: str, session_id: str) -> WorkflowState:
    start_time = datetime.now(datetime.UTC)
    
    # Log session start
    logging_service.log_session_start(
        session_id=session_id,
        caller_type="unknown",  # Will be determined by L1
        initial_message=initial_message
    )
    
    try:
        # Initialize state
        state = WorkflowState(
            session_id=session_id,
            user_id=None,
            raw_prompt=initial_message,
            # ... other fields
        )
        
        # Run workflow through L1 -> L2 -> L3
        # ... workflow execution ...
        
        # Determine final outcome
        if state.requires_human_escalation:
            final_outcome = "escalated"
        elif state.success:
            final_outcome = "success"
        else:
            final_outcome = "error"
        
        # Calculate duration
        end_time = datetime.now(datetime.UTC)
        total_duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Record session metrics
        metrics_service.record_session(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            message_count=len(state.messages),
            tiers_traversed=[state.current_tier],  # Track which tiers were used
            final_outcome=final_outcome,
            caller_type=state.caller_type
        )
        
        # Log session end
        logging_service.log_session_end(
            session_id=session_id,
            final_outcome=final_outcome,
            total_duration_ms=total_duration_ms,
            message_count=len(state.messages),
            tiers_traversed=[state.current_tier]
        )
        
        return state
        
    except Exception as e:
        # Log session error
        logging_service.log_session_error(
            session_id=session_id,
            error=e,
            context_data={"initial_message": initial_message}
        )
        raise
```

### Example 8: Low Confidence Detection

```python
# In routing conditions

def check_confidence_threshold(state: WorkflowState) -> str:
    confidence = state.intent_L2.get("confidence", 0.0)
    threshold_high = 0.75
    threshold_low = 0.4
    
    if confidence >= threshold_high:
        action = "route_to_l3"
    elif confidence >= threshold_low:
        action = "request_clarification"
        
        # Log low confidence detection
        logging_service.log_low_confidence_detection(
            session_id=state.session_id,
            tier="L2",
            confidence=confidence,
            threshold=threshold_high,
            action_taken=action
        )
    else:
        action = "escalate_to_human"
        
        # Log low confidence detection
        logging_service.log_low_confidence_detection(
            session_id=state.session_id,
            tier="L2",
            confidence=confidence,
            threshold=threshold_low,
            action_taken=action
        )
    
    return action
```

## Usage Examples

### Accessing Metrics via API

```bash
# Get full dashboard (last 24 hours)
curl http://localhost:8000/analytics/dashboard?time_window_hours=24

# Get L1 accuracy
curl http://localhost:8000/analytics/l1/accuracy?time_window_hours=24

# Get confidence distribution for L2
curl http://localhost:8000/analytics/confidence/L2?time_window_hours=24

# Get clarification statistics
curl http://localhost:8000/analytics/clarifications?time_window_hours=24

# Get escalation statistics
curl http://localhost:8000/analytics/escalations?time_window_hours=24

# Get L3 success rates
curl http://localhost:8000/analytics/l3/success-rates?time_window_hours=24

# Get session details
curl http://localhost:8000/analytics/sessions/{session_id}

# Export metrics as CSV
curl http://localhost:8000/analytics/export/csv?metric_type=l1&time_window_hours=24
```

### Viewing Dashboard

1. Start your FastAPI server:
```bash
uvicorn main:app --reload
```

2. Open browser to:
```
http://localhost:8000/dashboard
```

3. The dashboard will automatically load and display metrics

### Programmatic Access

```python
from src.services.metrics_service import get_metrics_service

metrics = get_metrics_service()

# Get dashboard data
dashboard = metrics.get_full_dashboard(time_window_hours=24)

# Get specific metrics
l1_accuracy = metrics.get_l1_accuracy(time_window_hours=24)
routing_perf = metrics.get_avg_routing_time(time_window_hours=24)
escalations = metrics.get_escalation_stats(time_window_hours=24)

print(f"L1 Accuracy: {l1_accuracy['accuracy']}")
print(f"Escalation Rate: {escalations['escalation_rate']}")
```

## Log File Format

Logs are written in JSON format to `logs/ai_receptionist.log`:

```json
{
  "timestamp": "2025-10-01T14:30:25.123456Z",
  "level": "INFO",
  "category": "classification",
  "message": "L1 classified intent: scheduling",
  "session_id": "abc123",
  "context": {
    "tier": "L1",
    "intent": "scheduling",
    "confidence": 0.92,
    "caller_type": "client",
    "processing_time_ms": 234.5
  }
}
```

## Production Considerations

### 1. Persistent Storage
The current implementation uses in-memory storage. For production:

```python
# Option A: Use Redis for fast access
import redis
from src.services.metrics_service import MetricsService

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Store metrics in Redis with TTL
redis_client.setex(
    f"metric:l1:{session_id}",
    86400,  # 24 hour TTL
    json.dumps(metric_data)
)

# Option B: Use TimescaleDB for time-series data
# Create tables for each metric type with timestamp indexing

# Option C: Use MongoDB for flexible document storage
from pymongo import MongoClient

mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['ai_receptionist']

db.l1_metrics.insert_one(asdict(l1_metric))
```

### 2. Log Aggregation
For production logging:

```python
# Use structured logging with external aggregation
import logging
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)

# Or use logging drivers for:
# - Datadog
# - Splunk
# - ELK Stack (Elasticsearch, Logstash, Kibana)
# - CloudWatch (AWS)
```

### 3. Alerting
Set up alerts for critical metrics:

```python
# Example: Alert on high escalation rate
def check_escalation_threshold():
    escalations = metrics_service.get_escalation_stats(time_window_hours=1)
    
    if escalations['escalation_rate'] > 0.3:  # 30% threshold
        send_alert(
            severity="warning",
            message=f"High escalation rate: {escalations['escalation_rate']:.1%}",
            details=escalations
        )
```

### 4. Data Retention
Implement data retention policies:

```python
# In src/services/retention_service.py
from datetime import datetime, timedelta

def cleanup_old_metrics(days_to_keep: int = 90):
    cutoff = datetime.now(datetime.UTC) - timedelta(days=days_to_keep)
    
    # Remove old metrics
    metrics_service.l1_metrics = [
        m for m in metrics_service.l1_metrics 
        if m.timestamp >= cutoff
    ]
    # ... repeat for other metric types
    
    # Also delete old log files
    cleanup_old_logs(days_to_keep)
```

## Testing the Integration

### Unit Test Example

```python
# tests/test_metrics_integration.py
import pytest
from datetime import datetime
from src.services.metrics_service import get_metrics_service

def test_l1_metric_recording():
    metrics = get_metrics_service()
    
    # Record a metric
    metrics.record_l1_classification(
        session_id="test-123",
        intent_name="scheduling",
        confidence=0.92,
        caller_type="client",
        processing_time_ms=150.0
    )
    
    # Verify it was recorded
    assert len(metrics.l1_metrics) > 0
    last_metric = metrics.l1_metrics[-1]
    assert last_metric.session_id == "test-123"
    assert last_metric.intent_name == "scheduling"
    assert last_metric.confidence == 0.92

def test_metrics_dashboard():
    metrics = get_metrics_service()
    
    # Record some test data
    for i in range(10):
        metrics.record_l1_classification(
            session_id=f"test-{i}",
            intent_name="scheduling",
            confidence=0.8 + (i * 0.01),
            caller_type="client",
            processing_time_ms=100.0 + i
        )
    
    # Get dashboard
    dashboard = metrics.get_full_dashboard(time_window_hours=24)
    
    assert dashboard is not None
    assert "l1_classification" in dashboard
    assert "session_summary" in dashboard
```

### Integration Test Example

```python
# tests/test_full_workflow_metrics.py
import pytest
from src.workflow.ai_receptionist_workflow import run_workflow
from src.services.metrics_service import get_metrics_service

def test_full_workflow_records_metrics():
    metrics = get_metrics_service()
    initial_count = len(metrics.session_metrics)
    
    # Run workflow
    state = run_workflow(
        initial_message="I need to schedule a cleaning",
        session_id="integration-test-123"
    )
    
    # Verify session was recorded
    assert len(metrics.session_metrics) == initial_count + 1
    
    # Verify L1 classification was recorded
    l1_metrics = [m for m in metrics.l1_metrics if m.session_id == "integration-test-123"]
    assert len(l1_metrics) > 0
    
    # Verify routing was recorded
    routing_metrics = [m for m in metrics.routing_metrics if m.session_id == "integration-test-123"]
    assert len(routing_metrics) > 0
```

## Troubleshooting

### Issue: Metrics not appearing in dashboard
**Solution**: Check that:
1. Metrics are being recorded in your nodes
2. FastAPI server is running
3. Analytics endpoints are properly registered
4. Time window includes your test data

### Issue: Logs not being written
**Solution**: Check that:
1. `logs/` directory exists and is writable
2. LoggingService is initialized with correct path
3. Minimum log level allows your messages through

### Issue: Dashboard shows "No data available"
**Solution**: 
1. Generate some test traffic through your workflow
2. Verify metrics are in memory: `print(len(metrics_service.l1_metrics))`
3. Check browser console for API errors

## Next Steps

1. **Complete Phase 8 checklist items** (☐ 8.1, 8.2, 8.3)
2. **Integrate metrics/logging into existing nodes**
3. **Test with real workflow execution**
4. **Set up production storage** (Redis/MongoDB)
5. **Configure alerting** for critical metrics
6. **Move to Phase 9**: Testing & Validation

## Summary

You now have:
✅ Comprehensive metrics tracking for all tiers
✅ Structured JSON logging with full context
✅ REST API for querying metrics
✅ Web dashboard for visualization
✅ Integration examples for all workflow stages

The telemetry system is production-ready with in-memory storage for development, and can be easily extended to use Redis, MongoDB, or TimescaleDB for production deployments.