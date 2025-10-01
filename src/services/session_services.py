"""
Session Service for managing multi-turn conversation state.

Handles session creation, state persistence, and conversation history tracking.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from src.models.workflow_models import WorkflowState
from src.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class SessionService:
    """
    Service for managing conversation sessions.
    
    Features:
    - Create and manage unique session IDs
    - Persist WorkflowState at each tier transition
    - Track conversation history
    - Auto-expire old sessions
    - Provide session analytics
    """
    
    def __init__(
        self,
        db_service: DatabaseService,
        default_ttl_minutes: int = 30,
        max_conversation_history: int = 10
    ):
        """
        Initialize Session Service.
        
        Args:
            db_service: Database service instance
            default_ttl_minutes: Default session TTL (time-to-live) in minutes
            max_conversation_history: Maximum conversation turns to keep
        """
        self.db_service = db_service
        self.default_ttl_minutes = default_ttl_minutes
        self.max_conversation_history = max_conversation_history
        
        logger.info(
            f"SessionService initialized (TTL: {default_ttl_minutes}min, "
            f"Max history: {max_conversation_history})"
        )
    
    # ============ Session Creation ============
    
    def create_session_id(self, prefix: str = "sess") -> str:
        """
        Generate a unique session ID.
        
        Args:
            prefix: Prefix for session ID (default: "sess")
        
        Returns:
            Unique session ID (e.g., "sess-20251001-abc123def")
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        unique_id = str(uuid.uuid4()).replace("-", "")[:10]
        
        session_id = f"{prefix}-{timestamp}-{unique_id}"
        logger.info(f"🆔 Created session ID: {session_id}")
        
        return session_id
    
    async def create_session(
        self,
        initial_state: WorkflowState,
        ttl_minutes: Optional[int] = None
    ) -> str:
        """
        Create a new session with initial state.
        
        Args:
            initial_state: Initial workflow state
            ttl_minutes: Custom TTL (uses default if not provided)
        
        Returns:
            Session ID
        """
        # Generate session ID if not present
        if not initial_state.session_id:
            initial_state.session_id = self.create_session_id()
        
        session_id = initial_state.session_id
        ttl = ttl_minutes or self.default_ttl_minutes
        
        # Save initial state
        await self.save_state(session_id, initial_state, ttl_minutes=ttl)
        
        logger.info(f"📝 Session created: {session_id} (TTL: {ttl}min)")
        
        return session_id
    
    # ============ State Persistence ============
    
    async def save_state(
        self,
        session_id: str,
        state: WorkflowState,
        ttl_minutes: Optional[int] = None
    ) -> bool:
        """
        Save workflow state to database.
        
        Args:
            session_id: Session identifier
            state: Current workflow state
            ttl_minutes: Time-to-live in minutes
        
        Returns:
            True if successful
        """
        try:
            ttl = ttl_minutes or self.default_ttl_minutes
            
            # Convert Pydantic model to dict
            state_dict = state.model_dump(mode='json')
            
            # Add metadata
            state_dict["_metadata"] = {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "tier": state.current_tier.value if state.current_tier else "UNKNOWN",
                "turn_count": state.turn_count
            }
            
            # Save to database
            success = await self.db_service.save_session(
                session_id=session_id,
                state_data=state_dict,
                ttl_minutes=ttl
            )
            
            if success:
                logger.debug(f"💾 State saved: {session_id} (tier: {state.current_tier})")
            else:
                logger.error(f"❌ Failed to save state: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error saving state for {session_id}: {e}")
            return False
    
    async def load_state(self, session_id: str) -> Optional[WorkflowState]:
        """
        Load workflow state from database.
        
        Args:
            session_id: Session identifier
        
        Returns:
            WorkflowState if found and valid, None otherwise
        """
        try:
            # Load from database
            state_dict = await self.db_service.load_session(session_id)
            
            if not state_dict:
                logger.debug(f"❌ Session not found: {session_id}")
                return None
            
            # Remove metadata before reconstructing
            state_dict.pop("_metadata", None)
            
            # Reconstruct WorkflowState from dict
            state = WorkflowState(**state_dict)
            
            logger.debug(
                f"📂 State loaded: {session_id} "
                f"(tier: {state.current_tier}, turn: {state.turn_count})"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error loading state for {session_id}: {e}")
            return None
    
    async def delete_state(self, session_id: str) -> bool:
        """
        Delete session state.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if deleted successfully
        """
        success = await self.db_service.delete_session(session_id)
        
        if success:
            logger.info(f"🗑️ Session deleted: {session_id}")
        
        return success
    
    # ============ Conversation History ============
    
    async def append_message(
        self,
        session_id: str,
        role: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Append message to conversation history.
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant/system)
            text: Message text
            metadata: Optional metadata (intent, confidence, etc.)
        
        Returns:
            True if successful
        """
        try:
            # Load current state
            state = await self.load_state(session_id)
            
            if not state:
                logger.warning(f"⚠️ Cannot append message - session not found: {session_id}")
                return False
            
            # Create message entry
            message = {
                "role": role,
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "turn": state.turn_count
            }
            
            if metadata:
                message["metadata"] = metadata
            
            # Append to conversation history
            if not state.conversation_history:
                state.conversation_history = []
            
            state.conversation_history.append(message)
            
            # Trim history if too long
            if len(state.conversation_history) > self.max_conversation_history:
                state.conversation_history = state.conversation_history[-self.max_conversation_history:]
                logger.debug(f"✂️ Trimmed conversation history to {self.max_conversation_history} messages")
            
            # Save updated state
            await self.save_state(session_id, state)
            
            logger.debug(f"💬 Message appended ({role}): {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error appending message: {e}")
            return False
    
    def get_conversation_context(
        self,
        state: WorkflowState,
        max_turns: int = 3
    ) -> str:
        """
        Get formatted conversation context for prompts.
        
        Args:
            state: Current workflow state
            max_turns: Maximum recent turns to include
        
        Returns:
            Formatted conversation history string
        """
        if not state.conversation_history:
            return "No previous conversation."
        
        # Get recent messages
        recent = state.conversation_history[-max_turns * 2:]  # x2 for user+assistant pairs
        
        # Format messages
        lines = []
        for msg in recent:
            role = msg.get("role", "unknown").capitalize()
            text = msg.get("text", "")
            lines.append(f"{role}: {text}")
        
        return "\n".join(lines)
    
    # ============ Session Management ============
    
    async def extend_session(
        self,
        session_id: str,
        additional_minutes: int = 30
    ) -> bool:
        """
        Extend session TTL.
        
        Args:
            session_id: Session identifier
            additional_minutes: Minutes to add to expiration
        
        Returns:
            True if successful
        """
        try:
            state = await self.load_state(session_id)
            
            if not state:
                logger.warning(f"⚠️ Cannot extend - session not found: {session_id}")
                return False
            
            # Re-save with new TTL
            current_ttl = self.default_ttl_minutes + additional_minutes
            await self.save_state(session_id, state, ttl_minutes=current_ttl)
            
            logger.info(f"⏰ Session extended: {session_id} (+{additional_minutes}min)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error extending session: {e}")
            return False
    
    async def is_session_active(self, session_id: str) -> bool:
        """
        Check if session is still active (not expired).
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if session exists and is active
        """
        state = await self.load_state(session_id)
        return state is not None
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up all expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        count = await self.db_service.cleanup_expired_sessions()
        
        if count > 0:
            logger.info(f"🧹 Cleaned up {count} expired sessions")
        
        return count
    
    # ============ Session Analytics ============
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information and statistics.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session info dict or None if not found
        """
        try:
            state = await self.load_state(session_id)
            
            if not state:
                return None
            
            # Get routing history
            routing_history = await self.db_service.get_routing_history(session_id)
            
            info = {
                "session_id": session_id,
                "created_at": state.created_at.isoformat() if state.created_at else None,
                "updated_at": state.updated_at.isoformat() if state.updated_at else None,
                "current_tier": state.current_tier.value if state.current_tier else None,
                "current_agent": state.current_agent,
                "turn_count": state.turn_count,
                "caller_type": state.caller_type.value if state.caller_type else None,
                "caller_phone": state.caller_phone,
                "intent_l1": state.intent_l1.model_dump() if state.intent_l1 else None,
                "intent_l2": state.intent_l2.model_dump() if state.intent_l2 else None,
                "clarification_count": state.clarification_count,
                "requires_human_escalation": state.requires_human_escalation,
                "ticket_id": state.ticket_id,
                "conversation_turns": len(state.conversation_history) if state.conversation_history else 0,
                "routing_path": [
                    f"{log['from_tier']}→{log['to_tier']}" 
                    for log in routing_history
                ],
                "entities_collected": list(state.entities.keys()) if state.entities else []
            }
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Error getting session info: {e}")
            return None
    
    async def get_active_sessions_count(self) -> int:
        """
        Get count of active sessions.
        
        Returns:
            Number of active sessions
        """
        try:
            count = await self.db_service.db.sessions.count_documents({
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            
            return count
            
        except Exception as e:
            logger.error(f"❌ Error counting sessions: {e}")
            return 0
    
    async def get_recent_sessions(
        self,
        limit: int = 10,
        caller_phone: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent sessions, optionally filtered by caller.
        
        Args:
            limit: Maximum number of sessions to return
            caller_phone: Filter by caller phone number
        
        Returns:
            List of session summaries
        """
        try:
            query = {
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            }
            
            if caller_phone:
                query["state_data.caller_phone"] = caller_phone
            
            cursor = self.db_service.db.sessions.find(query).sort(
                "updated_at", -1
            ).limit(limit)
            
            sessions = []
            async for doc in cursor:
                state_data = doc.get("state_data", {})
                sessions.append({
                    "session_id": doc["session_id"],
                    "caller_phone": state_data.get("caller_phone"),
                    "caller_type": state_data.get("caller_type"),
                    "current_tier": state_data.get("current_tier"),
                    "turn_count": state_data.get("turn_count", 0),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                    "expires_at": doc.get("expires_at")
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Error getting recent sessions: {e}")
            return []
    
    # ============ Conversation Export ============
    
    async def export_conversation(
        self,
        session_id: str,
        include_metadata: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Export full conversation transcript for archival or analysis.
        
        Args:
            session_id: Session identifier
            include_metadata: Include routing and state metadata
        
        Returns:
            Complete conversation export or None if not found
        """
        try:
            state = await self.load_state(session_id)
            
            if not state:
                return None
            
            export = {
                "session_id": session_id,
                "caller_phone": state.caller_phone,
                "caller_type": state.caller_type.value if state.caller_type else None,
                "started_at": state.created_at.isoformat() if state.created_at else None,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "total_turns": state.turn_count,
                "conversation": state.conversation_history or []
            }
            
            if include_metadata:
                routing_history = await self.db_service.get_routing_history(session_id)
                
                export["metadata"] = {
                    "intent_l1": state.intent_l1.model_dump() if state.intent_l1 else None,
                    "intent_l2": state.intent_l2.model_dump() if state.intent_l2 else None,
                    "entities": state.entities,
                    "routing_history": routing_history,
                    "clarification_count": state.clarification_count,
                    "escalated": state.requires_human_escalation,
                    "ticket_id": state.ticket_id,
                    "final_tier": state.current_tier.value if state.current_tier else None,
                    "final_agent": state.current_agent
                }
            
            return export
            
        except Exception as e:
            logger.error(f"❌ Error exporting conversation: {e}")
            return None