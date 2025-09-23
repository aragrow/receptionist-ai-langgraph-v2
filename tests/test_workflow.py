# ==================== tests/test_workflow.py ====================
"""Tests for the AI Receptionist workflow."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.workflow.ai_receptionist_workflow import AIReceptionistWorkflow
from src.models.workflow_models import WorkflowState, CallerType, Intent
from src.models.database_models import Client


@pytest.fixture
def workflow():
    """Create workflow instance for testing."""
    return AIReceptionistWorkflow()


@pytest.mark.asyncio
async def test_workflow_initialization(workflow):
    """Test workflow initialization."""
    # Mock database connection
    workflow.db_service.connect = AsyncMock()
    
    await workflow.initialize()
    workflow.db_service.connect.assert_called_once()


@pytest.mark.asyncio
async def test_process_call_client(workflow):
    """Test processing call from existing client."""
    # Mock database methods
    workflow.db_service.connect = AsyncMock()
    workflow.db_service.disconnect = AsyncMock()
    workflow.db_service.find_client_by_phone = AsyncMock(return_value=Client(
        name="John Doe",
        email="john@example.com",
        phone="+15551234567",
        address="123 Main St",
        city="Anytown",
        state="CA",
        zip="12345"
    ))
    workflow.context_service.build_client_context = AsyncMock(return_value={})
    
    call_data = {
        "caller_phone": "+15551234567",
        "speech_text": "What's the status of my repair?",
        "call_sid": "test123"
    }
    
    await workflow.initialize()
    result = await workflow.process_call(call_data)
    await workflow.cleanup()
    
    assert result.caller_type == CallerType.CLIENT
    assert result.intent == Intent.STATUS_CHECK
    assert result.processed is True