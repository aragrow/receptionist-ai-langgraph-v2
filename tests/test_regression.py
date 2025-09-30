# ============================== tests/test_regression.py ==============================
import pytest
from src.models.workflow_models import WorkflowState, CallerType, Intent

@pytest.mark.asyncio
async def test_client_status_end_to_end(ai_receptionist_realistic):
    # TODO: simulate actual conversation loop with a mock LLM
    pass

@pytest.mark.asyncio
async def test_vendor_reschedule(ai_receptionist_realistic):
    # TODO: write a simulated vendor flow
    pass

@pytest.mark.asyncio
async def test_lead_general_inquiry(ai_receptionist_realistic):
    # TODO: write a simulated lead flow
    pass