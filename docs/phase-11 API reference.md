# API Reference

Complete API documentation for the AI Receptionist System.

**Base URL**: `http://localhost:8000` (development)  
**API Version**: 2.0  
**Authentication**: None (add as needed for production)

---

## Table of Contents

1. [Call Processing API](#call-processing-api)
2. [Session Management API](#session-management-api)
3. [Analytics API](#analytics-api)
4. [Health & Status API](#health--status-api)
5. [Data Models](#data-models)
6. [Error Responses](#error-responses)
7. [Rate Limiting](#rate-limiting)

---

## Call Processing API

### POST /call

Process an incoming call with speech-to-text transcription.

**Request Body**:

```json
{
    "caller_phone": "string (required)",
    "speech_text": "string (required)",
    "call_sid": "string (required)",
    "session_id": "string (optional)"
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `caller_phone` | string | Yes | Caller's phone number in E.164 format (e.g., `+14155551234`) |
| `speech_text` | string | Yes | Transcribed speech from the caller |
| `call_sid` | string | Yes | Unique call identifier from telephony provider |
| `session_id` | string | No | Session ID to continue existing conversation. Auto-generated if not provided. |

**Response** (200 OK):

```json
{
    "response_text": "string",
    "session_id": "string",
    "intent": "string",
    "confidence": "number",
    "requires_clarification": "boolean",
    "missing_slots": "array of strings",
    "current_tier": "string",
    "processing_time_ms": "number",
    "routing_history": "array of objects",
    "action_result": "object (optional)",
    "next_steps": "array of strings (optional)"
}
```

**Response Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `response_text` | string | Text response to speak back to caller |
| `session_id` | string | Session ID for conversation continuity |
| `intent` | string | Identified intent (L1 or L2 level) |
| `confidence` | number | Confidence score (0.0-1.0) |
| `requires_clarification` | boolean | Whether clarification is needed |
| `missing_slots` | array | List of missing required information |
| `current_tier` | string | Current tier: "L1", "L2", or "L3" |
| `processing_time_ms` | number | Total processing time in milliseconds |
| `routing_history` | array | List of routing decisions made |
| `action_result` | object | Result from L3 action execution (if reached L3) |
| `next_steps` | array | Recommended next actions for user |

**Example Request**:

```bash
curl -X POST http://localhost:8000/call \
  -H "Content-Type: application/json" \
  -d '{
    "caller_phone": "+14155551234",
    "speech_text": "I want to schedule a cleaning for next Tuesday",
    "call_sid": "CA1234567890"
  }'
```

**Example Response** (First Turn - L2 Clarification):

```json
{
    "response_text": "I'd be happy to help you schedule a cleaning! Could you please provide the address and your contact number?",
    "session_id": "sess_abc123xyz",
    "intent": "book_service",
    "confidence": 0.92,
    "requires_clarification": true,
    "missing_slots": ["address", "contact_number"],
    "current_tier": "L2",
    "processing_time_ms": 245,
    "routing_history": [
        {
            "from_tier": "L1",
            "to_tier": "L2",
            "agent": "client_receptionist_l2",
            "confidence": 0.92,
            "timestamp": "2025-10-01T10:00:01Z",
            "reason": "High confidence scheduling intent for existing client"
        }
    ]
}
```

**Example Request** (Second Turn - Continuing Session):

```bash
curl -X POST http://localhost:8000/call \
  -H "Content-Type: application/json" \
  -d '{
    "caller_phone": "+14155551234",
    "speech_text": "123 Main St, Minneapolis. My number is 555-1234",
    "call_sid": "CA1234567890",
    "session_id": "sess_abc123xyz"
  }'
```

**Example Response** (Second Turn - L3 Action Completed):

```json
{
    "response_text": "Perfect! I've scheduled your house cleaning for Tuesday, October 10th at 2:00 PM at 123 Main St, Minneapolis. You'll receive a confirmation email shortly at the email we have on file.",
    "session_id": "sess_abc123xyz",
    "intent": "book_house_cleaning",
    "confidence": 0.98,
    "requires_clarification": false,
    "missing_slots": [],
    "current_tier": "L3",
    "processing_time_ms": 1850,
    "routing_history": [
        {
            "from_tier": "L1",
            "to_tier": "L2",
            "agent": "client_receptionist_l2",
            "confidence": 0.92,
            "timestamp": "2025-10-01T10:00:01Z",
            "reason": "High confidence scheduling intent"
        },
        {
            "from_tier": "L2",
            "to_tier": "L3",
            "agent": "sales_agent_l3",
            "confidence": 0.98,
            "timestamp": "2025-10-01T10:01:32Z",
            "reason": "All required slots filled"
        }
    ],
    "action_result": {
        "booking_id": "book_67890",
        "status": "confirmed",
        "scheduled_date": "2025-10-10T14:00:00Z",
        "service_type": "house_cleaning",
        "address": "123 Main St, Minneapolis, MN",
        "price": 150.00,
        "confirmation_sent": true
    },
    "next_steps": [
        "Check your email for booking confirmation",
        "Our team will arrive within 15 minutes of scheduled time",
        "Call (555) 555-5555 to reschedule or cancel"
    ]
}
```

**Error Responses**:

- `400 Bad Request`: Invalid request format
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: System overload or maintenance

---

## Session Management API

### GET /analytics/sessions/{session_id}

Retrieve detailed information about a specific session.

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session identifier |

**Response** (200 OK):

```json
{
    "session_id": "string",
    "caller_phone": "string",
    "caller_type": "string",
    "current_tier": "string",
    "conversation_history": "array",
    "routing_history": "array",
    "entities": "object",
    "created_at": "string (ISO datetime)",
    "updated_at": "string (ISO datetime)",
    "expires_at": "string (ISO datetime)",
    "status": "string"
}
```

**Example Request**:

```bash
curl http://localhost:8000/analytics/sessions/sess_abc123xyz
```

**Example Response**:

```json
{
    "session_id": "sess_abc123xyz",
    "caller_phone": "+14155551234",
    "caller_type": "client",
    "current_tier": "L3",
    "conversation_history": [
        {
            "role": "user",
            "text": "I want to schedule a cleaning for next Tuesday",
            "timestamp": "2025-10-01T10:00:00Z"
        },
        {
            "role": "agent",
            "text": "Could you please provide the address and your contact number?",
            "timestamp": "2025-10-01T10:00:02Z"
        },
        {
            "role": "user",
            "text": "123 Main St, Minneapolis. My number is 555-1234",
            "timestamp": "2025-10-01T10:01:30Z"
        },
        {
            "role": "agent",
            "text": "Perfect! I've scheduled your house cleaning...",
            "timestamp": "2025-10-01T10:01:34Z"
        }
    ],
    "routing_history": [
        {
            "from_tier": "L1",
            "to_tier": "L2",
            "agent": "client_receptionist_l2",
            "confidence": 0.92,
            "timestamp": "2025-10-01T10:00:01Z"
        },
        {
            "from_tier": "L2",
            "to_tier": "L3",
            "agent": "sales_agent_l3",
            "confidence": 0.98,
            "timestamp": "2025-10-01T10:01:32Z"
        }
    ],
    "entities": {
        "service_type": "house_cleaning",
        "preferred_date": "2025-10-10T14:00:00Z",
        "address": "123 Main St, Minneapolis, MN",
        "contact_number": "(555) 123-4567"
    },
    "created_at": "2025-10-01T10:00:00Z",
    "updated_at": "2025-10-01T10:01:34Z",
    "expires_at": "2025-10-01T10:30:00Z",
    "status": "completed"
}
```

---

### GET /analytics/sessions

List all sessions (with pagination and filtering).

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 20 | Items per page (max: 100) |
| `caller_type` | string | - | Filter by caller type |
| `status` | string | - | Filter by status (active, completed, escalated) |
| `start_date` | string | - | Filter by start date (ISO format) |
| `end_date` | string | - | Filter by end date (ISO format) |

**Example Request**:

```bash
curl "http://localhost:8000/analytics/sessions?caller_type=client&limit=50"
```

**Example Response**:

```json
{
    "total": 245,
    "page": 1,
    "limit": 50,
    "sessions": [
        {
            "session_id": "sess_abc123",
            "caller_phone": "+14155551234",
            "caller_type": "client",
            "current_tier": "L3",
            "created_at": "2025-10-01T10:00:00Z",
            "status": "completed"
        },
        // ... more sessions
    ]
}
```

---

## Analytics API

### GET /analytics/dashboard

Get comprehensive analytics dashboard data.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_window_hours` | integer | 24 | Time window in hours |

**Response** (200 OK):

```json
{
    "time_window_hours": 24,
    "generated_at": "string (ISO datetime)",
    "l1_classification": {
        "total_classifications": "integer",
        "average_confidence": "number",
        "by_intent": {
            "scheduling": {
                "count": "integer",
                "avg_confidence": "number"
            },
            // ... more intents
        },
        "by_caller_type": {
            "client": "integer",
            "prospect": "integer",
            // ... more types
        }
    },
    "l2_refinement": {
        "total_refinements": "integer",
        "average_confidence": "number",
        "clarification_rate": "number",
        "avg_clarifications_per_session": "number",
        "most_common_missing_slots": "array"
    },
    "l3_actions": {
        "total_executions": "integer",
        "success_rate": "number",
        "by_action": {
            "create_booking": {
                "count": "integer",
                "success_count": "integer",
                "avg_processing_time_ms": "number"
            },
            // ... more actions
        },
        "by_agent": {
            "sales_agent_l3": {
                "count": "integer",
                "success_rate": "number"
            },
            // ... more agents
        }
    },
    "routing_performance": {
        "avg_total_time_ms": "number",
        "avg_l1_time_ms": "number",
        "avg_l2_time_ms": "number",
        "avg_l3_time_ms": "number",
        "routing_decisions": {
            "direct_to_l2": "integer",
            "clarification_needed": "integer",
            "escalated": "integer"
        }
    },
    "escalations": {
        "total_escalations": "integer",
        "escalation_rate": "number",
        "avg_clarifications_before_escalation": "number",
        "by_reason": {
            "low_confidence": "integer",
            "max_clarifications": "integer",
            "action_failed": "integer",
            "explicit_request": "integer"
        },
        "by_tier": {
            "L1": "integer",
            "L2": "integer",
            "L3": "integer"
        }
    }
}
```

**Example Request**:

```bash
curl "http://localhost:8000/analytics/dashboard?time_window_hours=168"
```

---

### GET /analytics/l1/accuracy

Get L1 classification accuracy metrics.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_window_hours` | integer | 24 | Time window in hours |

**Response** (200 OK):

```json
{
    "time_window_hours": 24,
    "total_classifications": 1250,
    "average_confidence": 0.87,
    "high_confidence_rate": 0.78,
    "medium_confidence_rate": 0.18,
    "low_confidence_rate": 0.04,
    "by_intent": {
        "scheduling": {
            "count": 450,
            "avg_confidence": 0.91,
            "high_confidence_count": 390
        },
        "billing": {
            "count": 200,
            "avg_confidence": 0.85,
            "high_confidence_count": 160
        },
        "support": {
            "count": 300,
            "avg_confidence": 0.82,
            "high_confidence_count": 230
        },
        "general": {
            "count": 300,
            "avg_confidence": 0.78,
            "high_confidence_count": 210
        }
    },
    "by_caller_type": {
        "client": {
            "count": 600,
            "avg_confidence": 0.92
        },
        "prospect": {
            "count": 400,
            "avg_confidence": 0.84
        },
        "partner": {
            "count": 150,
            "avg_confidence": 0.88
        },
        "unknown": {
            "count": 100,
            "avg_confidence": 0.65
        }
    }
}
```

**Example Request**:

```bash
curl "http://localhost:8000/analytics/l1/accuracy?time_window_hours=24"
```

---

### GET /analytics/l2/refinement

Get L2 intent refinement metrics.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_window_hours` | integer | 24 | Time window in hours |

**Response** (200 OK):

```json
{
    "time_window_hours": 24,
    "total_refinements": 980,
    "average_confidence": 0.91,
    "clarification_rate": 0.35,
    "avg_clarifications_per_session": 0.8,
    "most_common_missing_slots": [
        {"slot": "address", "count": 250},
        {"slot": "preferred_date", "count": 180},
        {"slot": "contact_number", "count": 150},
        {"slot": "service_type", "count": 80}
    ],
    "by_l2_agent": {
        "client_receptionist_l2": {
            "count": 550,
            "avg_confidence": 0.93,
            "clarification_rate": 0.30
        },
        "prospect_receptionist_l2": {
            "count": 300,
            "avg_confidence": 0.88,
            "clarification_rate": 0.45
        },
        "partner_receptionist_l2": {
            "count": 80,
            "avg_confidence": 0.92,
            "clarification_rate": 0.25
        },
        "general_receptionist_l2": {
            "count": 50,
            "avg_confidence": 0.75,
            "clarification_rate": 0.60
        }
    }
}
```

---

### GET /analytics/l3/actions

Get L3 action execution metrics.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_window_hours` | integer | 24 | Time window in hours |

**Response** (200 OK):

```json
{
    "time_window_hours": 24,
    "total_executions": 637,
    "success_rate": 0.94,
    "avg_processing_time_ms": 1650,
    "by_action": {
        "create_booking": {
            "count": 250,
            "success_count": 240,
            "success_rate": 0.96,
            "avg_processing_time_ms": 1800
        },
        "reschedule_booking": {
            "count": 100,
            "success_count": 95,
            "success_rate": 0.95,
            "avg_processing_time_ms": 1500
        },
        "create_ticket": {
            "count": 150,
            "success_count": 148,
            "success_rate": 0.99,
            "avg_processing_time_ms": 1200
        },
        "generate_invoice": {
            "count": 80,
            "success_count": 75,
            "success_rate": 0.94,
            "avg_processing_time_ms": 2000
        },
        "provide_info": {
            "count": 57,
            "success_count": 57,
            "success_rate": 1.00,
            "avg_processing_time_ms": 800
        }
    },
    "by_agent": {
        "sales_agent_l3": {
            "count": 350,
            "success_rate": 0.95,
            "avg_processing_time_ms": 1750
        },
        "support_agent_l3": {
            "count": 150,
            "success_rate": 0.99,
            "avg_processing_time_ms": 1200
        },
        "billing_agent_l3": {
            "count": 80,
            "success_rate": 0.94,
            "avg_processing_time_ms": 2000
        },
        "scheduling_agent_l3": {
            "count": 50,
            "success_rate": 0.96,
            "avg_processing_time_ms": 1500
        },
        "general_agent_l3": {
            "count": 7,
            "success_rate": 1.00,
            "avg_processing_time_ms": 800
        }
    },
    "failure_reasons": {
        "validation_failed": 15,
        "database_error": 8,
        "external_api_error": 12,
        "timeout": 3
    }
}
```

---

### GET /analytics/escalations

Get escalation statistics.

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_window_hours` | integer | 24 | Time window in hours |

**Response** (200 OK):

```json
{
    "time_window_hours": 24,
    "total_escalations": 98,
    "escalation_rate": 0.078,
    "avg_clarifications_before_escalation": 1.8,
    "by_reason": {
        "low_confidence": 25,
        "max_clarifications_reached": 40,
        "action_failed": 18,
        "explicit_request": 10,
        "timeout": 5
    },
    "by_tier": {
        "L1": 25,
        "L2": 55,
        "L3": 18
    },
    "by_caller_type": {
        "client": 30,
        "prospect": 45,
        "partner": 8,
        "unknown": 15
    },
    "avg_resolution_time_minutes": 35,
    "open_tickets": 12,
    "resolved_tickets": 86
}
```

---

### GET /analytics/export/csv

Export metrics as CSV file.

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metric_type` | string | Yes | Type: `sessions`, `l1`, `l2`, `l3`, `escalations` |
| `time_window_hours` | integer | No | Time window (default: 24) |

**Response**: CSV file download

**Example Request**:

```bash
curl "http://localhost:8000/analytics/export/csv?metric_type=sessions&time_window_hours=168" \
  -o sessions_export.csv
```

---

## Health & Status API

### GET /health

Get system health status.

**Response** (200 OK):

```json
{
    "status": "healthy",
    "timestamp": "2025-10-01T10:00:00Z",
    "version": "2.0.0",
    "uptime_seconds": 86400,
    "components": {
        "database": {
            "status": "connected",
            "latency_ms": 15
        },
        "session_service": {
            "status": "active",
            "active_sessions": 234
        },
        "workflow": {
            "status": "operational",
            "queued_requests": 0
        }
    }
}
```

**Status Values**:
- `healthy`: All systems operational
- `degraded`: Some components experiencing issues
- `unhealthy`: Critical failure

**Example Request**:

```bash
curl http://localhost:8000/health
```

---

### GET /metrics

Get Prometheus-format metrics (optional).

**Response**: Plain text Prometheus metrics

**Example Response**:

```
# HELP ai_receptionist_requests_total Total number of requests
# TYPE ai_receptionist_requests_total counter
ai_receptionist_requests_total{tier="l1"} 1250
ai_receptionist_requests_total{tier="l2"} 980
ai_receptionist_requests_total{tier="l3"} 637

# HELP ai_receptionist_processing_time_seconds Processing time distribution
# TYPE ai_receptionist_processing_time_seconds histogram
ai_receptionist_processing_time_seconds_bucket{tier="l1",le="0.1"} 850
ai_receptionist_processing_time_seconds_bucket{tier="l1",le="0.2"} 1200
ai_receptionist_processing_time_seconds_bucket{tier="l1",le="+Inf"} 1250
```

---

## Data Models

### WorkflowState

Complete workflow state passed between tiers.

```python
{
    "session_id": "string",
    "user_id": "string | null",
    "raw_prompt": "string",
    "caller_phone": "string",
    "caller_type": "client | prospect | partner | unknown",
    "intent_l1": {
        "name": "string",
        "confidence": "number (0.0-1.0)"
    },
    "intent_l2": {
        "name": "string",
        "confidence": "number (0.0-1.0)"
    },
    "entities": {
        "key": "value"  // Extracted entities
    },
    "required_slots": ["string"],
    "missing_slots": ["string"],
    "routing_confidence": "number",
    "routing_history": [
        {
            "from_tier": "string",
            "to_tier": "string",
            "agent": "string",
            "confidence": "number",
            "timestamp": "string (ISO datetime)",
            "reason": "string"
        }
    ],
    "current_tier": "L1 | L2 | L3",
    "clarification_count": "integer",
    "max_clarifications": "integer",
    "awaiting_clarification": "boolean",
    "clarification_question": "string | null",
    "requires_human_escalation": "boolean",
    "escalation_reason": "string | null",
    "ticket_id": "string | null",
    "action_result": "object | null",
    "action_success": "boolean",
    "confirmation_message": "string | null",
    "next_steps": ["string"],
    "previous_messages": [
        {
            "role": "user | agent",
            "text": "string",
            "timestamp": "string (ISO datetime)"
        }
    ],
    "processing_start_time": "string (ISO datetime)",
    "processing_end_time": "string (ISO datetime)",
    "total_processing_time_ms": "number"
}
```

---

### CallerType Enum

```
client     - Existing customer
prospect   - Potential new customer
partner    - Vendor or partner
unknown    - Unable to identify
```

---

### Intent Enum (L1)

```
scheduling        - Booking or scheduling related
billing          - Payment or invoice related
support          - Service issue or complaint
technical_issue  - Technical problem
general          - General inquiry
```

---

### Tier Enum

```
L1  - Receptionist (broad classification)
L2  - Intent Refiner (slot extraction)
L3  - Domain Specialist (action execution)
```

---

## Error Responses

### Standard Error Format

```json
{
    "error": {
        "code": "string",
        "message": "string",
        "details": "object | null",
        "timestamp": "string (ISO datetime)"
    }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request |
| `VALIDATION_ERROR` | 422 | Invalid field values |
| `SESSION_NOT_FOUND` | 404 | Session doesn't exist |
| `SESSION_EXPIRED` | 410 | Session has expired |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | System overload |
| `DATABASE_ERROR` | 503 | Database connection issue |

### Example Error Response

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid phone number format",
        "details": {
            "field": "caller_phone",
            "provided": "555-1234",
            "expected": "E.164 format (e.g., +14155551234)"
        },
        "timestamp": "2025-10-01T10:00:00Z"
    }
}
```

---

## Rate Limiting

**Default Limits**:
- **Per IP**: 100 requests per minute
- **Per Session**: 20 requests per minute
- **Analytics**: 60 requests per minute

**Rate Limit Headers**:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1633046400
```

**429 Response**:

```json
{
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Rate limit exceeded. Please try again later.",
        "details": {
            "retry_after_seconds": 42
        },
        "timestamp": "2025-10-01T10:00:00Z"
    }
}
```

---

## Authentication (Production)

**Recommended**: Add API key authentication for production.

**Request Header**:

```
Authorization: Bearer YOUR_API_KEY
```

**Example**:

```bash
curl -X POST http://localhost:8000/call \
  -H "Authorization: Bearer sk_live_abc123xyz" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

## Webhooks (Future)

Support for webhook notifications on specific events.

**Events**:
- `session.created`
- `session.completed`
- `session.escalated`
- `booking.created`
- `ticket.created`

**Webhook Payload Example**:

```json
{
    "event": "booking.created",
    "timestamp": "2025-10-01T10:00:00Z",
    "data": {
        "booking_id": "book_67890",
        "session_id": "sess_abc123",
        "caller_phone": "+14155551234",
        "scheduled_date": "2025-10-10T14:00:00Z",
        "service_type": "house_cleaning"
    }
}
```

---

**API Version**: 2.0  
**Last Updated**: October 2025  
**Contact**: dev@example.com