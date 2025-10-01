# ==================== src/services/ticket_service.py ====================
"""
Ticket Service for managing human escalation tickets.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class TicketService:
    """
    Service for creating and managing escalation tickets.
    
    Responsibilities:
    - Create tickets with conversation transcripts
    - Update ticket status
    - Assign tickets to operators
    - Retrieve tickets by various criteria
    - Track ticket metrics
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize ticket service.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.tickets_collection = db["escalation_tickets"]
        self.operators_collection = db["operators"]
        self.metrics_collection = db["escalation_metrics"]
    
    # ============ Ticket Creation & Retrieval ============
    
    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new escalation ticket.
        
        Args:
            ticket_data: Ticket information including transcript and context
        
        Returns:
            Created ticket document
        """
        # Ensure required fields
        if "ticket_id" not in ticket_data:
            raise ValueError("ticket_id is required")
        
        # Add timestamps
        ticket_data["created_at"] = datetime.now(timezone.utc)
        ticket_data["updated_at"] = datetime.now(timezone.utc)
        
        # Set default status if not provided
        if "status" not in ticket_data:
            ticket_data["status"] = "open"
        
        # Set default priority if not provided
        if "priority" not in ticket_data:
            ticket_data["priority"] = "medium"
        
        # Initialize notes array if not present
        if "notes" not in ticket_data:
            ticket_data["notes"] = []
        
        # Insert into database
        try:
            result = await self.tickets_collection.insert_one(ticket_data)
            
            logger.info(
                f"Created ticket {ticket_data['ticket_id']} "
                f"with priority {ticket_data.get('priority', 'unknown')}"
            )
            
            # Log ticket creation for metrics
            await self._log_ticket_creation(ticket_data)
            
            return ticket_data
            
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            raise
    
    async def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a ticket by ID.
        
        Args:
            ticket_id: Ticket ID to look up
        
        Returns:
            Ticket document or None if not found
        """
        try:
            ticket = await self.tickets_collection.find_one({"ticket_id": ticket_id})
            
            if ticket:
                # Remove MongoDB _id for cleaner output
                ticket.pop("_id", None)
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error retrieving ticket {ticket_id}: {e}")
            return None
    
    async def get_tickets_by_session(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all tickets for a session.
        
        Args:
            session_id: Session ID to look up
        
        Returns:
            List of ticket documents
        """
        try:
            cursor = self.tickets_collection.find({"session_id": session_id})
            tickets = await cursor.to_list(length=100)
            
            # Remove MongoDB _id
            for ticket in tickets:
                ticket.pop("_id", None)
            
            return tickets
            
        except Exception as e:
            logger.error(f"Error retrieving tickets for session {session_id}: {e}")
            return []
    
    async def get_open_tickets(
        self,
        limit: int = 50,
        priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get open tickets, optionally filtered by priority.
        
        Args:
            limit: Maximum number of tickets to return
            priority: Optional priority filter (urgent, high, medium, low)
        
        Returns:
            List of open ticket documents
        """
        try:
            query = {"status": "open"}
            
            if priority:
                query["priority"] = priority
            
            cursor = self.tickets_collection.find(query).sort(
                [("created_at", -1)]
            ).limit(limit)
            
            tickets = await cursor.to_list(length=limit)
            
            # Remove MongoDB _id
            for ticket in tickets:
                ticket.pop("_id", None)
            
            return tickets
            
        except Exception as e:
            logger.error(f"Error retrieving open tickets: {e}")
            return []
    
    # ============ Ticket Updates ============
    
    async def update_ticket_status(
        self,
        ticket_id: str,
        new_status: str,
        operator_notes: Optional[str] = None
    ) -> bool:
        """
        Update ticket status.
        
        Args:
            ticket_id: Ticket to update
            new_status: New status (open, in_progress, resolved, closed)
            operator_notes: Optional notes from operator
        
        Returns:
            True if update successful
        """
        try:
            update_data = {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if operator_notes:
                update_data["operator_notes"] = operator_notes
            
            # Add resolution timestamp if closing
            if new_status in ["resolved", "closed"]:
                update_data["resolved_at"] = datetime.now(timezone.utc)
            
            result = await self.tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated ticket {ticket_id} status to {new_status}")
                
                # Log status change metric
                await self._log_ticket_status_change(ticket_id, new_status)
                
                return True
            else:
                logger.warning(f"Failed to update ticket {ticket_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating ticket status: {e}")
            return False
    
    async def assign_to_operator(
        self,
        ticket_id: str,
        operator_id: str,
        operator_name: str
    ) -> bool:
        """
        Assign ticket to an operator.
        
        Args:
            ticket_id: Ticket to assign
            operator_id: Operator's ID
            operator_name: Operator's name
        
        Returns:
            True if assignment successful
        """
        try:
            update_data = {
                "assigned_to": {
                    "operator_id": operator_id,
                    "operator_name": operator_name,
                    "assigned_at": datetime.now(timezone.utc)
                },
                "status": "in_progress",  # Auto-update status when assigned
                "updated_at": datetime.now(timezone.utc)
            }
            
            result = await self.tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Assigned ticket {ticket_id} to {operator_name}")
                
                # Update operator's active ticket count
                await self.operators_collection.update_one(
                    {"operator_id": operator_id},
                    {"$inc": {"active_tickets": 1}}
                )
                
                return True
            else:
                logger.warning(f"Failed to assign ticket {ticket_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error assigning ticket: {e}")
            return False
    
    async def add_operator_note(
        self,
        ticket_id: str,
        operator_id: str,
        note: str
    ) -> bool:
        """
        Add a note to a ticket.
        
        Args:
            ticket_id: Ticket to update
            operator_id: ID of operator adding note
            note: Note text
        
        Returns:
            True if note added successfully
        """
        try:
            note_entry = {
                "operator_id": operator_id,
                "note": note,
                "timestamp": datetime.now(timezone.utc)
            }
            
            result = await self.tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {
                    "$push": {"notes": note_entry},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error adding operator note: {e}")
            return False
    
    # ============ Metrics & Analytics ============
    
    async def _log_ticket_creation(self, ticket_data: Dict[str, Any]) -> None:
        """
        Log ticket creation for metrics tracking.
        
        Args:
            ticket_data: Ticket information
        """
        try:
            metric_entry = {
                "event": "ticket_created",
                "ticket_id": ticket_data["ticket_id"],
                "session_id": ticket_data.get("session_id"),
                "caller_type": ticket_data.get("caller_type"),
                "escalation_reason": ticket_data.get("escalation_reason"),
                "priority": ticket_data.get("priority"),
                "timestamp": datetime.now(timezone.utc)
            }
            
            # Insert into metrics collection
            await self.metrics_collection.insert_one(metric_entry)
            
        except Exception as e:
            logger.error(f"Error logging ticket creation metric: {e}")
    
    async def _log_ticket_status_change(self, ticket_id: str, new_status: str) -> None:
        """
        Log ticket status change for metrics.
        
        Args:
            ticket_id: Ticket ID
            new_status: New status
        """
        try:
            metric_entry = {
                "event": "ticket_status_changed",
                "ticket_id": ticket_id,
                "new_status": new_status,
                "timestamp": datetime.now(timezone.utc)
            }
            
            await self.metrics_collection.insert_one(metric_entry)
            
        except Exception as e:
            logger.error(f"Error logging status change metric: {e}")
    
    async def get_escalation_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get escalation metrics for a date range.
        
        Args:
            start_date: Start of date range (defaults to 30 days ago)
            end_date: End of date range (defaults to now)
        
        Returns:
            Dictionary with escalation metrics
        """
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        try:
            # Build query
            query = {
                "created_at": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
            
            # Get all tickets in range
            cursor = self.tickets_collection.find(query)
            tickets = await cursor.to_list(length=10000)
            
            # Calculate metrics
            total_tickets = len(tickets)
            
            if total_tickets == 0:
                return {
                    "total_tickets": 0,
                    "by_priority": {},
                    "by_status": {},
                    "by_reason": {},
                    "by_caller_type": {},
                    "avg_resolution_time_hours": None,
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    }
                }
            
            # Count by priority
            by_priority = {}
            for ticket in tickets:
                priority = ticket.get("priority", "unknown")
                by_priority[priority] = by_priority.get(priority, 0) + 1
            
            # Count by status
            by_status = {}
            for ticket in tickets:
                status = ticket.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1
            
            # Count by caller type
            by_caller_type = {}
            for ticket in tickets:
                caller_type = ticket.get("caller_type", "unknown")
                by_caller_type[caller_type] = by_caller_type.get(caller_type, 0) + 1
            
            # Count by escalation reason
            by_reason = {}
            for ticket in tickets:
                reason = ticket.get("escalation_reason", "unknown")
                # Simplify reason for grouping
                if "clarification" in reason.lower():
                    reason_key = "max_clarifications_reached"
                elif "confidence" in reason.lower():
                    reason_key = "low_confidence"
                elif "user request" in reason.lower():
                    reason_key = "user_requested_human"
                else:
                    reason_key = "other"
                
                by_reason[reason_key] = by_reason.get(reason_key, 0) + 1
            
            # Calculate average resolution time for resolved tickets
            resolved_tickets = [
                t for t in tickets 
                if t.get("status") in ["resolved", "closed"] and t.get("resolved_at")
            ]
            
            avg_resolution_time = None
            if resolved_tickets:
                total_resolution_time = 0
                for ticket in resolved_tickets:
                    created = ticket.get("created_at")
                    resolved = ticket.get("resolved_at")
                    if created and resolved:
                        delta = (resolved - created).total_seconds() / 3600  # hours
                        total_resolution_time += delta
                
                avg_resolution_time = total_resolution_time / len(resolved_tickets)
            
            return {
                "total_tickets": total_tickets,
                "by_priority": by_priority,
                "by_status": by_status,
                "by_reason": by_reason,
                "by_caller_type": by_caller_type,
                "avg_resolution_time_hours": round(avg_resolution_time, 2) if avg_resolution_time else None,
                "resolution_rate": round(len(resolved_tickets) / total_tickets * 100, 2) if total_tickets > 0 else 0,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating escalation metrics: {e}")
            return {
                "error": str(e),
                "total_tickets": 0
            }
    
    async def get_ticket_count_by_caller_type(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Get ticket counts grouped by caller type.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
        
        Returns:
            Dictionary mapping caller_type to count
        """
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        try:
            # Aggregate by caller type
            pipeline = [
                {
                    "$match": {
                        "created_at": {
                            "$gte": start_date,
                            "$lte": end_date
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$caller_type",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            cursor = self.tickets_collection.aggregate(pipeline)
            results = await cursor.to_list(length=100)
            
            # Convert to simple dict
            return {item["_id"]: item["count"] for item in results}
            
        except Exception as e:
            logger.error(f"Error getting ticket count by caller type: {e}")
            return {}
    
    # ============ Ticket Search & Filtering ============
    
    async def search_tickets(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        caller_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search tickets with various filters.
        
        Args:
            query: Text search in transcript
            status: Filter by status
            priority: Filter by priority
            caller_type: Filter by caller type
            limit: Maximum results
        
        Returns:
            List of matching tickets
        """
        try:
            search_query = {}
            
            if status:
                search_query["status"] = status
            
            if priority:
                search_query["priority"] = priority
            
            if caller_type:
                search_query["caller_type"] = caller_type
            
            if query:
                # Text search in escalation reason and transcript
                search_query["$or"] = [
                    {"escalation_reason": {"$regex": query, "$options": "i"}},
                    {"transcript.text": {"$regex": query, "$options": "i"}},
                    {"ticket_id": {"$regex": query, "$options": "i"}}
                ]
            
            cursor = self.tickets_collection.find(search_query).sort(
                [("created_at", -1)]
            ).limit(limit)
            
            tickets = await cursor.to_list(length=limit)
            
            # Remove MongoDB _id
            for ticket in tickets:
                ticket.pop("_id", None)
            
            return tickets
            
        except Exception as e:
            logger.error(f"Error searching tickets: {e}")
            return []
    
    # ============ Cleanup & Maintenance ============
    
    async def close_old_resolved_tickets(self, days: int = 30) -> int:
        """
        Automatically close tickets that have been resolved for a certain period.
        
        Args:
            days: Number of days after resolution to auto-close
        
        Returns:
            Number of tickets closed
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            result = await self.tickets_collection.update_many(
                {
                    "status": "resolved",
                    "resolved_at": {"$lt": cutoff_date}
                },
                {
                    "$set": {
                        "status": "closed",
                        "updated_at": datetime.now(timezone.utc),
                        "auto_closed": True
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Auto-closed {result.modified_count} old resolved tickets")
            
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error auto-closing old tickets: {e}")
            return 0
    
    async def delete_old_tickets(self, days: int = 365) -> int:
        """
        Delete tickets older than specified days (for data retention).
        
        Args:
            days: Age threshold for deletion
        
        Returns:
            Number of tickets deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            result = await self.tickets_collection.delete_many(
                {
                    "created_at": {"$lt": cutoff_date},
                    "status": {"$in": ["closed", "resolved"]}
                }
            )
            
            if result.deleted_count > 0:
                logger.info(f"Deleted {result.deleted_count} old tickets")
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting old tickets: {e}")
            return 0
    
    # ============ Operator Management ============
    
    async def get_available_operators(self) -> List[Dict[str, Any]]:
        """
        Get list of available operators for ticket assignment.
        
        Returns:
            List of available operator documents
        """
        try:
            cursor = self.operators_collection.find({
                "status": "available"
            }).sort([("active_tickets", 1)])  # Sort by least busy
            
            operators = await cursor.to_list(length=100)
            
            # Remove MongoDB _id
            for operator in operators:
                operator.pop("_id", None)
            
            return operators
            
        except Exception as e:
            logger.error(f"Error getting available operators: {e}")
            return []
    
    async def get_operator_stats(self, operator_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific operator.
        
        Args:
            operator_id: Operator ID
        
        Returns:
            Dictionary with operator statistics
        """
        try:
            operator = await self.operators_collection.find_one({"operator_id": operator_id})
            
            if not operator:
                return None
            
            # Get assigned tickets
            assigned_tickets = await self.tickets_collection.count_documents({
                "assigned_to.operator_id": operator_id
            })
            
            # Get resolved tickets
            resolved_tickets = await self.tickets_collection.count_documents({
                "assigned_to.operator_id": operator_id,
                "status": {"$in": ["resolved", "closed"]}
            })
            
            # Calculate average resolution time
            pipeline = [
                {
                    "$match": {
                        "assigned_to.operator_id": operator_id,
                        "status": {"$in": ["resolved", "closed"]},
                        "resolved_at": {"$exists": True}
                    }
                },
                {
                    "$project": {
                        "resolution_time": {
                            "$divide": [
                                {"$subtract": ["$resolved_at", "$created_at"]},
                                3600000  # Convert ms to hours
                            ]
                        }
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_resolution_time": {"$avg": "$resolution_time"}
                    }
                }
            ]
            
            cursor = self.tickets_collection.aggregate(pipeline)
            results = await cursor.to_list(length=1)
            avg_resolution_time = results[0]["avg_resolution_time"] if results else None
            
            return {
                "operator_id": operator_id,
                "name": operator.get("name"),
                "total_tickets_assigned": assigned_tickets,
                "total_tickets_resolved": resolved_tickets,
                "active_tickets": operator.get("active_tickets", 0),
                "avg_resolution_time_hours": round(avg_resolution_time, 2) if avg_resolution_time else None,
                "resolution_rate": round(resolved_tickets / assigned_tickets * 100, 2) if assigned_tickets > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting operator stats: {e}")
            return None