# ============================== tests/test_unit_models.py ==============================
import pytest
from src.models.workflow_models import WorkflowState, CallerType, Intent
from src.models.database_models import Client, Vendor


def test_workflow_state_defaults():
    state = WorkflowState()
    assert state.processed is False
    assert state.intent is None


def test_workflow_state_serialization():
    state = WorkflowState(caller_phone="+15551234567", intent=Intent.STATUS_CHECK)
    data = state.model_dump()
    assert "caller_phone" in data


def test_invalid_enum_raises():
    with pytest.raises(ValueError):
        WorkflowState(intent="NOT_A_VALID_INTENT")  # wrong type


def test_client_model_validation():
    client = Client(name="Jane Doe", phone="+15551234567")
    assert client.name == "Jane Doe"