# ==================== src/agents/partner_agent_l3.py ====================
"""
Partner Agent L3 - Domain specialist for vendor/partner operations.
Handles: vendor check-ins, schedule updates, assignment confirmations.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from bson import ObjectId

from src.agents.l3_base_agent import L3BaseAgent
from src.models.workflow_models import WorkflowState
from src.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class PartnerAgentL3(L3BaseAgent):
    """
    Partner domain specialist - handles all vendor/partner operations.
    
    Supported Actions:
    - vendor_checkin: Log vendor arrival at job site
    - update_assignment: Update vendor assignment status
    - report_completion: Report job completion
    - request_supplies: Request additional supplies
    """
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize Partner Agent L3.
        
        Args:
            db_service: Database service for data access
        """
        super().__init__(
            agent_name="partner_agent_l3",
            domain="partner",
            db_service=db_service
        )
        
        logger.info("PartnerAgentL3 initialized")
    
    def get_supported_actions(self) -> List[str]:
        """
        Get list of actions this agent can perform.
        
        Returns:
            List of action names
        """
        return [
            "vendor_checkin",
            "update_assignment",
            "report_completion",
            "request_supplies"
        ]
    
    async def validate_prerequisites(
        self,
        action_name: str,
        state: WorkflowState
    ) -> tuple[bool, str | None]:
        """
        Validate that all prerequisites are met for the action.
        
        Args:
            action_name: Name of action to validate
            state: Current workflow state
        
        Returns:
            (is_valid, error_message)
        """
        entities = state.entities
        
        if action_name == "vendor_checkin":
            # Required: job_id or location
            if not entities.get("job_id") and not entities.get("location"):
                return False, "Either job ID or location is required for check-in"
            return True, None
        
        elif action_name == "update_assignment":
            # Required: job_id, status
            required_slots = ["job_id", "status"]
            return self._check_required_slots(state, required_slots)
        
        elif action_name == "report_completion":
            # Required: job_id
            required_slots = ["job_id"]
            return self._check_required_slots(state, required_slots)
        
        elif action_name == "request_supplies":
            # Required: job_id, supplies_needed
            required_slots = ["job_id", "supplies_needed"]
            return self._check_required_slots(state, required_slots)
        
        else:
            return False, f"Unknown action: {action_name}"
    
    async def execute_action(
        self,
        action_name: str,
        state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Execute the partner action.
        
        Args:
            action_name: Name of action to execute
            state: Current workflow state with all required information
        
        Returns:
            Dictionary with action results
        """
        try:
            if action_name == "vendor_checkin":
                return await self._vendor_checkin(state)
            
            elif action_name == "update_assignment":
                return await self._update_assignment(state)
            
            elif action_name == "report_completion":
                return await self._report_completion(state)
            
            elif action_name == "request_supplies":
                return await self._request_supplies(state)
            
            else:
                return {
                    "success": False,
                    "error_code": "UNKNOWN_ACTION",
                    "error_message": f"Unknown action: {action_name}"
                }
        
        except Exception as e:
            logger.error(f"Action execution failed: {action_name} - {e}")
            return {
                "success": False,
                "error_code": "EXECUTION_ERROR",
                "error_message": str(e)
            }
    
    # ============ Action Implementations ============
    
    async def _vendor_checkin(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Log vendor check-in at job site.
        
        Args:
            state: Workflow state with check-in details
        
        Returns:
            Check-in result dictionary
        """
        entities = state.entities
        
        # Extract check-in details
        job_id = entities.get("job_id")
        location = entities.get("location")
        vendor_id = str(state.vendor.id) if state.vendor else None
        notes = entities.get("notes")
        
        # If no job_id, try to find by location
        if not job_id and location:
            # Search for jobs at this location
            job = await self.db_service.db.jobs.find_one({
                "status": "scheduled",
                "scheduled_date": {
                    "$gte": datetime.now(timezone.utc).replace(hour=0, minute=0),
                    "$lt": datetime.now(timezone.utc).replace(hour=23, minute=59)
                }
                # In production, add address matching logic
            })
            
            if job:
                job_id = str(job["_id"])
            else:
                return {
                    "success": False,
                    "error_code": "JOB_NOT_FOUND",
                    "error_message": f"No scheduled job found at location: {location}"
                }
        
        if not job_id:
            return {
                "success": False,
                "error_code": "MISSING_JOB_ID",
                "error_message": "Job ID is required for check-in"
            }
        
        # Create visit record
        visit_id = ObjectId()
        visit_doc = {
            "_id": visit_id,
            "job_id": ObjectId(job_id),
            "vendor_id": ObjectId(vendor_id) if vendor_id else None,
            "visit_date": datetime.now(timezone.utc),
            "technician_name": state.vendor.name if state.vendor else "Unknown",
            "status": "arrived",
            "check_in_time": datetime.now(timezone.utc),
            "check_out_time": None,
            "notes": notes
        }
        
        # Save visit
        await self.db_service.db.visits.insert_one(visit_doc)
        
        # Update job status
        await self.db_service.db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": "in-progress",
                    "started_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"Vendor checked in at job {job_id}")
        
        return {
            "success": True,
            "visit_id": str(visit_id),
            "job_id": job_id,
            "check_in_time": datetime.now(timezone.utc).isoformat(),
            "status": "checked_in"
        }
    
    async def _update_assignment(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Update vendor assignment status.
        
        Args:
            state: Workflow state with assignment details
        
        Returns:
            Assignment update result dictionary
        """
        entities = state.entities
        
        # Extract update details
        job_id = entities.get("job_id")
        status = entities.get("status")
        notes = entities.get("notes")
        
        # Validate status
        valid_statuses = ["accepted", "declined", "en_route", "in_progress", "completed"]
        if status not in valid_statuses:
            return {
                "success": False,
                "error_code": "INVALID_STATUS",
                "error_message": f"Status must be one of: {', '.join(valid_statuses)}"
            }
        
        # Update job
        update_data = {
            "vendor_status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if status == "in_progress":
            update_data["status"] = "in-progress"
            update_data["started_at"] = datetime.now(timezone.utc)
        elif status == "completed":
            update_data["status"] = "completed"
            update_data["completion_date"] = datetime.now(timezone.utc)
        
        if notes:
            update_data["vendor_notes"] = notes
        
        result = await self.db_service.db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return {
                "success": False,
                "error_code": "JOB_NOT_FOUND",
                "error_message": f"Job {job_id} not found"
            }
        
        logger.info(f"Assignment updated: {job_id} -> {status}")
        
        return {
            "success": True,
            "job_id": job_id,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _report_completion(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Report job completion.
        
        Args:
            state: Workflow state with completion details
        
        Returns:
            Completion report result dictionary
        """
        entities = state.entities
        
        # Extract completion details
        job_id = entities.get("job_id")
        completion_notes = entities.get("completion_notes") or entities.get("notes")
        issues_encountered = entities.get("issues_encountered")
        
        # Get job
        job = await self.db_service.db.jobs.find_one({"_id": ObjectId(job_id)})
        
        if not job:
            return {
                "success": False,
                "error_code": "JOB_NOT_FOUND",
                "error_message": f"Job {job_id} not found"
            }
        
        # Update job to completed
        update_data = {
            "status": "completed",
            "completion_date": datetime.now(timezone.utc),
            "completion_notes": completion_notes,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if issues_encountered:
            update_data["issues_encountered"] = issues_encountered
        
        await self.db_service.db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        
        # Update visit record
        await self.db_service.db.visits.update_one(
            {"job_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": "completed",
                    "check_out_time": datetime.now(timezone.utc),
                    "report": completion_notes
                }
            }
        )
        
        logger.info(f"Job completion reported: {job_id}")
        
        return {
            "success": True,
            "job_id": job_id,
            "completion_date": datetime.now(timezone.utc).isoformat(),
            "status": "completed"
        }
    
    async def _request_supplies(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Request additional supplies for a job.
        
        Args:
            state: Workflow state with supply request details
        
        Returns:
            Supply request result dictionary
        """
        entities = state.entities
        
        # Extract request details
        job_id = entities.get("job_id")
        supplies_needed = entities.get("supplies_needed")
        urgency = entities.get("urgency", "normal")
        
        # Create supply request
        request_id = ObjectId()
        request_doc = {
            "_id": request_id,
            "job_id": ObjectId(job_id),
            "vendor_id": ObjectId(str(state.vendor.id)) if state.vendor else None,
            "supplies_needed": supplies_needed,
            "urgency": urgency,
            "status": "pending",
            "requested_at": datetime.now(timezone.utc),
            "fulfilled_at": None
        }
        
        # Save request
        await self.db_service.db.supply_requests.insert_one(request_doc)
        
        # Notify operations team (placeholder)
        logger.info(f"Supply request created: {request_id} for job {job_id}")
        
        return {
            "success": True,
            "request_id": str(request_id),
            "job_id": job_id,
            "supplies_needed": supplies_needed,
            "status": "pending",
            "urgency": urgency
        }