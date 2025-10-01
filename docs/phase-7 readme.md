# Phase 7: Session Management Implementation Guide

## Overview

Phase 7 adds comprehensive session management to support multi-turn conversations in the 3-tier agentic routing system. This enables:

- **Persistent state** across multiple conversation turns
- **Conversation history** tracking for context-aware responses
- **Automatic session expiration** to manage resources
- **Session analytics** for monitoring and debugging

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
│  /process-call  /sessions/{id}  /sessions  /stats          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  SessionService                             │
│  • Create/Load/Save sessions                                │
│  • Manage conversation history                              │
│  • Handle expiration & cleanup                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  DatabaseService                            │
│  MongoDB Collections:                                       │
│  • sessions - State persistence                             │
│  • routing_logs - Decision tracking                         │
│  • escalation_tickets - Human handoffs                      │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. SessionService (`src/services/session_service.py`)

Main service for session management.

**Key Methods:**
- `create_session()` - Initialize new session with state
- `save_state()` - Persist workflow state to database
- `load_state()` - Retrieve workflow state from database
- `append_message()` - Add message to conversation history
- `cleanup_expired_sessions()` - Remove old sessions
- `get_session_info()` - Analytics and debugging
- `export_conversation()` - Full transcript export

**Configuration:**
```python
session_service = SessionService(
    db_service=db_service,
    default_ttl_minutes=30,        # Session lifetime
    max_conversation_history=10    # Max messages to keep
)
```

### 2. Updated API Endpoints (`main.py`)

#### POST `/process-call`
Process a call with session support.

**Request:**
```json
{
  "caller_phone": "555-123-4567",
  "speech_text": "I need to schedule a cleaning",
  "call_sid": "CA1234567890",
  "session_id": "sess-20251001-abc123"  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "sess-20251001-abc123",
  "caller_type": "client",
  "intent": "scheduling",
  "response": "I'd be happy to help schedule a cleaning...",
  "current_tier": "L2",
  "turn_count": 2,
  "requires_escalation": false
}
```

#### GET `/sessions/{session_id}`
Get session information and history.

**Response:**
```json
{
  "session_id": "sess-20251001-abc123",
  "created_at": "2025-10-01T10:00:00Z",
  "current_tier": "L2",
  "turn_count": 3,
  "caller_type": "client",
  "conversation_turns": 6,
  "routing_path": ["START→L1", "L1→L2"],
  "requires_escalation": false
}
```

#### GET `/sessions`
List recent active sessions.

**Query Parameters:**
- `caller_phone` (optional) - Filter by phone number
- `limit` (default: 10) - Max results

#### GET `/sessions/{session_id}/export`
Export full conversation transcript.

**Query Parameters:**
- `include_metadata` (default: true) - Include routing/state data

#### DELETE `/sessions/{session_id}`
Delete a session.

#### POST `/sessions/cleanup`
Manually trigger expired session cleanup.

### 3. Database Models

#### SessionState Collection
```javascript
{
  "session_id": "sess-20251001-abc123",
  "state_data": {
    // Complete WorkflowState as dict
    "caller_phone": "555-123-4567",
    "current_tier": "L2",
    "turn_count": 3,
    "conversation_history": [...],
    "entities": {...}
  },
  "created_at": ISODate("2025-10-01T10:00:00Z"),
  "updated_at": ISODate("2025-10-01T10:15:00Z"),
  "expires_at": ISODate("2025-10-01T10:30:00Z"),
  "caller_phone": "555-123-4567",  // For indexing
  "current_tier": "L2"              // For indexing
}
```

**Indexes:**
- `session_id` (unique)
- `created_at`
- `expires_at` (for TTL cleanup)

#### RoutingLog Collection
```javascript
{
  "session_id": "sess-20251001-abc123",
  "from_tier": "L1",
  "to_tier": "L2",
  "reason": "High confidence classification",
  "confidence": 0.92,
  "timestamp": ISODate("2025-10-01T10:00:05Z"),
  "metadata": {
    "intent": "scheduling",
    "caller