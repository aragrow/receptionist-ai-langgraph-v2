# ============================== tests/test_integration.py ==============================
import pytest
from unittest.mock import AsyncMock
from src.workflow.ai_receptionist_workflow import AIReceptionistWorkflow
from src.models.workflow_models import CallerType, Intent


@pytest.mark.asyncio
async def test_end_to_end_client_flow(monkeypatch):
    workflow = AIReceptionistWorkflow()
    workflow.db_service.find_client_by_phone = AsyncMock(return_value={"name": "John"})
    workflow.context_service.build_client_context = AsyncMock(return_value={"jobs": []})

    call_data = {"caller_phone": "+15551234567", "speech_text": "status?", "call_sid": "1"}
    result = await workflow.process_call(call_data)

    assert result.caller_type == CallerType.CLIENT
    assert result.intent in (Intent.STATUS_CHECK, Intent.GENERIC)