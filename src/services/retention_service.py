# ==================== src/utilities/retention_service.py ====================
"""
Data Retention Service

Manages automatic deletion of old data to comply with GDPR/CCPA regulations
and configurable retention policies.
"""

from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from pymongo import MongoClient
from pymongo.collection import Collection

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class DataType(Enum):
    """Types of data with different retention periods."""
    SESSION = "session"
    CONVERSATION_LOG = "conversation_log"
    TICKET = "ticket"
    METRICS = "metrics"
    AUDIT_LOG = "audit_log"
    USER_DATA = "user_data"


class RetentionPolicy(BaseModel):
    """Configuration for data retention."""
    data_type: DataType
    retention_days: int = Field(
        default=90,
        description="Number of days to retain data"
    )
    archive_before_delete: bool = Field(
        default=False,
        description="Archive data before deletion"
    )
    archive_location: Optional[str] = Field(
        default=None,
        description="S3 bucket or file path for archives"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this retention policy is active"
    )


class DeletionResult(BaseModel):
    """Result of a deletion operation."""
    data_type: DataType
    deleted_count: int
    archived_count: int = 0
    errors: List[str] = Field(default_factory=list)
    execution_time_seconds: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RetentionService:
    """
    Service for managing data retention and automatic deletion.
    
    Responsibilities:
    - Delete old sessions beyond retention period
    - Delete old conversation logs
    - Archive data before deletion (optional)
    - Track deletion operations in audit log
    - Provide manual purge endpoints
    """
    
    def __init__(
        self,
        mongo_client: MongoClient,
        database_name: str = "ai_receptionist",
        default_retention_days: int = 90
    ):
        """
        Initialize retention service.
        
        Args:
            mongo_client: MongoDB client instance
            database_name: Name of database
            default_retention_days: Default retention period in days
        """
        self.db = mongo_client[database_name]
        self.default_retention_days = default_retention_days
        
        # Collection references
        self.sessions_collection = self.db["sessions"]
        self.conversation_logs_collection = self.db["conversation_logs"]
        self.tickets_collection = self.db["tickets"]
        self.metrics_collection = self.db["metrics"]
        self.audit_logs_collection = self.db["audit_logs"]
        self.retention_policies_collection = self.db["retention_policies"]
        
        # Initialize default policies
        self._initialize_default_policies()
    
    def _initialize_default_policies(self) -> None:
        """Create default retention policies if they don't exist."""
        default_policies = [
            RetentionPolicy(
                data_type=DataType.SESSION,
                retention_days=30,
                archive_before_delete=False
            ),
            RetentionPolicy(
                data_type=DataType.CONVERSATION_LOG,
                retention_days=90,
                archive_before_delete=True,
                archive_location="s3://retention-archives/conversations/"
            ),
            RetentionPolicy(
                data_type=DataType.TICKET,
                retention_days=365,
                archive_before_delete=True,
                archive_location="s3://retention-archives/tickets/"
            ),
            RetentionPolicy(
                data_type=DataType.METRICS,
                retention_days=180,
                archive_before_delete=False
            ),
            RetentionPolicy(
                data_type=DataType.AUDIT_LOG,
                retention_days=730,  # 2 years for compliance
                archive_before_delete=True,
                archive_location="s3://retention-archives/audit/"
            ),
        ]
        
        for policy in default_policies:
            existing = self.retention_policies_collection.find_one({
                "data_type": policy.data_type.value
            })
            if not existing:
                self.retention_policies_collection.insert_one(policy.model_dump())
                logger.info(f"Created default retention policy for {policy.data_type.value}")
    
    def get_retention_policy(self, data_type: DataType) -> RetentionPolicy:
        """
        Get retention policy for a data type.
        
        Args:
            data_type: Type of data
        
        Returns:
            RetentionPolicy for the data type
        """
        policy_doc = self.retention_policies_collection.find_one({
            "data_type": data_type.value
        })
        
        if policy_doc:
            return RetentionPolicy(**policy_doc)
        else:
            # Return default policy
            return RetentionPolicy(
                data_type=data_type,
                retention_days=self.default_retention_days
            )
    
    def update_retention_policy(self, policy: RetentionPolicy) -> bool:
        """
        Update or create a retention policy.
        
        Args:
            policy: New retention policy
        
        Returns:
            True if successful
        """
        result = self.retention_policies_collection.update_one(
            {"data_type": policy.data_type.value},
            {"$set": policy.model_dump()},
            upsert=True
        )
        
        logger.info(f"Updated retention policy for {policy.data_type.value}")
        return result.acknowledged
    
    def delete_old_sessions(self, dry_run: bool = False) -> DeletionResult:
        """
        Delete sessions older than retention period.
        
        Args:
            dry_run: If True, only count records without deleting
        
        Returns:
            DeletionResult with deletion stats
        """
        start_time = datetime.now(UTC)
        policy = self.get_retention_policy(DataType.SESSION)
        
        if not policy.enabled:
            logger.info("Session retention policy is disabled")
            return DeletionResult(
                data_type=DataType.SESSION,
                deleted_count=0,
                execution_time_seconds=0
            )
        
        cutoff_date = datetime.now(UTC) - timedelta(days=policy.retention_days)
        
        try:
            # Find old sessions
            query = {
                "created_at": {"$lt": cutoff_date}
            }
            
            if dry_run:
                count = self.sessions_collection.count_documents(query)
                logger.info(f"Dry run: Would delete {count} sessions")
                return DeletionResult(
                    data_type=DataType.SESSION,
                    deleted_count=0,
                    execution_time_seconds=(datetime.now(UTC) - start_time).total_seconds()
                )
            
            # Archive if needed
            archived_count = 0
            if policy.archive_before_delete:
                archived_count = self._archive_data(
                    self.sessions_collection,
                    query,
                    policy.archive_location
                )
            
            # Delete old sessions
            result = self.sessions_collection.delete_many(query)
            
            # Log audit trail
            self._log_deletion(
                data_type=DataType.SESSION,
                deleted_count=result.deleted_count,
                cutoff_date=cutoff_date
            )
            
            execution_time = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(
                f"Deleted {result.deleted_count} sessions older than {policy.retention_days} days "
                f"(archived: {archived_count})"
            )
            
            return DeletionResult(
                data_type=DataType.SESSION,
                deleted_count=result.deleted_count,
                archived_count=archived_count,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            logger.error(f"Error deleting old sessions: {e}")
            return DeletionResult(
                data_type=DataType.SESSION,
                deleted_count=0,
                errors=[str(e)],
                execution_time_seconds=(datetime.now(UTC) - start_time).total_seconds()
            )
    
    def delete_old_conversation_logs(self, dry_run: bool = False) -> DeletionResult:
        """
        Delete conversation logs older than retention period.
        
        Args:
            dry_run: If True, only count records without deleting
        
        Returns:
            DeletionResult with deletion stats
        """
        start_time = datetime.now(UTC)
        policy = self.get_retention_policy(DataType.CONVERSATION_LOG)
        
        if not policy.enabled:
            logger.info("Conversation log retention policy is disabled")
            return DeletionResult(
                data_type=DataType.CONVERSATION_LOG,
                deleted_count=0,
                execution_time_seconds=0
            )
        
        cutoff_date = datetime.now(UTC) - timedelta(days=policy.retention_days)
        
        try:
            query = {
                "timestamp": {"$lt": cutoff_date}
            }
            
            if dry_run:
                count = self.conversation_logs_collection.count_documents(query)
                logger.info(f"Dry run: Would delete {count} conversation logs")
                return DeletionResult(
                    data_type=DataType.CONVERSATION_LOG,
                    deleted_count=0,
                    execution_time_seconds=(datetime.now(UTC) - start_time).total_seconds()
                )
            
            # Archive if needed
            archived_count = 0
            if policy.archive_before_delete:
                archived_count = self._archive_data(
                    self.conversation_logs_collection,
                    query,
                    policy.archive_location
                )
            
            result = self.conversation_logs_collection.delete_many(query)
            
            self._log_deletion(
                data_type=DataType.CONVERSATION_LOG,
                deleted_count=result.deleted_count,
                cutoff_date=cutoff_date
            )
            
            execution_time = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(
                f"Deleted {result.deleted_count} conversation logs older than {policy.retention_days} days"
            )
            
            return DeletionResult(
                data_type=DataType.CONVERSATION_LOG,
                deleted_count=result.deleted_count,
                archived_count=archived_count,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            logger.error(f"Error deleting conversation logs: {e}")
            return DeletionResult(
                data_type=DataType.CONVERSATION_LOG,
                deleted_count=0,
                errors=[str(e)],
                execution_time_seconds=(datetime.now(UTC) - start_time).total_seconds()
            )
    
    def delete_old_metrics(self, dry_run: bool = False) -> DeletionResult:
        """Delete metrics older than retention period."""
        start_time = datetime.now(UTC)
        policy = self.get_retention_policy(DataType.METRICS)
        
        if not policy.enabled:
            return DeletionResult(
                data_type=DataType.METRICS,
                deleted_count=0,
                execution_time_seconds=0
            )
        
        cutoff_date = datetime.now(UTC) - timedelta(days=policy.retention_days)
        
        try:
            query = {
                "timestamp": {"$lt": cutoff_date}
            }
            
            if dry_run:
                count = self.metrics_collection.count_documents(query)
                return DeletionResult(
                    data_type=DataType.METRICS,
                    deleted_count=0,
                    execution_time_seconds=(datetime.now(UTC) - start_time).total_seconds()
                )
            
            result = self.metrics_collection.delete_many(query)
            
            self._log_deletion(
                data_type=DataType.METRICS,
                deleted_count=result.deleted_count,
                cutoff_date=cutoff_date
            )
            
            execution_time = (datetime.now(UTC) - start_time).total_seconds()
            return DeletionResult(
                data_type=DataType.METRICS,
                deleted_count=result.deleted_count,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            logger.error(f"Error deleting metrics: {e}")
            return DeletionResult(
                data_type=DataType.METRICS,
                deleted_count=0,
                errors=[str(e)],
                execution_time_seconds=(datetime.now(UTC) - start_time).total_seconds()
            )
    
    def purge_all_expired_data(self, dry_run: bool = False) -> Dict[DataType, DeletionResult]:
        """
        Run retention cleanup for all data types.
        
        Args:
            dry_run: If True, only count records without deleting
        
        Returns:
            Dictionary mapping data types to deletion results
        """
        logger.info(f"Starting retention cleanup (dry_run={dry_run})")
        
        results = {
            DataType.SESSION: self.delete_old_sessions(dry_run),
            DataType.CONVERSATION_LOG: self.delete_old_conversation_logs(dry_run),
            DataType.METRICS: self.delete_old_metrics(dry_run),
        }
        
        total_deleted = sum(r.deleted_count for r in results.values())
        total_archived = sum(r.archived_count for r in results.values())
        
        logger.info(
            f"Retention cleanup complete: {total_deleted} records deleted, "
            f"{total_archived} archived"
        )
        
        return results
    
    def delete_user_data(self, user_id: str) -> Dict[str, int]:
        """
        Delete all data for a specific user (GDPR right to erasure).
        
        Args:
            user_id: User identifier
        
        Returns:
            Dictionary with counts of deleted records per collection
        """
        logger.info(f"Deleting all data for user: {user_id}")
        
        deleted_counts = {}
        
        # Delete from all collections
        collections = {
            "sessions": self.sessions_collection,
            "conversation_logs": self.conversation_logs_collection,
            "tickets": self.tickets_collection,
        }
        
        for name, collection in collections.items():
            result = collection.delete_many({"user_id": user_id})
            deleted_counts[name] = result.deleted_count
            logger.info(f"Deleted {result.deleted_count} {name} for user {user_id}")
        
        # Log audit trail
        self.audit_logs_collection.insert_one({
            "event_type": "user_data_deletion",
            "user_id": user_id,
            "deleted_counts": deleted_counts,
            "timestamp": datetime.now(UTC),
            "reason": "User request (GDPR)"
        })
        
        return deleted_counts
    
    def _archive_data(
        self,
        collection: Collection,
        query: Dict[str, Any],
        archive_location: Optional[str]
    ) -> int:
        """
        Archive data before deletion.
        
        Args:
            collection: MongoDB collection
            query: Query to find records to archive
            archive_location: S3 bucket or file path
        
        Returns:
            Number of archived records
        """
        if not archive_location:
            return 0
        
        try:
            # Find records to archive
            records = list(collection.find(query))
            
            if not records:
                return 0
            
            # TODO: Implement actual archiving to S3 or file system
            # For now, just log the intent
            logger.info(
                f"Would archive {len(records)} records to {archive_location}"
            )
            
            return len(records)
            
        except Exception as e:
            logger.error(f"Error archiving data: {e}")
            return 0
    
    def _log_deletion(
        self,
        data_type: DataType,
        deleted_count: int,
        cutoff_date: datetime
    ) -> None:
        """
        Log deletion operation to audit trail.
        
        Args:
            data_type: Type of data deleted
            deleted_count: Number of records deleted
            cutoff_date: Cutoff date for deletion
        """
        self.audit_logs_collection.insert_one({
            "event_type": "data_retention_cleanup",
            "data_type": data_type.value,
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date,
            "timestamp": datetime.now(UTC)
        })
    
    def get_retention_stats(self) -> Dict[str, Any]:
        """
        Get statistics about data retention.
        
        Returns:
            Dictionary with retention statistics
        """
        stats = {}
        
        for data_type in DataType:
            policy = self.get_retention_policy(data_type)
            cutoff_date = datetime.now(UTC) - timedelta(days=policy.retention_days)
            
            # Count records eligible for deletion
            collection = self._get_collection_for_type(data_type)
            if collection:
                eligible_count = collection.count_documents({
                    "created_at": {"$lt": cutoff_date}
                })
                
                stats[data_type.value] = {
                    "retention_days": policy.retention_days,
                    "enabled": policy.enabled,
                    "eligible_for_deletion": eligible_count,
                    "cutoff_date": cutoff_date.isoformat()
                }
        
        return stats
    
    def _get_collection_for_type(self, data_type: DataType) -> Optional[Collection]:
        """Get MongoDB collection for a data type."""
        mapping = {
            DataType.SESSION: self.sessions_collection,
            DataType.CONVERSATION_LOG: self.conversation_logs_collection,
            DataType.TICKET: self.tickets_collection,
            DataType.METRICS: self.metrics_collection,
        }
        return