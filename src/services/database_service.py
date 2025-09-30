# ==================== src/services/database_service.py ====================
"""Database service for MongoDB operations."""

import asyncio
import html
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
import sys
from config.settings import settings
from src.models.database_models import (
    Client, Property, Job, Visit, Vendor, KnowledgeBase, AgentActionPrompt
)


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(settings.database.mongodb_url)
        self.db = self.client[settings.database.database_name]
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
    
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
    
    async def find_agent_action_prompt(self, agent: str, action: str, level: int = 1) -> str:
        print("Searching for prompt:", repr(agent), repr(action), repr(level))
        try:
            result = await self.db.agent_action_prompts.find_one({"agent": agent, "action": action, "level": level, "active": True}, {"_id": 0, "agent": 0, "action": 0, "level": 0, "active": 0})
            print("Searching for prompt (repr):", repr(agent), repr(action), repr(level))
            print("DB name:", getattr(self.db, 'name', '<unknown>'))
            print("Collections:", await self.db.list_collection_names())
            print("Result:", result)
            result = result if result else None
        except Exception as e:
            print (f"Errror Finding Agent Action Prompt: {str(e)}")
            sys.exit(1)    

        return result    

    async def find_client_by_phone(self, phone: str) -> Optional[Client]:
        """
           Find client by phone number.
           The ** is Python's dictionary unpacking operator.It converts dictionary key-value pairs into named arguments
        """
        try:
            result = await self.db.clients.find_one({"phone": phone}, {"embeddings": 0})
            print("Searching for phone (repr):", repr(phone))
            print("Type:", type(phone))
            print("DB name:", getattr(self.db, 'name', '<unknown>'))
            print("Collections:", await self.db.list_collection_names())
            print("Result:", result)
            result = Client(**result) if result else None
        except Exception as e:
            print (f"Errror Finding Client: {str(e)}")
            sys.exit(1)    

        return result
    
    async def find_vendor_by_phone(self, phone: str) -> Optional[Vendor]:
        """Find vendor by phone number."""
        result = await self.db.vendors.find_one({"phone": phone})
        print("Searching for phone (repr):", repr(phone))
        print("Type:", type(phone))
        print("DB name:", getattr(self.db, 'name', '<unknown>'))
        print("Collections:", await self.db.list_collection_names())
        return Vendor(**result) if result else None
    
    async def get_client_properties(self, client_id: ObjectId) -> List[Property]:
        """Get all properties for a client."""
        cursor = self.db.properties.find({"client_id": client_id})
        properties = []
        async for doc in cursor:
            properties.append(Property(**doc))
        return properties
    
    async def get_property_jobs(self, property_id: ObjectId) -> List[Job]:
        """Get all jobs for a property."""
        cursor = self.db.jobs.find({"property_id": property_id})
        jobs = []
        async for doc in cursor:
            jobs.append(Job(**doc))
        return jobs
    
    async def get_job_visits(self, job_id: ObjectId) -> List[Visit]:
        """Get all visits for a job."""
        cursor = self.db.visits.find({"job_id": job_id})
        visits = []
        async for doc in cursor:
            visits.append(Visit(**doc))
        return visits
    
    async def get_vendor_jobs(self, vendor_id: ObjectId) -> List[Job]:
        """Get all jobs for a vendor."""
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