# ==================== src/models/database_models.py ====================
"""Database models for MongoDB collections using Pydantic."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId class for Pydantic validation."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        """Ensure ObjectId is represented as string in JSON schema."""
        schema = handler(schema)
        schema.update(type="string")
        return schema


class BaseDocument(BaseModel):
    """Base document with common fields for all collections."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
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
    scheduled_date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    completion_date: Optional[datetime] = None


class Visit(BaseDocument):
    """Visit model."""

    job_id: PyObjectId
    visit_date: datetime = Field(default_factory=datetime.utcnow)
    technician_name: str
    report: Optional[str] = None
    status: str = "scheduled"  # scheduled, completed, canceled


class KnowledgeBase(BaseDocument):
    """Knowledge base entry."""

    entity_id: PyObjectId  # Reference to any entity
    entity_type: str  # client, property, job, visit, vendor
    content: str
    embedding: List[float] = Field(default_factory=list)
