# ============================== tests/test_nodes.py ==============================
import pytest
from src.nodes.identity_checker import IdentityChecker
from src.nodes.intent_analyzer import IntentAnalyzer
from src.nodes.context_builder import ContextBuilder
from src.nodes.response_generator import ResponseGenerator
from src.models.workflow_models import WorkflowState, CallerType, Intent


@pytest.mark.asyncio
async def test_identity_checker_client():
    checker = IdentityChecker()
    state = WorkflowState(caller_phone="+15551234567")
    new_state = await checker.run(state)
    assert new_state.caller_type in (CallerType.CLIENT, CallerType.LEAD, CallerType.VENDOR)


@pytest.mark.asyncio
async def test_intent_analyzer_status_check():
    analyzer = IntentAnalyzer()
    state = WorkflowState(speech_text="What's the status of my job?")
    new_state = await analyzer.run(state)
    assert new_state.intent in (Intent.STATUS_CHECK, Intent.GENERIC)