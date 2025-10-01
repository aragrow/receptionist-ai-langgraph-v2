# ==================== src/actions/scheduling_actions.py ====================
"""
Scheduling domain actions for SchedulingAgentL3.
Handles rescheduling, cancellations, appointment management.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from bson import ObjectId

from src.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class SchedulingActions:
    """Actions for scheduling/rescheduling domain."""
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize scheduling actions.
        
        Args:
            db_service: Database service for data operations
        """
        self.db_service = db_service
    
    async def reschedule_appointment(
        self,
        job_id: str,
        new_date: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reschedule an existing appointment.
        
        Args:
            job_id: Job ObjectId
            new_date: New date/time (ISO format)
            reason: Reason for rescheduling
        
        Returns:
            {
                "success": bool,
                "job_id": str,
                "old_date": str,
                "new_date": str,
                "confirmation_number": str
            }
        """
        try:
            logger.info(f"Rescheduling job {job_id} to {new_date}")
            
            # Parse new date
            try:
                new_datetime = datetime.fromisoformat(new_date.replace('Z', '+00:00'))
            except ValueError:
                return {
                    "success": False,
                    "error_code": "INVALID_DATE",
                    "error_message": f"Invalid date format: {new_date}"
                }
            
            # Get existing job
            job = await self.db_service.db.jobs.find_one({"_id": ObjectId(job_id)})
            
            if not job:
                return {
                    "success": False,
                    "error_code": "JOB_NOT_FOUND",
                    "error_message": f"Job {job_id} not found"
                }
            
            old_date = job.get("scheduled_date")
            
            # Check if job can be rescheduled
            if job.get("status") in ["completed", "cancelled"]:
                return {
                    "success": False,
                    "error_code": "CANNOT_RESCHEDULE",
                    "error_message": f"Cannot reschedule a {job.get('status')} job"
                }
            
            # Check availability for new time
            is_available = await self._check_availability(new_datetime)
            if not is_available:
                # Find alternatives
                alternatives = await self._find_alternative_slots(new_datetime)
                return {
                    "success": False,
                    "error_code": "TIME_UNAVAILABLE",
                    "error_message": "The requested time slot is not available",
                    "alternative_slots": alternatives
                }
            
            # Update job
            result = await self.db_service.db.jobs.update_one(
                {"_id": ObjectId(job_id)},
                {
                    "$set": {
                        "scheduled_date": new_datetime,
                        "updated_at": datetime.now(timezone.utc),
                        "reschedule_reason": reason
                    },
                    "$push": {
                        "reschedule_history": {
                            "old_date": old_date,
                            "new_date": new_datetime,
                            "reason": reason,
                            "rescheduled_at": datetime.now(timezone.utc)
                        }
                    }
                }
            )
            
            if result.matched_count == 0:
                return {
                    "success": False,
                    "error_code": "UPDATE_FAILED",
                    "error_message": "Failed to update job"
                }
            
            # Generate confirmation
            confirmation_number = f"RS-{str(job_id)[-8:].upper()}"
            
            # Send notifications
            await self._send_reschedule_notification(
                job_id=job_id,
                old_date=old_date.isoformat() if old_date else None,
                new_date=new_datetime.isoformat(),
                confirmation_number=confirmation_number
            )
            
            logger.info(f"Job rescheduled successfully: {confirmation_number}")
            
            return {
                "success": True,
                "job_id": job_id,
                "old_date": old_date.isoformat() if old_date else None,
                "new_date": new_datetime.isoformat(),
                "confirmation_number": confirmation_number,
                "status": "rescheduled"
            }
            
        except Exception as e:
            logger.error(f"Reschedule failed: {e}")
            return {
                "success": False,
                "error_code": "RESCHEDULE_FAILED",
                "error_message": str(e)
            }
    
    async def cancel_appointment(
        self,
        job_id: str,
        reason: Optional[str] = None,
        refund_requested: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel an existing appointment.
        
        Args:
            job_id: Job ObjectId
            reason: Cancellation reason
            refund_requested: Whether customer wants a refund
        
        Returns:
            {
                "success": bool,
                "job_id": str,
                "cancellation_number": str,
                "refund_status": str
            }
        """
        try:
            logger.info(f"Cancelling job {job_id}")
            
            # Get existing job
            job = await self.db_service.db.jobs.find_one({"_id": ObjectId(job_id)})
            
            if not job:
                return {
                    "success": False,
                    "error_code": "JOB_NOT_FOUND",
                    "error_message": f"Job {job_id} not found"
                }
            
            # Check if already cancelled
            if job.get("status") == "cancelled":
                return {
                    "success": False,
                    "error_code": "ALREADY_CANCELLED",
                    "error_message": "This appointment is already cancelled"
                }
            
            # Cannot cancel completed jobs
            if job.get("status") == "completed":
                return {
                    "success": False,
                    "error_code": "CANNOT_CANCEL",
                    "error_message": "Cannot cancel a completed job"
                }
            
            # Check cancellation policy (24 hours notice)
            scheduled_date = job.get("scheduled_date")
            if scheduled_date:
                hours_until = (scheduled_date - datetime.now(timezone.utc)).total_seconds() / 3600
                
                if hours_until < 24:
                    cancellation_fee = True
                    refund_amount = 0.5  # 50% refund if within 24 hours
                else:
                    cancellation_fee = False
                    refund_amount = 1.0  # Full refund if >24 hours
            else:
                cancellation_fee = False
                refund_amount = 1.0
            
            # Update job status
            result = await self.db_service.db.jobs.update_one(
                {"_id": ObjectId(job_id)},
                {
                    "$set": {
                        "status": "cancelled",
                        "cancellation_reason": reason,
                        "cancellation_date": datetime.now(timezone.utc),
                        "cancellation_fee_applied": cancellation_fee,
                        "refund_percentage": refund_amount
                    }
                }
            )
            
            if result.matched_count == 0:
                return {
                    "success": False,
                    "error_code": "UPDATE_FAILED",
                    "error_message": "Failed to cancel job"
                }
            
            # Generate cancellation number
            cancellation_number = f"CN-{str(job_id)[-8:].upper()}"
            
            # Determine refund status
            if refund_requested:
                if refund_amount == 1.0:
                    refund_status = "full_refund_approved"
                elif refund_amount == 0.5:
                    refund_status = "partial_refund_approved"
                else:
                    refund_status = "no_refund_available"
            else:
                refund_status = "not_requested"
            
            # Send notifications
            await self._send_cancellation_notification(
                job_id=job_id,
                cancellation_number=cancellation_number,
                refund_status=refund_status
            )
            
            logger.info(f"Job cancelled successfully: {cancellation_number}")
            
            return {
                "success": True,
                "job_id": job_id,
                "cancellation_number": cancellation_number,
                "refund_status": refund_status,
                "refund_percentage": refund_amount,
                "cancellation_fee_applied": cancellation_fee
            }
            
        except Exception as e:
            logger.error(f"Cancellation failed: {e}")
            return {
                "success": False,
                "error_code": "CANCELLATION_FAILED",
                "error_message": str(e)
            }
    
    async def get_upcoming_appointments(
        self,
        client_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get upcoming appointments for a client.
        
        Args:
            client_id: Client ObjectId
            limit: Maximum number of appointments to return
        
        Returns:
            {
                "success": bool,
                "appointments": List[Dict],
                "count": int
            }
        """
        try:
            logger.info(f"Getting appointments for client {client_id}")
            
            # Query for upcoming jobs
            cursor = self.db_service.db.jobs.find({
                "client_id": ObjectId(client_id),
                "status": {"$in": ["scheduled", "pending"]},
                "scheduled_date": {"$gte": datetime.now(timezone.utc)}
            }).sort("scheduled_date", 1).limit(limit)
            
            appointments = []
            async for job in cursor:
                appointments.append({
                    "job_id": str(job["_id"]),
                    "title": job.get("title", "Service Appointment"),
                    "scheduled_date": job.get("scheduled_date").isoformat() if job.get("scheduled_date") else None,
                    "status": job.get("status"),
                    "description": job.get("description")
                })
            
            logger.info(f"Found {len(appointments)} upcoming appointments")
            
            return {
                "success": True,
                "appointments": appointments,
                "count": len(appointments)
            }
            
        except Exception as e:
            logger.error(f"Failed to get appointments: {e}")
            return {
                "success": False,
                "error_code": "QUERY_FAILED",
                "error_message": str(e)
            }
    
    async def find_next_available_slot(
        self,
        service_type: str,
        preferred_date: Optional[str] = None,
        duration_hours: int = 2
    ) -> Dict[str, Any]:
        """
        Find the next available appointment slot.
        
        Args:
            service_type: Type of service
            preferred_date: Preferred date (ISO format), defaults to today
            duration_hours: Estimated duration
        
        Returns:
            {
                "success": bool,
                "available_slot": str,
                "alternative_slots": List[str]
            }
        """
        try:
            # Parse preferred date or use today
            if preferred_date:
                try:
                    start_date = datetime.fromisoformat(preferred_date.replace('Z', '+00:00'))
                except ValueError:
                    start_date = datetime.now(timezone.utc)
            else:
                start_date = datetime.now(timezone.utc)
            
            # Find next available slot
            available_slot = None
            alternative_slots = []
            
            for day_offset in range(14):  # Check next 2 weeks
                check_date = start_date.replace(day=start_date.day + day_offset)
                
                # Check multiple time slots per day (9 AM, 12 PM, 3 PM)
                for hour in [9, 12, 15]:
                    check_datetime = check_date.replace(hour=hour, minute=0, second=0)
                    
                    if await self._check_availability(check_datetime):
                        if not available_slot:
                            available_slot = check_datetime.isoformat()
                        else:
                            alternative_slots.append(check_datetime.isoformat())
                        
                        if len(alternative_slots) >= 5:  # Return up to 5 alternatives
                            break
                
                if available_slot and len(alternative_slots) >= 5:
                    break
            
            if not available_slot:
                return {
                    "success": False,
                    "error_code": "NO_AVAILABILITY",
                    "error_message": "No available slots found in the next 2 weeks"
                }
            
            logger.info(f"Found available slot: {available_slot}")
            
            return {
                "success": True,
                "available_slot": available_slot,
                "alternative_slots": alternative_slots
            }
            
        except Exception as e:
            logger.error(f"Failed to find available slot: {e}")
            return {
                "success": False,
                "error_code": "SEARCH_FAILED",
                "error_message": str(e)
            }
    
    # ============ Helper Methods ============
    
    async def _check_availability(self, requested_datetime: datetime) -> bool:
        """Check if a time slot is available."""
        try:
            # Simple capacity check
            existing_jobs = await self.db_service.db.jobs.count_documents({
                "scheduled_date": {
                    "$gte": requested_datetime.replace(minute=0, second=0),
                    "$lt": requested_datetime.replace(minute=59, second=59)
                },
                "status": {"$in": ["scheduled", "in-progress"]}
            })
            
            # Max 3 jobs per hour
            return existing_jobs < 3
            
        except Exception as e:
            logger.error(f"Availability check error: {e}")
            return True  # Default to available on error
    
    async def _find_alternative_slots(
        self,
        requested_datetime: datetime,
        count: int = 3
    ) -> List[str]:
        """Find alternative available time slots."""
        alternatives = []
        
        for day_offset in range(1, 8):  # Next 7 days
            for hour in [9, 12, 15]:  # Morning, noon, afternoon
                check_date = requested_datetime.replace(
                    day=requested_datetime.day + day_offset,
                    hour=hour,
                    minute=0,
                    second=0
                )
                
                if await self._check_availability(check_date):
                    alternatives.append(check_date.isoformat())
                    
                    if len(alternatives) >= count:
                        return alternatives
        
        return alternatives
    
    async def _send_reschedule_notification(
        self,
        job_id: str,
        old_date: Optional[str],
        new_date: str,
        confirmation_number: str
    ):
        """Send reschedule notification."""
        logger.info(f"Sending reschedule notification: {confirmation_number}")
        # Placeholder - implement actual notification service
    
    async def _send_cancellation_notification(
        self,
        job_id: str,
        cancellation_number: str,
        refund_status: str
    ):
        """Send cancellation notification."""
        logger.info(f"Sending cancellation notification: {cancellation_number}")
        # Placeholder - implement actual notification service