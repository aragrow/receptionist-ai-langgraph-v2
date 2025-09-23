# ==================== src/models/database_models.py ====================
"""Database models for MongoDB collections."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from pydantic.json_schema import JsonSchemaValue
from pydantic import GetJsonSchemaHandler
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId class for Pydantic."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: JsonSchemaValue, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        schema = handler(schema)
        schema.update(type="string")
        return schema


class BaseDocument(BaseModel):
    """Base document with common fields."""
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class Client(BaseDocument):
    """Client model."""
    
    name: str
    email: str
    phone: str
    address: str
    address_1: Optional[str] = None
    city: str
    state: str
    zip: str
    country: str = "US"


class Property(BaseDocument):
    """Property model."""
    
    client_id: PyObjectId
    address: str
    address_1: Optional[str] = None
    city: str
    state: str
    zip: str
    country: str = "US"
    property_type: str  # residential, commercial
    size: Optional[str] = None


class Vendor(BaseDocument):
    """Vendor model."""
    
    name: str
    contact_person: Optional[str] = None
    phone: str
    email: str
    address: str
    address_1: Optional[str] = None
    city: str
    state: str
    zip: str
    country: str = "US"
    service_type: str  # plumbing, electrical, landscaping


class Job(BaseDocument):
    """Job model."""
    
    property_id: PyObjectId
    vendor_id: PyObjectId
    title: str
    description: str
    status: str = "pending"  # pending, in-progress, completed
    scheduled_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None


class Visit(BaseDocument):
    """Visit model."""
    
    job_id: PyObjectId
    visit_date: datetime
    technician_name: str
    report: Optional[str] = None
    status: str = "scheduled"  # scheduled, completed, canceled


class KnowledgeBase(BaseDocument):
    """Knowledge base entry."""
    
    entity_id: PyObjectId  # Reference to any entity
    entity_type: str  # client, property, job, visit, vendor
    content: str
    embedding: List[float] = Field(default_factory=list)
