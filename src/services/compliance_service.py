# ==================== src/services/compliance_service.py ====================
"""
Compliance Service

Manages GDPR/CCPA compliance features including:
- Consent tracking
- Data access requests
- Data deletion requests (Right to be Forgotten)
- Data portability (Right to Data Access)
- Audit trails
"""

from datetime import datetime, UTC
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import logging
from pymongo import MongoClient
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ConsentType(Enum):
    """Types of consent that can be tracked."""
    DATA_PROCESSING = "data_processing"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    THIRD_PARTY_SHARING = "third_party_sharing"
    RECORDING = "recording"


class ConsentStatus(Enum):
    """Status of consent."""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


class DataAccessRequestStatus(Enum):
    """Status of data access request."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Consent(BaseModel):
    """Model for user consent."""
    user_id: str
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    version: str = Field(
        default="1.0",
        description="Version of consent form/policy"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DataAccessRequest(BaseModel):
    """Model for GDPR/CCPA data access request."""
    request_id: str
    user_id: str
    email: str
    request_type: str = Field(
        description="'access' for data export or 'deletion' for right to be forgotten"
    )
    status: DataAccessRequestStatus
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    data_export_url: Optional[str] = None
    verification_token: Optional[str] = None
    verified: bool = False
    verified_at: Optional[datetime] = None
    notes: List[str] = Field(default_factory=list)


class AuditLogEntry(BaseModel):
    """Model for audit log entry."""
    event_type: str
    user_id: Optional[str] = None
    actor_id: Optional[str] = None  # Who performed the action
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    severity: str = Field(default="info")  # info, warning, error, critical


class ComplianceService:
    """
    Service for managing GDPR/CCPA compliance.
    
    Responsibilities:
    - Track and manage user consent
    - Handle data access requests (Right to Access)
    - Handle data deletion requests (Right to be Forgotten)
    - Provide data portability (export user data)
    - Maintain audit trail of data access
    - Generate compliance reports
    """
    
    def __init__(
        self,
        mongo_client: MongoClient,
        database_name: str = "ai_receptionist"
    ):
        """
        Initialize compliance service.
        
        Args:
            mongo_client: MongoDB client instance
            database_name: Name of database
        """
        self.db = mongo_client[database_name]
        
        # Collection references
        self.consent_collection = self.db["consent"]
        self.data_requests_collection = self.db["data_access_requests"]
        self.audit_logs_collection = self.db["audit_logs"]
        self.sessions_collection = self.db["sessions"]
        self.conversation_logs_collection = self.db["conversation_logs"]
        self.tickets_collection = self.db["tickets"]
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self) -> None:
        """Create database indexes for performance."""
        # Consent indexes
        self.consent_collection.create_index([("user_id", 1), ("consent_type", 1)])
        self.consent_collection.create_index("created_at")
        
        # Data request indexes
        self.data_requests_collection.create_index("request_id", unique=True)
        self.data_requests_collection.create_index([("user_id", 1), ("status", 1)])
        self.data_requests_collection.create_index("requested_at")
        
        # Audit log indexes
        self.audit_logs_collection.create_index([("user_id", 1), ("timestamp", -1)])
        self.audit_logs_collection.create_index("timestamp")
        self.audit_logs_collection.create_index("event_type")
    
    # ==================== CONSENT MANAGEMENT ====================
    
    def record_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Consent:
        """
        Record user consent.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent
            granted: Whether consent was granted
            ip_address: IP address of user
            user_agent: User agent string
            metadata: Additional metadata
        
        Returns:
            Consent object
        """
        status = ConsentStatus.GRANTED if granted else ConsentStatus.DENIED
        now = datetime.now(UTC)
        
        consent = Consent(
            user_id=user_id,
            consent_type=consent_type,
            status=status,
            granted_at=now if granted else None,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        
        self.consent_collection.insert_one(consent.model_dump())
        
        # Log to audit trail
        self._log_audit(
            event_type="consent_recorded",
            user_id=user_id,
            action="record_consent",
            details={
                "consent_type": consent_type.value,
                "granted": granted
            },
            ip_address=ip_address
        )
        
        logger.info(f"Recorded consent for user {user_id}: {consent_type.value}={granted}")
        return consent
    
    def withdraw_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Withdraw previously granted consent.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to withdraw
            ip_address: IP address of user
        
        Returns:
            True if successful
        """
        now = datetime.now(UTC)
        
        result = self.consent_collection.update_many(
            {
                "user_id": user_id,
                "consent_type": consent_type.value,
                "status": ConsentStatus.GRANTED.value
            },
            {
                "$set": {
                    "status": ConsentStatus.WITHDRAWN.value,
                    "withdrawn_at": now,
                    "updated_at": now
                }
            }
        )
        
        # Log to audit trail
        self._log_audit(
            event_type="consent_withdrawn",
            user_id=user_id,
            action="withdraw_consent",
            details={
                "consent_type": consent_type.value,
                "updated_count": result.modified_count
            },
            ip_address=ip_address
        )
        
        logger.info(f"Withdrew consent for user {user_id}: {consent_type.value}")
        return result.modified_count > 0
    
    def get_user_consents(self, user_id: str) -> List[Consent]:
        """
        Get all consents for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of Consent objects
        """
        consents = list(self.consent_collection.find({"user_id": user_id}))
        return [Consent(**c) for c in consents]
    
    def has_consent(
        self,
        user_id: str,
        consent_type: ConsentType
    ) -> bool:
        """
        Check if user has granted specific consent.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to check
        
        Returns:
            True if consent is granted
        """
        consent = self.consent_collection.find_one({
            "user_id": user_id,
            "consent_type": consent_type.value,
            "status": ConsentStatus.GRANTED.value
        })
        return consent is not None
    
    # ==================== DATA ACCESS REQUESTS ====================
    
    def create_data_access_request(
        self,
        user_id: str,
        email: str,
        request_type: str = "access"
    ) -> DataAccessRequest:
        """
        Create a data access request (GDPR Article 15 - Right to Access).
        
        Args:
            user_id: User identifier
            email: User's email for verification
            request_type: 'access' or 'deletion'
        
        Returns:
            DataAccessRequest object
        """
        import uuid
        
        request_id = f"DAR-{uuid.uuid4().hex[:12].upper()}"
        verification_token = uuid.uuid4().hex
        
        request = DataAccessRequest(
            request_id=request_id,
            user_id=user_id,
            email=email,
            request_type=request_type,
            status=DataAccessRequestStatus.PENDING,
            verification_token=verification_token
        )
        
        self.data_requests_collection.insert_one(request.model_dump())
        
        # Log to audit trail
        self._log_audit(
            event_type="data_access_request_created",
            user_id=user_id,
            action="create_request",
            details={
                "request_id": request_id,
                "request_type": request_type
            }
        )
        
        logger.info(f"Created data access request {request_id} for user {user_id}")
        
        # TODO: Send verification email with token
        
        return request
    
    def verify_data_request(
        self,
        request_id: str,
        verification_token: str
    ) -> bool:
        """
        Verify a data access request using the token.
        
        Args:
            request_id: Request identifier
            verification_token: Verification token from email
        
        Returns:
            True if verification successful
        """
        result = self.data_requests_collection.update_one(
            {
                "request_id": request_id,
                "verification_token": verification_token,
                "verified": False
            },
            {
                "$set": {
                    "verified": True,
                    "verified_at": datetime.now(UTC),
                    "status": DataAccessRequestStatus.PROCESSING.value
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Verified data access request {request_id}")
            return True
        
        return False
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all data for a user (GDPR Article 20 - Right to Data Portability).
        
        Args:
            user_id: User identifier
        
        Returns:
            Dictionary containing all user data
        """
        logger.info(f"Exporting data for user {user_id}")
        
        # Collect data from all collections
        user_data = {
            "user_id": user_id,
            "export_date": datetime.now(UTC).isoformat(),
            "sessions": list(self.sessions_collection.find({"user_id": user_id})),
            "conversation_logs": list(self.conversation_logs_collection.find({"user_id": user_id})),
            "tickets": list(self.tickets_collection.find({"user_id": user_id})),
            "consents": list(self.consent_collection.find({"user_id": user_id})),
            "data_requests": list(self.data_requests_collection.find({"user_id": user_id}))
        }
        
        # Convert ObjectIds to strings for JSON serialization
        user_data = self._serialize_for_json(user_data)
        
        # Log to audit trail
        self._log_audit(
            event_type="data_exported",
            user_id=user_id,
            action="export_data",
            details={
                "sessions_count": len(user_data["sessions"]),
                "logs_count": len(user_data["conversation_logs"])
            }
        )
        
        return user_data
    
    def delete_user_data(
        self,
        user_id: str,
        reason: str = "User request (GDPR Article 17 - Right to Erasure)"
    ) -> Dict[str, int]:
        """
        Delete all data for a user (Right to be Forgotten).
        
        Args:
            user_id: User identifier
            reason: Reason for deletion
        
        Returns:
            Dictionary with counts of deleted records
        """
        logger.warning(f"Deleting all data for user {user_id}. Reason: {reason}")
        
        deleted_counts = {}
        
        # Delete from all collections
        collections = {
            "sessions": self.sessions_collection,
            "conversation_logs": self.conversation_logs_collection,
            "tickets": self.tickets_collection,
            "consent": self.consent_collection,
        }
        
        for name, collection in collections.items():
            result = collection.delete_many({"user_id": user_id})
            deleted_counts[name] = result.deleted_count
        
        # Mark data requests as completed
        self.data_requests_collection.update_many(
            {
                "user_id": user_id,
                "request_type": "deletion",
                "status": {"$ne": DataAccessRequestStatus.COMPLETED.value}
            },
            {
                "$set": {
                    "status": DataAccessRequestStatus.COMPLETED.value,
                    "completed_at": datetime.now(UTC)
                },
                "$push": {
                    "notes": f"Data deleted: {deleted_counts}"
                }
            }
        )
        
        # Log to audit trail
        self._log_audit(
            event_type="user_data_deleted",
            user_id=user_id,
            action="delete_all_data",
            details={
                "reason": reason,
                "deleted_counts": deleted_counts
            },
            severity="warning"
        )
        
        logger.info(f"Deleted data for user {user_id}: {deleted_counts}")
        return deleted_counts
    
    def process_pending_requests(self, limit: int = 10) -> List[str]:
        """
        Process pending data access requests.
        
        Args:
            limit: Maximum number of requests to process
        
        Returns:
            List of processed request IDs
        """
        # Find verified, pending requests
        pending_requests = list(self.data_requests_collection.find({
            "status": DataAccessRequestStatus.PROCESSING.value,
            "verified": True
        }).limit(limit))
        
        processed_ids = []
        
        for request_doc in pending_requests:
            request = DataAccessRequest(**request_doc)
            
            try:
                if request.request_type == "access":
                    # Export user data
                    user_data = self.export_user_data(request.user_id)
                    
                    # TODO: Upload to S3 and generate signed URL
                    data_export_url = f"https://exports.example.com/{request.request_id}.json"
                    
                    # Update request
                    self.data_requests_collection.update_one(
                        {"request_id": request.request_id},
                        {
                            "$set": {
                                "status": DataAccessRequestStatus.COMPLETED.value,
                                "completed_at": datetime.now(UTC),
                                "data_export_url": data_export_url
                            }
                        }
                    )
                    
                    # TODO: Send email with download link
                    
                elif request.request_type == "deletion":
                    # Delete user data
                    deleted_counts = self.delete_user_data(
                        request.user_id,
                        reason=f"Data access request {request.request_id}"
                    )
                    
                    # Request is already marked as completed in delete_user_data
                    
                processed_ids.append(request.request_id)
                logger.info(f"Processed data access request {request.request_id}")
                
            except Exception as e:
                logger.error(f"Error processing request {request.request_id}: {e}")
                self.data_requests_collection.update_one(
                    {"request_id": request.request_id},
                    {
                        "$set": {
                            "status": DataAccessRequestStatus.FAILED.value
                        },
                        "$push": {
                            "notes": f"Error: {str(e)}"
                        }
                    }
                )
        
        return processed_ids
    
    # ==================== AUDIT TRAIL ====================
    
    def _log_audit(
        self,
        event_type: str,
        action: str,
        user_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: str = "info"
    ) -> None:
        """
        Log an event to the audit trail.
        
        Args:
            event_type: Type of event
            action: Action performed
            user_id: User who is subject of action
            actor_id: User who performed action
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details
            ip_address: IP address
            user_agent: User agent
            severity: Severity level
        """
        entry = AuditLogEntry(
            event_type=event_type,
            user_id=user_id,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity
        )
        
        self.audit_logs_collection.insert_one(entry.model_dump())
    
    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """
        Retrieve audit logs with filters.
        
        Args:
            user_id: Filter by user
            event_type: Filter by event type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
        
        Returns:
            List of audit log entries
        """
        query = {}
        
        if user_id:
            query["user_id"] = user_id
        if event_type:
            query["event_type"] = event_type
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date
        
        logs = list(
            self.audit_logs_collection
            .find(query)
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        return [AuditLogEntry(**log) for log in logs]
    
    # ==================== COMPLIANCE REPORTS ====================
    
    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Generate compliance report for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            Dictionary with compliance metrics
        """
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "consent": {
                "total_granted": self.consent_collection.count_documents({
                    "status": ConsentStatus.GRANTED.value,
                    "granted_at": {"$gte": start_date, "$lte": end_date}
                }),
                "total_withdrawn": self.consent_collection.count_documents({
                    "status": ConsentStatus.WITHDRAWN.value,
                    "withdrawn_at": {"$gte": start_date, "$lte": end_date}
                })
            },
            "data_requests": {
                "total": self.data_requests_collection.count_documents({
                    "requested_at": {"$gte": start_date, "$lte": end_date}
                }),
                "access_requests": self.data_requests_collection.count_documents({
                    "request_type": "access",
                    "requested_at": {"$gte": start_date, "$lte": end_date}
                }),
                "deletion_requests": self.data_requests_collection.count_documents({
                    "request_type": "deletion",
                    "requested_at": {"$gte": start_date, "$lte": end_date}
                }),
                "completed": self.data_requests_collection.count_documents({
                    "status": DataAccessRequestStatus.COMPLETED.value,
                    "completed_at": {"$gte": start_date, "$lte": end_date}
                })
            },
            "audit_events": {
                "total": self.audit_logs_collection.count_documents({
                    "timestamp": {"$gte": start_date, "$lte": end_date}
                }),
                "data_access": self.audit_logs_collection.count_documents({
                    "event_type": "data_accessed",
                    "timestamp": {"$gte": start_date, "$lte": end_date}
                }),
                "data_deletions": self.audit_logs_collection.count_documents({
                    "event_type": "user_data_deleted",
                    "timestamp": {"$gte": start_date, "$lte": end_date}
                })
            }
        }
        
        return report
    
    def _serialize_for_json(self, data: Any) -> Any:
        """Convert MongoDB documents to JSON-serializable format."""
        from bson import ObjectId
        
        if isinstance(data, dict):
            return {
                k: self._serialize_for_json(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._serialize_for_json(item) for item in data]
        elif isinstance(data, ObjectId):
            return str(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data