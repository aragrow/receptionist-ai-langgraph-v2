# Compliance & Data Privacy Documentation

## Overview

This system implements comprehensive GDPR and CCPA compliance features to protect user privacy and meet regulatory requirements.

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [Configuration](#configuration)
5. [Automated Tasks](#automated-tasks)
6. [User Rights](#user-rights)
7. [Audit Trail](#audit-trail)
8. [Best Practices](#best-practices)

---

## Features

### 1. PII Masking
Automatically detects and masks Personally Identifiable Information (PII) in logs and outputs:
- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- Physical addresses
- IP addresses
- Dates of birth

### 2. Consent Management
Track user consent for various data processing activities:
- Data processing consent
- Marketing consent
- Analytics consent
- Third-party sharing consent
- Call recording consent

### 3. Data Retention
Configurable retention policies with automatic deletion:
- Sessions: 30 days (default)
- Conversation logs: 90 days (default)
- Tickets: 365 days (default)
- Metrics: 180 days (default)
- Audit logs: 730 days (default)

### 4. User Rights (GDPR/CCPA)
- **Right to Access**: Export all user data
- **Right to Erasure**: Delete all user data ("Right to be Forgotten")
- **Right to Data Portability**: Download data in machine-readable format
- **Right to Withdraw Consent**: Remove previously granted consent

### 5. Audit Trail
Complete audit log of all data access and processing activities.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Application                │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────────┐      ┌────────────────────┐  │
│  │  PII Masking     │      │  Compliance        │  │
│  │  Utility         │◄─────┤  Service           │  │
│  └──────────────────┘      └────────────────────┘  │
│                                      ▲               │
│  ┌──────────────────┐               │               │
│  │  Retention       │               │               │
│  │  Service         │───────────────┘               │
│  └──────────────────┘                               │
│           ▲                                          │
│           │                                          │
│  ┌────────┴─────────┐                               │
│  │  Retention       │                               │
│  │  Scheduler       │                               │
│  └──────────────────┘                               │
│                                                       │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  MongoDB    │
                  └─────────────┘
```

---

## API Endpoints

### Consent Management

#### Record Consent
```http
POST /api/compliance/consent
Content-Type: application/json

{
  "user_id": "user_123",
  "consent_type": "data_processing",
  "granted": true,
  "metadata": {
    "source": "web_form",
    "version": "1.0"
  }
}
```

#### Withdraw Consent
```http
POST /api/compliance/consent/withdraw
Content-Type: application/json

{
  "user_id": "user_123",
  "consent_type": "marketing"
}
```

#### Get User Consents
```http
GET /api/compliance/consent/{user_id}
```

### Data Access Requests

#### Create Data Request
```http
POST /api/compliance/data-request
Content-Type: application/json

{
  "user_id": "user_123",
  "email": "user@example.com",
  "request_type": "access"  // or "deletion"
}
```

#### Verify Data Request
```http
POST /api/compliance/data-request/verify
Content-Type: application/json

{
  "request_id": "DAR-ABC123DEF456",
  "verification_token": "token_from_email"
}
```

#### Check Request Status
```http
GET /api/compliance/data-request/{request_id}
```

### Data Export

#### Export User Data
```http
GET /api/compliance/export/{user_id}
```

Response includes:
- All sessions
- All conversation logs
- All tickets
- All consents
- All data requests

### Data Deletion

#### Delete User Data
```http
POST /api/compliance/delete-user-data
Content-Type: application/json

{
  "user_id": "user_123",
  "confirmation": "DELETE",
  "reason": "User request per GDPR Article 17"
}
```

⚠️ **WARNING**: This permanently deletes all user data and cannot be undone.

### Audit Logs

#### Get Audit Logs
```http
GET /api/compliance/audit-logs?user_id=user_123&limit=100
```

Query parameters:
- `user_id`: Filter by user
- `event_type`: Filter by event type
- `start_date`: Filter by start date (ISO 8601)
- `end_date`: Filter by end date (ISO 8601)
- `limit`: Maximum results (default: 100)

### Compliance Reporting

#### Generate Report
```http
POST /api/compliance/report
Content-Type: application/json

{
  "start_date": "2025-09-01T00:00:00Z",
  "end_date": "2025-09-30T23:59:59Z"
}
```

### Retention Management

#### Get Retention Stats
```http
GET /api/compliance/retention/stats
```

#### Get Retention Policies
```http
GET /api/compliance/retention/policies
```

#### Update Retention Policy
```http
PUT /api/compliance/retention/policy
Content-Type: application/json

{
  "data_type": "session",
  "retention_days": 45,
  "archive_before_delete": true,
  "archive_location": "s3://my-bucket/archives/",
  "enabled": true
}
```

#### Run Cleanup
```http
POST /api/compliance/retention/cleanup?dry_run=true
```

---

## Configuration

### Environment Variables

```bash
# Compliance Settings
COMPLIANCE_ENABLED=true
RETENTION_ENABLED=true
DEFAULT_RETENTION_DAYS=90

# Scheduler Settings
SCHEDULER_ENABLED=true
CLEANUP_HOUR=2  # Hour to run daily cleanup (0-23)

# Archiving (optional)
ARCHIVE_ENABLED=false
ARCHIVE_LOCATION=s3://retention-archives/

# PII Masking
PII_MASKING_ENABLED=true
MASK_LOGS=true
```

### Retention Policy Configuration

Edit policies in MongoDB or via API:

```python
from src.services.retention_service import RetentionService, RetentionPolicy, DataType

retention_service = RetentionService(mongo_client)

# Update session retention to 45 days
policy = RetentionPolicy(
    data_type=DataType.SESSION,
    retention_days=45,
    archive_before_delete=False,
    enabled=True
)

retention_service.update_retention_policy(policy)
```

---

## Automated Tasks

The system runs automated tasks via `APScheduler`:

### Daily Retention Cleanup
- **Schedule**: Every day at 2:00 AM
- **Action**: Deletes data older than retention period
- **Job ID**: `retention_cleanup`

### Hourly Data Request Processing
- **Schedule**: Every hour at :00
- **Action**: Processes verified data access/deletion requests
- **Job ID**: `process_data_requests`

### Weekly Compliance Report
- **Schedule**: Every Monday at 9:00 AM
- **Action**: Generates compliance metrics report
- **Job ID**: `weekly_compliance_report`

### Daily Retention Stats
- **Schedule**: Every day at 12:00 PM
- **Action**: Logs statistics about data eligible for deletion
- **Job ID**: `retention_stats`

### Starting the Scheduler

```python
from src.services.retention_scheduler import initialize_scheduler
from src.services.retention_service import RetentionService
from src.services.compliance_service import ComplianceService

# Initialize services
retention_service = RetentionService(mongo_client)
compliance_service = ComplianceService(mongo_client)

# Start scheduler
scheduler = initialize_scheduler(
    retention_service=retention_service,
    compliance_service=compliance_service,
    enabled=True
)
```

---

## User Rights

### GDPR Compliance

#### Article 7: Right to Consent
Users can grant and withdraw consent for data processing activities.

**Implementation**: `/api/compliance/consent` endpoints

#### Article 15: Right to Access
Users can request a copy of all their personal data.

**Implementation**: `/api/compliance/data-request` with `request_type: "access"`

#### Article 17: Right to Erasure (Right to be Forgotten)
Users can request deletion of all their personal data.

**Implementation**: `/api/compliance/data-request` with `request_type: "deletion"`

#### Article 20: Right to Data Portability
Users can download their data in a machine-readable format (JSON).

**Implementation**: `/api/compliance/export/{user_id}`

#### Article 30: Records of Processing Activities
System maintains audit logs of all data processing activities.

**Implementation**: Automatic audit logging in `ComplianceService`

### CCPA Compliance

#### Right to Know
Consumers can request information about personal data collected.

**Implementation**: Same as GDPR Article 15

#### Right to Delete
Consumers can request deletion of their personal data.

**Implementation**: Same as GDPR Article 17

#### Right to Opt-Out
Consumers can opt out of data sharing with third parties.

**Implementation**: Consent withdrawal via `/api/compliance/consent/withdraw`

---

## Audit Trail

Every compliance-related action is logged with:

- **Event Type**: Type of action (consent_recorded, data_accessed, etc.)
- **User ID**: Subject of the action
- **Actor ID**: Who performed the action
- **Timestamp**: When the action occurred
- **IP Address**: Source IP address
- **User Agent**: Browser/client information
- **Details**: Additional context about the action

### Event Types

- `consent_recorded` - User granted or denied consent
- `consent_withdrawn` - User withdrew consent
- `data_access_request_created` - Data access/deletion request created
- `data_exported` - User data exported
- `user_data_deleted` - User data permanently deleted
- `data_retention_cleanup` - Automatic retention cleanup ran
- `retention_policy_updated` - Retention policy changed

### Accessing Audit Logs

```python
from src.services.compliance_service import ComplianceService

compliance_service = ComplianceService(mongo_client)

# Get logs for specific user
logs = compliance_service.get_audit_logs(
    user_id="user_123",
    limit=50
)

# Get logs for specific event type
logs = compliance_service.get_audit_logs(
    event_type="data_exported",
    start_date=datetime(2025, 9, 1),
    end_date=datetime(2025, 9, 30)
)
```

---

## Best Practices

### 1. PII Protection

**Always mask PII before logging:**

```python
from src.utilities.pii_masking import sanitize_for_logging

# Bad
logger.info(f"User email: {user_email}")

# Good
logger.info(f"User email: {sanitize_for_logging(user_email)}")

# For dictionaries
user_data = {"name": "John", "email": "john@example.com"}
logger.info(sanitize_for_logging(user_data))
```

**Check for PII before storing:**

```python
from src.utilities.pii_masking import has_pii, detect_pii

text = "Contact me at john@example.com"

if has_pii(text):
    detected = detect_pii(text)
    logger.warning(f"PII detected: {list(detected.keys())}")
```

### 2. Consent Management

**Always check consent before processing:**

```python
if not compliance_service.has_consent(user_id, ConsentType.DATA_PROCESSING):
    raise HTTPException(
        status_code=403,
        detail="User has not granted data processing consent"
    )
```

**Record consent with context:**

```python
compliance_service.record_consent(
    user_id=user_id,
    consent_type=ConsentType.MARKETING,
    granted=True,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    metadata={
        "source": "signup_form",
        "version": "2.0",
        "timestamp": datetime.now(UTC).isoformat()
    }
)
```

### 3. Data Retention

**Set appropriate retention periods:**

- **Sessions**: 30 days (short-term interaction data)
- **Conversation Logs**: 90 days (training and quality purposes)
- **Tickets**: 365 days (customer service records)
- **Audit Logs**: 730 days (2 years for compliance)

**Archive before deletion:**

Enable archiving for important data types:

```python
policy = RetentionPolicy(
    data_type=DataType.CONVERSATION_LOG,
    retention_days=90,
    archive_before_delete=True,
    archive_location="s3://my-bucket/archives/conversations/"
)
```

### 4. Data Deletion

**Use soft deletes for critical data:**

Instead of immediate deletion, mark records as deleted and delete later:

```python
# Soft delete
session_collection.update_one(
    {"session_id": session_id},
    {"$set": {"deleted": True, "deleted_at": datetime.now(UTC)}}
)

# Hard delete later during retention cleanup
```

**Always log deletions:**

```python
compliance_service._log_audit(
    event_type="data_deleted",
    user_id=user_id,
    action="delete_session",
    details={"session_id": session_id, "reason": reason}
)
```

### 5. Data Export

**Sanitize exports before sending:**

```python
user_data = compliance_service.export_user_data(user_id)

# Remove internal fields
for collection in user_data.values():
    if isinstance(collection, list):
        for item in collection:
            item.pop("_id", None)
            item.pop("internal_notes", None)
```

**Secure export URLs:**

- Use signed URLs with expiration (24-48 hours)
- Require authentication to download
- Log all download attempts

### 6. Security

**Protect sensitive endpoints:**

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@router.post("/delete-user-data")
async def delete_user_data(
    delete_req: UserDataDeleteRequest,
    credentials: str = Depends(security)
):
    # Verify admin/user permissions
    if not verify_admin_token(credentials):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Proceed with deletion
    ...
```

**Rate limit sensitive operations:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/data-request")
@limiter.limit("5/hour")  # Max 5 requests per hour
async def create_data_request(...):
    ...
```

### 7. Monitoring

**Set up alerts for:**

- Failed retention cleanups
- Unprocessed data requests (> 24 hours old)
- High volume of data deletion requests
- Audit log anomalies

**Monitor metrics:**

```python
# Track compliance metrics
metrics = {
    "active_consents": consent_collection.count_documents({"status": "granted"}),
    "pending_requests": data_requests_collection.count_documents({"status": "pending"}),
    "retention_eligible": retention_service.get_retention_stats()
}
```

---

## Troubleshooting

### Data Not Being Deleted

1. **Check retention policy is enabled:**
   ```python
   policy = retention_service.get_retention_policy(DataType.SESSION)
   print(f"Enabled: {policy.enabled}")
   ```

2. **Check scheduler is running:**
   ```python
   from src.services.retention_scheduler import get_scheduler
   
   scheduler = get_scheduler()
   if scheduler:
       print(scheduler.get_scheduled_jobs())
   else:
       print("Scheduler not initialized")
   ```

3. **Run manual cleanup:**
   ```bash
   curl -X POST "http://localhost:8000/api/compliance/retention/cleanup?dry_run=true"
   ```

### Data Requests Not Processing

1. **Check if requests are verified:**
   ```python
   unverified = data_requests_collection.count_documents({"verified": False})
   print(f"Unverified requests: {unverified}")
   ```

2. **Manually trigger processing:**
   ```python
   processed = compliance_service.process_pending_requests(limit=10)
   print(f"Processed: {processed}")
   ```

### PII Still Appearing in Logs

1. **Check PII masking is enabled:**
   ```python
   from src.utilities.pii_masking import mask_pii
   
   test_text = "Email: test@example.com"
   print(mask_pii(test_text))
   ```

2. **Verify logger configuration:**
   Ensure all loggers use `sanitize_for_logging()` wrapper.

---

## Testing

### Unit Tests

```bash
# Test PII masking
pytest tests/test_pii_masking.py

# Test retention service
pytest tests/test_retention_service.py

# Test compliance service
pytest tests/test_compliance_service.py
```

### Integration Tests

```python
# Test full data deletion flow
def test_data_deletion_flow():
    # Create user data
    user_id = "test_user_123"
    create_test_data(user_id)
    
    # Request deletion
    request = compliance_service.create_data_access_request(
        user_id=user_id,
        email="test@example.com",
        request_type="deletion"
    )
    
    # Verify request
    compliance_service.verify_data_request(
        request.request_id,
        request.verification_token
    )
    
    # Process request
    compliance_service.process_pending_requests()
    
    # Verify deletion
    assert sessions_collection.count_documents({"user_id": user_id}) == 0
    assert logs_collection.count_documents({"user_id": user_id}) == 0
```

---

## FAQ

### Q: How long does it take to process a data deletion request?

A: Data deletion requests are processed hourly by the scheduler. Once verified, deletion typically completes within 1-2 hours.

### Q: Can deleted data be recovered?

A: No. Once data is deleted via the compliance system, it is permanently removed and cannot be recovered. Always ensure proper verification before approving deletion requests.

### Q: What happens to archived data?

A: Archived data is stored in the configured archive location (S3 bucket or file system) before deletion. Archives should have their own retention policy and access controls.

### Q: How do I handle a user who wants their data deleted but has active services?

A: Consider implementing a "soft delete" that anonymizes the user's PII but retains necessary business records. Consult with legal counsel for specific requirements.

### Q: Are audit logs also subject to retention policies?

A: Audit logs typically have longer retention periods (default 2 years) to maintain compliance history. Configure separately based on regulatory requirements.

---

## Resources

### GDPR
- [Official GDPR Text](https://gdpr-info.eu/)
- [Article 17 - Right to Erasure](https://gdpr-info.eu/art-17-gdpr/)
- [Article 30 - Records of Processing](https://gdpr-info.eu/art-30-gdpr/)

### CCPA
- [Official CCPA Text](https://oag.ca.gov/privacy/ccpa)
- [CCPA Compliance Guide](https://www.oag.ca.gov/privacy/ccpa/compliance)

### Best Practices
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework)
- [ISO 27701 Privacy Information Management](https://www.iso.org/standard/71670.html)

---

## Support

For questions or issues related to compliance features:

1. Check the troubleshooting section above
2. Review audit logs for detailed error information
3. Contact your legal/compliance team for policy questions
4. File an issue in the project repository for technical problems