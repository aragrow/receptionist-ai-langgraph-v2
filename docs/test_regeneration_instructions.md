Recommended Test Plan for AI Receptionist App
This document outlines the comprehensive set of tests to ensure reliability, correctness, and security whenever changes are made to the codebase.

1. Unit Tests (Lowest-level, fast run)
Validate individual classes, models, and services in isolation.

Models (src/models)
WorkflowState model
Default initialization of state fields.
Serialization and deserialization to dict.
Invalid type handling (e.g., passing string where enum required).
Database models (Client, Vendor, etc.)
Required/optional field validation.
ObjectId / _id handling and custom serializers.
Escaping/sanitization of notes and addresses.
Utilities (src/utilities)
phone_utils
Normalize phone numbers with/without +1.
Reject malformed phone formats.
text_processing
Stop word removal.
Chunking of text >1000 tokens with 100-token overlap.
Graceful handling of empty or very short text.
Services
DatabaseService
Connection success and failure scenarios.
CRUD operations with mock Mongo.
Auto-creation of collections when missing.
EmbeddingService
Successful embedding generation (mocked Google API).
Fallback to zero vector when embedding API fails.
Chunking + embedding of large text bodies.
ContextService
Client context aggregation (client + properties + jobs + visits).
Vendor context aggregation (vendor + jobs + visits).
Lead context returns only KB info.
Access restrictions filter forbidden fields.
2. Node/Workflow Layer (src/nodes)
Test each workflow node in isolation.

IdentityChecker
Known client phone → CallerType.CLIENT.
Known vendor phone → CallerType.VENDOR.
Unknown phone → CallerType.LEAD.
IntentAnalyzer
“What’s my job status?” → Intent.STATUS_CHECK.
“I want cleaning service” → Intent.SERVICE_INQUIRY.
Unknown phrasing → Intent.GENERIC.
ContextBuilder
Client context includes only their own jobs.
Vendor context excludes unrelated client jobs.
Lead context restricted to general KB entries.
ResponseGenerator
Generates meaningful text response.
Enforces access control (no data leakage).
Embeds context correctly into LLM prompt.
3. Integration Tests
Combine multiple modules to validate workflows.

Database + Embedding pipeline
Insert client/job → verify KB entry with embedding exists.
Process call end-to-end (mock LLM)
Client call → returns personalized response.
Vendor call → returns vendor-focused response.
Lead call → returns general KB info only.
Twilio webhook simulation
Simulated call event JSON → processed → generates appropriate Twilio TTS response.
4. Access Control Tests
Critical to enforce data protection rules.

Client restrictions
Clients only retrieve their properties, jobs, visits.
Attempt to access another client’s job → denied/filtered.
Vendor restrictions
Vendors only retrieve their assigned jobs.
Vendors cannot view unrelated clients.
Lead restrictions
Leads cannot see private data.
System role
System/AI has full access (internal use only).
5. Performance & Reliability Tests
EmbeddingService handles large text bodies (10k+ tokens, chunked).
Workflow latency < X ms for standard calls.
Database concurrency test: multiple simultaneous calls succeed without conflict.
Embedding API failures trigger retries/backoff gracefully.
6. Regression & Scenario Tests
End-to-End Conversation Flows
Client asks status → job status pulled from DB + summarized.
Vendor updates/reschedules job → workflow reflects new state.
Lead makes service inquiry → responds with general info only.
Malicious Input Handling
SQL/JS injection attempts → sanitized safely.
Overly long inputs (>50k chars) truncated gracefully.
Failover Scenarios
DB outage → workflow exits gracefully with error handling.
Embedding API error → workflow falls back to non-embedded text.