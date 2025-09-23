# ==================== config/settings.py ====================
"""Configuration settings for the AI Receptionist system."""

import os
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseModel):
    """Database configuration."""
    
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "ai_receptionist"
    
    
class TwilioSettings(BaseModel):
    """Twilio configuration."""
    
    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    phone_number: Optional[str] = None


class LLMSettings(BaseModel):
    """LLM configuration."""
    
    google_api_key: Optional[str] = None
    model_name: str = "gemini-pro"
    max_tokens: int = 1000
    temperature: float = 0.7


class EmbeddingSettings(BaseModel):
    """Embedding configuration."""
    
    chunk_size: int = 1000
    chunk_overlap: int = 100
    embedding_model: str = "all-MiniLM-L6-v2"


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # Components
    database: DatabaseSettings = DatabaseSettings()
    twilio: TwilioSettings = TwilioSettings()
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


# Global settings instance
settings = Settings()