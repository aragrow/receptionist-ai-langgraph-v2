# ==================== src/services/database_service.py ====================
"""Database service for MongoDB operations."""

import asyncio
import html
import logging
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from config.settings import settings
from src.models.database_models import (
    Client, Property, Job, Visit, Vendor, KnowledgeBase, AgentActionPrompt
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._prompt_cache: Dict[str, str] = {}  # Cache for prompts
        self._cache_ttl: int = 3600  # Cache TTL in seconds (1 hour)
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def connect(self):
        """Connect to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(settings.database.mongodb_url)
            self.db = self.client[settings.database.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB: {settings.database.database_name}")
            
            # Create indexes for performance
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("📡 Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes for common queries."""
        try:
            # Clients - index on phone for fast lookup
            await self.db.clients.create_index("phone")
            
            # Vendors - index on phone
            await self.db.vendors.create_index("phone")
            
            # Agent prompts - compound index for fast retrieval
            await self.db.agent_action_prompts.create_index([
                ("agent", 1),
                ("action", 1),
                ("level", 1),
                ("active", 1)
            ])
            
            # Sessions - index for cleanup and retrieval
            await self.db.sessions.create_index("session_id", unique=True)
            await self.db.sessions.create_index("created_at")
            await self.db.sessions.create_index("expires_at")
            
            # Routing logs - index for analytics
            await self.db.routing_logs.create_index("session_id")
            await self.db.routing_logs.create_index("timestamp")
            
            logger.debug("✅ Database indexes created/verified")
            
        except Exception as e:
            logger.warning(f"⚠️ Index creation warning: {e}")
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data before saving to database."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Remove potentially harmful characters
                sanitized[key] = html.escape(value.strip())
            else:
                sanitized[key] = value
        return sanitized
    
    # ============ Agent Prompt Methods ============
    
    async def find_agent_action_prompt(
        self, 
        agent: str, 
        action: str, 
        level: int = 1
    ) -> Optional[str]:
        """
        Find agent action prompt from database.
        
        Args:
            agent: Agent name (e.g., "receptionist")
            action: Action name (e.g., "l1_classification")
            level: Prompt level/version (default: 1)
        
        Returns:
            Prompt string if found, None otherwise
        """
        try:
            # Check cache first
            cache_key = f"{agent}:{action}:{level}"
            
            if cache_key in self._prompt_cache:
                # Check if cache is still valid
                if cache_key in self._cache_timestamps:
                    age = (datetime.now(timezone.utc) - self._cache_timestamps[cache_key]).total_seconds()
                    if age < self._cache_ttl:
                        logger.debug(f"📦 Using cached prompt: {cache_key}")
                        return self._prompt_cache[cache_key]
            
            # Query database for active prompt
            print(f"Getting agent prompt from db: {self.db.name}, {agent}, {action}, {level}")
            result = await self.db.agent_action_prompts.find_one({
                "agent": agent,
                "action": action,
                "level": level,
            })
            
            if result and "prompt" in result:
                prompt = result["prompt"]
                
                # Cache the result
                self._prompt_cache[cache_key] = prompt
                self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
                
                logger.debug(f"✅ Retrieved prompt from DB: {agent}/{action}/level-{level}")
                return prompt
            
            # If not found with specified level, try to find any active prompt for this agent/action
            result = await self.db.agent_action_prompts.find_one({
                "agent": agent,
                "action": action,
                "active": True
            })
            
            if result and "prompt" in result:
                prompt = result["prompt"]
                logger.warning(
                    f"⚠️ Prompt level {level} not found, using level {result.get('level', 'unknown')}"
                )
                return prompt
            
            logger.error(
                f"❌ Prompt not found: agent={agent}, action={action}, level={level}"
            )
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding agent prompt: {e}")
            return None
    
    def clear_prompt_cache(self):
        """Clear the prompt cache."""
        self._prompt_cache.clear()
        self._cache_timestamps.clear()
        logger.info("🗑️ Prompt cache cleared")
    
    # ============ Client/Vendor Lookup Methods ============
    
    async def find_client_by_phone(self, phone: str) -> Optional[Client]:
        """
        Find client by phone number.
        
        Args:
            phone: Phone number (should be normalized)
        
        Returns:
            Client object if found, None otherwise
        """
        try:
            print(f"Getting clients by phone from db: {self.db}")
            result = await self.db.clients.find_one(
                {"phone": phone},
                {"embeddings": 0}  # Exclude embeddings for performance
            )
            
            if result:
                logger.info(f"✅ Found client: {result.get('name', 'Unknown')} ({phone})")
                return Client(**result)
            
            logger.debug(f"❌ Client not found: {phone}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding client by phone: {e}")
            return None
    
    async def find_vendor_by_phone(self, phone: str) -> Optional[Vendor]:
        """
        Find vendor by phone number.
        
        Args:
            phone: Phone number (should be normalized)
        
        Returns:
            Vendor object if found, None otherwise
        """
        try:
            print(f"Getting vendor by phone from db: {self.db}")
            result = await self.db.vendors.find_one({"phone": phone})
            
            if result:
                logger.info(f"✅ Found vendor: {result.get('name', 'Unknown')} ({phone})")
                return Vendor(**result)
            
            logger.debug(f"❌ Vendor not found: {phone}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding vendor by phone: {e}")
            return None
    
    # ============ Session Management Methods ============
    
    async def save_session(
        self,
        session_id: str,
        state_data: Dict[str, Any],
        ttl_minutes: int = 30
    ) -> bool:
        """
        Save session state to database.
        
        Args:
            session_id: Unique session identifier
            state_data: Session state data
            ttl_minutes: Time-to-live in minutes
        
        Returns:
            True if successful, False otherwise
        """
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
            
            session_doc = {
                "session_id": session_id,
                "state_data": state_data,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "expires_at": expires_at
            }
            
            # Upsert (update or insert)
            print(f"Saving sessions to db: {self.db}")
            await self.db.sessions.update_one(
                {"session_id": session_id},
                {"$set": session_doc},
                upsert=True
            )
            
            logger.debug(f"💾 Session saved: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving session: {e}")
            return False
    
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session state from database.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session state data if found and not expired, None otherwise
        """
        try:
            print(f"Getting sessions from db: {self.db}")
            result = await self.db.sessions.find_one({"session_id": session_id})
            
            if not result:
                logger.debug(f"❌ Session not found: {session_id}")
                return None
            
            # Check expiration
            if result.get("expires_at") and result["expires_at"] < datetime.now(timezone.utc):
                logger.info(f"⏰ Session expired: {session_id}")
                await self.delete_session(session_id)
                return None
            
            logger.debug(f"📂 Session loaded: {session_id}")
            return result.get("state_data")
            
        except Exception as e:
            logger.error(f"❌ Error loading session: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from database.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if deleted, False otherwise
        """
        try:
            print(f"Delete sessions from db: {self.db}")
            result = await self.db.sessions.delete_one({"session_id": session_id})
            
            if result.deleted_count > 0:
                logger.debug(f"🗑️ Session deleted: {session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error deleting session: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from database.
        
        Returns:
            Number of sessions deleted
        """
        try:
            print(f"Cleaning up expired sessionsfrom db: {self.db}")
            result = await self.db.sessions.delete_many({
                "expires_at": {"$lt": datetime.now(timezone.utc)}
            })
            
            if result.deleted_count > 0:
                logger.info(f"🧹 Cleaned up {result.deleted_count} expired sessions")
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up sessions: {e}")
            return 0
    
    # ============ Routing Log Methods ============
    
    async def log_routing_decision(
        self,
        session_id: str,
        from_tier: str,
        to_tier: str,
        reason: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log routing decision for analytics.
        
        Args:
            session_id: Session identifier
            from_tier: Source tier
            to_tier: Destination tier
            reason: Routing reason
            confidence: Confidence score
            metadata: Additional metadata
        
        Returns:
            True if logged successfully
        """
        try:
            log_entry = {
                "session_id": session_id,
                "from_tier": from_tier,
                "to_tier": to_tier,
                "reason": reason,
                "confidence": confidence,
                "timestamp": datetime.now(timezone.utc),
                "metadata": metadata or {}
            }
            print(f"Getting routing decisions from db: {self.db}")
            await self.db.routing_logs.insert_one(log_entry)
            logger.debug(f"📊 Routing logged: {from_tier} → {to_tier}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error logging routing: {e}")
            return False
    
    async def get_routing_history(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get routing history for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            List of routing log entries
        """
        try:
            print(f"Getting routing jobs property from db: {self.db}")
            cursor = self.db.routing_logs.find(
                {"session_id": session_id}
            ).sort("timestamp", 1)
            
            logs = []
            async for log in cursor:
                # Remove MongoDB _id for cleaner output
                log.pop("_id", None)
                logs.append(log)
            
            return logs
            
        except Exception as e:
            logger.error(f"❌ Error getting routing history: {e}")
            return []
    
    # ============ Existing Methods (from original file) ============
    
    async def get_client_properties(self, client_id: ObjectId) -> List[Property]:
        """Get all properties for a client."""
        cursor = self.db.properties.find({"client_id": client_id})
        properties = []
        async for doc in cursor:
            properties.append(Property(**doc))
        return properties
    
    async def get_property_jobs(self, property_id: ObjectId) -> List[Job]:
        """Get all jobs for a property."""
        print(f"Getting jobs for property from db: {self.db}")
        cursor = self.db.jobs.find({"property_id": property_id})
        jobs = []
        async for doc in cursor:
            jobs.append(Job(**doc))
        return jobs
    
    async def get_job_visits(self, job_id: ObjectId) -> List[Visit]:
        """Get all visits for a job."""
        print(f"Getting jobs visits for property from db: {self.db}")
        cursor = self.db.visits.find({"job_id": job_id})
        visits = []
        async for doc in cursor:
            visits.append(Visit(**doc))
        return visits
    
    async def get_vendor_jobs(self, vendor_id: ObjectId) -> List[Job]:
        """Get all jobs for a vendor."""
        print(f"Getting jobs for vendors from db: {self.db}")
        cursor = self.db.jobs.find({"vendor_id": vendor_id})
        jobs = []
        async for doc in cursor:
            jobs.append(Job(**doc))
        return jobs
    
    async def search_knowledge_base(
        self, 
        entity_ids: List[ObjectId], 
        query_embedding: List[float],
        limit: int = 10
    ) -> List[KnowledgeBase]:
        """Search knowledge base using vector similarity."""
        # Simple implementation - in production use vector search
        pipeline = [
            {"$match": {"entity_id": {"$in": entity_ids}}},
            {"$limit": limit}
        ]
        print(f"Search Knowledge base from db: {self.db}")
        cursor = self.db.knowledge_base.aggregate(pipeline)
        results = []
        async for doc in cursor:
            results.append(KnowledgeBase(**doc))
        return results
    
    async def save_knowledge_base_entry(self, entry: KnowledgeBase) -> ObjectId:
        """Save knowledge base entry."""
        sanitized_data = self._sanitize_data(entry.dict(by_alias=True))
        result = await self.db.knowledge_base.insert_one(sanitized_data)
        return result.inserted_id