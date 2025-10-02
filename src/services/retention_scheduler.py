# ==================== src/services/retention_scheduler.py ====================
"""
Scheduled Tasks for Data Retention and Compliance

Runs periodic jobs to:
- Clean up expired data based on retention policies
- Process pending data access requests
- Generate compliance reports
"""

from datetime import datetime, UTC, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from typing import Optional

from src.services.retention_service import RetentionService
from src.services.compliance_service import ComplianceService


logger = logging.getLogger(__name__)


class RetentionScheduler:
    """
    Scheduler for automated data retention and compliance tasks.
    """
    
    def __init__(
        self,
        retention_service: RetentionService,
        compliance_service: ComplianceService,
        enabled: bool = True
    ):
        """
        Initialize retention scheduler.
        
        Args:
            retention_service: RetentionService instance
            compliance_service: ComplianceService instance
            enabled: Whether scheduler is enabled
        """
        self.retention_service = retention_service
        self.compliance_service = compliance_service
        self.scheduler = AsyncIOScheduler()
        self.enabled = enabled
        self._is_running = False
    
    def start(self) -> None:
        """Start the scheduler."""
        if not self.enabled:
            logger.info("Retention scheduler is disabled")
            return
        
        if self._is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting retention scheduler")
        
        # Schedule daily retention cleanup at 2 AM
        self.scheduler.add_job(
            self._run_retention_cleanup,
            CronTrigger(hour=2, minute=0),
            id="retention_cleanup",
            name="Daily Retention Cleanup",
            replace_existing=True
        )
        
        # Process data access requests every hour
        self.scheduler.add_job(
            self._process_data_requests,
            CronTrigger(minute=0),
            id="process_data_requests",
            name="Process Data Access Requests",
            replace_existing=True
        )
        
        # Generate weekly compliance report on Mondays at 9 AM
        self.scheduler.add_job(
            self._generate_weekly_report,
            CronTrigger(day_of_week='mon', hour=9, minute=0),
            id="weekly_compliance_report",
            name="Weekly Compliance Report",
            replace_existing=True
        )
        
        # Check retention stats daily at noon
        self.scheduler.add_job(
            self._log_retention_stats,
            CronTrigger(hour=12, minute=0),
            id="retention_stats",
            name="Log Retention Stats",
            replace_existing=True
        )
        
        self.scheduler.start()
        self._is_running = True
        logger.info("Retention scheduler started successfully")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._is_running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping retention scheduler")
        self.scheduler.shutdown(wait=True)
        self._is_running = False
        logger.info("Retention scheduler stopped")
    
    async def _run_retention_cleanup(self) -> None:
        """
        Run scheduled retention cleanup.
        
        This deletes data that has exceeded its retention period.
        """
        logger.info("Starting scheduled retention cleanup")
        
        try:
            results = self.retention_service.purge_all_expired_data(dry_run=False)
            
            total_deleted = sum(r.deleted_count for r in results.values())
            total_archived = sum(r.archived_count for r in results.values())
            
            logger.info(
                f"Retention cleanup completed: {total_deleted} records deleted, "
                f"{total_archived} archived"
            )
            
            # Log details for each data type
            for data_type, result in results.items():
                if result.deleted_count > 0 or result.archived_count > 0:
                    logger.info(
                        f"  {data_type.value}: deleted={result.deleted_count}, "
                        f"archived={result.archived_count}, "
                        f"time={result.execution_time_seconds:.2f}s"
                    )
                
                if result.errors:
                    logger.error(
                        f"  {data_type.value} errors: {', '.join(result.errors)}"
                    )
        
        except Exception as e:
            logger.error(f"Error during scheduled retention cleanup: {e}", exc_info=True)
    
    async def _process_data_requests(self) -> None:
        """
        Process pending data access requests.
        
        Handles GDPR/CCPA requests for data export or deletion.
        """
        logger.info("Processing pending data access requests")
        
        try:
            processed_ids = self.compliance_service.process_pending_requests(limit=50)
            
            if processed_ids:
                logger.info(
                    f"Processed {len(processed_ids)} data access requests: "
                    f"{', '.join(processed_ids)}"
                )
            else:
                logger.debug("No pending data access requests to process")
        
        except Exception as e:
            logger.error(f"Error processing data access requests: {e}", exc_info=True)
    
    async def _generate_weekly_report(self) -> None:
        """
        Generate weekly compliance report.
        
        Creates a summary of compliance activities for the past week.
        """
        logger.info("Generating weekly compliance report")
        
        try:
            end_date = datetime.now(UTC)
            start_date = end_date - timedelta(days=7)
            
            report = self.compliance_service.generate_compliance_report(
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(
                f"Weekly compliance report generated:\n"
                f"  Consent granted: {report['consent']['total_granted']}\n"
                f"  Consent withdrawn: {report['consent']['total_withdrawn']}\n"
                f"  Data requests: {report['data_requests']['total']}\n"
                f"  Data requests completed: {report['data_requests']['completed']}\n"
                f"  Audit events: {report['audit_events']['total']}"
            )
            
            # TODO: Send report via email to compliance team
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}", exc_info=True)
    
    async def _log_retention_stats(self) -> None:
        """
        Log retention statistics.
        
        Provides visibility into how much data is eligible for deletion.
        """
        logger.info("Checking retention statistics")
        
        try:
            stats = self.retention_service.get_retention_stats()
            
            total_eligible = sum(
                s.get("eligible_for_deletion", 0)
                for s in stats.values()
            )
            
            if total_eligible > 0:
                logger.info(f"Total records eligible for deletion: {total_eligible}")
                
                for data_type, data_stats in stats.items():
                    eligible = data_stats.get("eligible_for_deletion", 0)
                    if eligible > 0:
                        logger.info(
                            f"  {data_type}: {eligible} records "
                            f"(retention: {data_stats['retention_days']} days)"
                        )
            else:
                logger.debug("No records currently eligible for deletion")
        
        except Exception as e:
            logger.error(f"Error checking retention stats: {e}", exc_info=True)
    
    def trigger_cleanup_now(self, dry_run: bool = False) -> None:
        """
        Manually trigger retention cleanup immediately.
        
        Args:
            dry_run: If True, only count records without deleting
        """
        logger.info(f"Manually triggering retention cleanup (dry_run={dry_run})")
        
        try:
            results = self.retention_service.purge_all_expired_data(dry_run=dry_run)
            
            total_deleted = sum(r.deleted_count for r in results.values())
            logger.info(f"Manual cleanup completed: {total_deleted} records affected")
            
            return results
        
        except Exception as e:
            logger.error(f"Error during manual cleanup: {e}", exc_info=True)
            raise
    
    def get_scheduled_jobs(self) -> list:
        """
        Get list of scheduled jobs.
        
        Returns:
            List of job information
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs


# Global scheduler instance
_scheduler_instance: Optional[RetentionScheduler] = None


def initialize_scheduler(
    retention_service: RetentionService,
    compliance_service: ComplianceService,
    enabled: bool = True
) -> RetentionScheduler:
    """
    Initialize and start the global scheduler.
    
    Args:
        retention_service: RetentionService instance
        compliance_service: ComplianceService instance
        enabled: Whether scheduler should be enabled
    
    Returns:
        RetentionScheduler instance
    """
    global _scheduler_instance
    
    if _scheduler_instance is not None:
        logger.warning("Scheduler already initialized")
        return _scheduler_instance
    
    _scheduler_instance = RetentionScheduler(
        retention_service=retention_service,
        compliance_service=compliance_service,
        enabled=enabled
    )
    
    _scheduler_instance.start()
    return _scheduler_instance


def get_scheduler() -> Optional[RetentionScheduler]:
    """Get the global scheduler instance."""
    return _scheduler_instance


def shutdown_scheduler() -> None:
    """Shutdown the global scheduler."""
    global _scheduler_instance
    
    if _scheduler_instance is not None:
        _scheduler_instance.stop()
        _scheduler_instance = None