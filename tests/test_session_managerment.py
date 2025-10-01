# ==================== src/test/test_session_management.py ====================

"""
Test Suite for Session Management (Phase 7).

Tests all session service functionality including:
- Session creation and persistence
- State loading and saving
- Conversation history management
- Session expiration and cleanup
- Multi-turn conversation support
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.session_service import SessionService
from src.services.database_service import DatabaseService
from src.models.workflow_models import WorkflowState, CallerType, AgentTier, IntentL1


# ============ Fixtures ============

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_service():
    """Provide database service for tests."""
    service = DatabaseService()
    await service.connect()
    yield service
    await service.disconnect()


@pytest.fixture(scope="function")
async def session_service(db_service):
    """Provide session service for tests."""
    service = SessionService(
        db_service=db_service,
        default_ttl_minutes=30,
        max_conversation_history=10
    )
    yield service


@pytest.fixture
def sample_workflow_state():
    """Create a sample WorkflowState for testing."""
    return WorkflowState(
        session_id=None,  # Will be generated
        caller_phone="555-123-4567",
        speech_text="I need to schedule a cleaning",
        caller_type=CallerType.CLIENT,
        current_tier=AgentTier.L1,
        turn_count=1,
        intent_l1=IntentL1(
            name="scheduling",
            confidence=0.92
        ),
        entities={"service_type": "cleaning"},
        conversation_history=[],
        routing_history=[]
    )


# ============ Test Session Creation ============

@pytest.mark.asyncio
async def test_create_session_id(session_service):
    """Test session ID generation."""
    session_id = session_service.create_session_id()
    
    assert session_id is not None
    assert session_id.startswith("sess-")
    assert len(session_id) > 15  # sess-YYYYMMDD-xxxxx
    
    # Test custom prefix
    custom_id = session_service.create_session_id(prefix="test")
    assert custom_id.startswith("test-")


@pytest.mark.asyncio
async def test_create_session(session_service, sample_workflow_state):
    """Test session creation with initial state."""
    session_id = await session_service.create_session(
        initial_state=sample_workflow_state,
        ttl_minutes=30
    )
    
    assert session_id is not None
    assert sample_workflow_state.session_id == session_id
    
    # Verify session was saved
    loaded_state = await session_service.load_state(session_id)
    assert loaded_state is not None
    assert loaded_state.caller_phone == "555-123-4567"
    
    # Cleanup
    await session_service.delete_state(session_id)


# ============ Test State Persistence ============

@pytest.mark.asyncio
async def test_save_and_load_state(session_service, sample_workflow_state):
    """Test saving and loading workflow state."""
    # Create session
    session_id = session_service.create_session_id()
    sample_workflow_state.session_id = session_id
    
    # Save state
    success = await session_service.save_state(
        session_id=session_id,
        state=sample_workflow_state,
        ttl_minutes=30
    )
    
    assert success is True
    
    # Load state
    loaded_state = await session_service.load_state(session_id)
    
    assert loaded_state is not None
    assert loaded_state.session_id == session_id
    assert loaded_state.caller_phone == sample_workflow_state.caller_phone
    assert loaded_state.speech_text == sample_workflow_state.speech_text
    assert loaded_state.caller_type == sample_workflow_state.caller_type
    assert loaded_state.turn_count == sample_workflow_state.turn_count
    
    # Cleanup
    await session_service.delete_state(session_id)


@pytest.mark.asyncio
async def test_update_existing_state(session_service, sample_workflow_state):
    """Test updating an existing session state."""
    # Create session
    session_id = await session_service.create_session(sample_workflow_state)
    
    # Load and modify
    loaded_state = await session_service.load_state(session_id)
    loaded_state.turn_count = 2
    loaded_state.speech_text = "What about next Tuesday?"
    
    # Save updated state
    await session_service.save_state(session_id, loaded_state)
    
    # Reload and verify
    reloaded_state = await session_service.load_state(session_id)
    assert reloaded_state.turn_count == 2
    assert reloaded_state.speech_text == "What about next Tuesday?"
    
    # Cleanup
    await session_service.delete_state(session_id)


# ============ Test Conversation History ============

@pytest.mark.asyncio
async def test_append_message(session_service, sample_workflow_state):
    """Test appending messages to conversation history."""
    # Create session
    session_id = await session_service.create_session(sample_workflow_state)
    
    # Append user message
    success = await session_service.append_message(
        session_id=session_id,
        role="user",
        text="I need a cleaning service",
        metadata={"intent": "scheduling"}
    )
    
    assert success is True
    
    # Append assistant message
    await session_service.append_message(
        session_id=session_id,
        role="assistant",
        text="I'd be happy to help schedule a cleaning. What date works for you?",
        metadata={"tier": "L2"}
    )
    
    # Load state and verify
    state = await session_service.load_state(session_id)
    assert len(state.conversation_history) == 2
    assert state.conversation_history[0]["role"] == "user"
    assert state.conversation_history[1]["role"] == "assistant"
    assert "metadata" in state.conversation_history[0]
    
    # Cleanup
    await session_service.delete_state(session_id)


@pytest.mark.asyncio
async def test_conversation_history_truncation(session_service, sample_workflow_state):
    """Test that conversation history is truncated to max length."""
    # Create session with small max history
    service = SessionService(
        db_service=session_service.db_service,
        default_ttl_minutes=30,
        max_conversation_history=3  # Small limit for testing
    )
    
    session_id = await service.create_session(sample_workflow_state)
    
    # Add more messages than the limit
    for i in range(5):
        await service.append_message(
            session_id=session_id,
            role="user" if i % 2 == 0 else "assistant",
            text=f"Message {i}"
        )
    
    # Load and verify truncation
    state = await service.load_state(session_id)
    assert len(state.conversation_history) == 3  # Should be truncated
    assert state.conversation_history[0]["text"] == "Message 2"  # Oldest kept
    assert state.conversation_history[-1]["text"] == "Message 4"  # Newest
    
    # Cleanup
    await service.delete_state(session_id)


@pytest.mark.asyncio
async def test_get_conversation_context(session_service, sample_workflow_state):
    """Test conversation context formatting."""
    # Add conversation history
    sample_workflow_state.conversation_history = [
        {"role": "user", "text": "Hello"},
        {"role": "assistant", "text": "Hi there!"},
        {"role": "user", "text": "I need help"}
    ]
    
    context = session_service.get_conversation_context(
        state=sample_workflow_state,
        max_turns=2
    )
    
    assert "User: Hello" in context or "user: Hello" in context.lower()
    assert "Assistant: Hi there!" in context or "assistant: Hi there!" in context.lower()


# ============ Test Session Management ============

@pytest.mark.asyncio
async def test_is_session_active(session_service, sample_workflow_state):
    """Test checking if session is active."""
    # Create session
    session_id = await session_service.create_session(sample_workflow_state)
    
    # Check active
    is_active = await session_service.is_session_active(session_id)
    assert is_active is True
    
    # Delete session
    await session_service.delete_state(session_id)
    
    # Check inactive
    is_active = await session_service.is_session_active(session_id)
    assert is_active is False


@pytest.mark.asyncio
async def test_extend_session(session_service, sample_workflow_state):
    """Test extending session TTL."""
    # Create session
    session_id = await session_service.create_session(
        sample_workflow_state,
        ttl_minutes=10
    )
    
    # Extend session
    success = await session_service.extend_session(
        session_id=session_id,
        additional_minutes=20
    )
    
    assert success is True
    
    # Verify session still active
    is_active = await session_service.is_session_active(session_id)
    assert is_active is True
    
    # Cleanup
    await session_service.delete_state(session_id)


@pytest.mark.asyncio
async def test_delete_session(session_service, sample_workflow_state):
    """Test session deletion."""
    # Create session
    session_id = await session_service.create_session(sample_workflow_state)
    
    # Verify exists
    state = await session_service.load_state(session_id)
    assert state is not None
    
    # Delete
    success = await session_service.delete_state(session_id)
    assert success is True
    
    # Verify deleted
    state = await session_service.load_state(session_id)
    assert state is None


# ============ Test Session Expiration ============

@pytest.mark.asyncio
async def test_session_expiration(session_service, sample_workflow_state):
    """Test that expired sessions are not loaded."""
    # Create session with very short TTL (1 second)
    session_id = session_service.create_session_id()
    sample_workflow_state.session_id = session_id
    
    # Manually save with past expiration
    await session_service.db_service.save_session(
        session_id=session_id,
        state_data=sample_workflow_state.model_dump(mode='json'),
        ttl_minutes=-1  # Already expired
    )
    
    # Try to load - should return None
    state = await session_service.load_state(session_id)
    assert state is None  # Expired session should not be loaded


@pytest.mark.asyncio
async def test_cleanup_expired_sessions(session_service, sample_workflow_state):
    """Test cleanup of expired sessions."""
    # Create multiple sessions with different expiration times
    expired_ids = []
    active_ids = []
    
    # Create 3 expired sessions
    for i in range(3):
        session_id = session_service.create_session_id()
        sample_workflow_state.session_id = session_id
        
        await session_service.db_service.save_session(
            session_id=session_id,
            state_data=sample_workflow_state.model_dump(mode='json'),
            ttl_minutes=-1  # Expired
        )
        expired_ids.append(session_id)
    
    # Create 2 active sessions
    for i in range(2):
        session_id = await session_service.create_session(
            sample_workflow_state,
            ttl_minutes=30
        )
        active_ids.append(session_id)
    
    # Run cleanup
    cleaned_count = await session_service.cleanup_expired_sessions()
    
    assert cleaned_count >= 3  # At least our 3 expired sessions
    
    # Verify expired sessions are gone
    for session_id in expired_ids:
        state = await session_service.load_state(session_id)
        assert state is None
    
    # Verify active sessions still exist
    for session_id in active_ids:
        state = await session_service.load_state(session_id)
        assert state is not None
    
    # Cleanup active sessions
    for session_id in active_ids:
        await session_service.delete_state(session_id)


# ============ Test Session Analytics ============

@pytest.mark.asyncio
async def test_get_session_info(session_service, sample_workflow_state):
    """Test retrieving session information."""
    # Create session with some activity
    session_id = await session_service.create_session(sample_workflow_state)
    
    # Add some messages
    await session_service.append_message(
        session_id=session_id,
        role="user",
        text="Hello"
    )
    await session_service.append_message(
        session_id=session_id,
        role="assistant",
        text="Hi there!"
    )
    
    # Log a routing decision
    await session_service.db_service.log_routing_decision(
        session_id=session_id,
        from_tier="L1",
        to_tier="L2",
        reason="High confidence classification",
        confidence=0.92
    )
    
    # Get session info
    info = await session_service.get_session_info(session_id)
    
    assert info is not None
    assert info["session_id"] == session_id
    assert info["caller_phone"] == "555-123-4567"
    assert info["turn_count"] == 1
    assert info["conversation_turns"] == 2
    assert len(info["routing_path"]) > 0
    
    # Cleanup
    await session_service.delete_state(session_id)


@pytest.mark.asyncio
async def test_get_active_sessions_count(session_service, sample_workflow_state):
    """Test counting active sessions."""
    initial_count = await session_service.get_active_sessions_count()
    
    # Create 3 new sessions
    session_ids = []
    for i in range(3):
        session_id = await session_service.create_session(sample_workflow_state)
        session_ids.append(session_id)
    
    # Count should increase
    new_count = await session_service.get_active_sessions_count()
    assert new_count >= initial_count + 3
    
    # Cleanup
    for session_id in session_ids:
        await session_service.delete_state(session_id)


@pytest.mark.asyncio
async def test_get_recent_sessions(session_service, sample_workflow_state):
    """Test retrieving recent sessions."""
    # Create sessions with different phone numbers
    session_ids = []
    
    for i, phone in enumerate(["555-111-1111", "555-222-2222", "555-111-1111"]):
        state = sample_workflow_state.model_copy(deep=True)
        state.caller_phone = phone
        session_id = await session_service.create_session(state)
        session_ids.append(session_id)
    
    # Get all recent sessions
    all_sessions = await session_service.get_recent_sessions(limit=10)
    assert len(all_sessions) >= 3
    
    # Filter by phone number
    filtered_sessions = await session_service.get_recent_sessions(
        caller_phone="555-111-1111",
        limit=10
    )
    
    # Should have at least 2 sessions with this phone
    matching = [s for s in filtered_sessions if s.get("caller_phone") == "555-111-1111"]
    assert len(matching) >= 2
    
    # Cleanup
    for session_id in session_ids:
        await session_service.delete_state(session_id)


# ============ Test Conversation Export ============

@pytest.mark.asyncio
async def test_export_conversation(session_service, sample_workflow_state):
    """Test exporting full conversation."""
    # Create session with activity
    session_id = await session_service.create_session(sample_workflow_state)
    
    # Add conversation
    await session_service.append_message(
        session_id=session_id,
        role="user",
        text="I need help",
        metadata={"intent": "support"}
    )
    await session_service.append_message(
        session_id=session_id,
        role="assistant",
        text="Sure, what do you need?",
        metadata={"tier": "L2"}
    )
    
    # Add routing log
    await session_service.db_service.log_routing_decision(
        session_id=session_id,
        from_tier="L1",
        to_tier="L2",
        reason="Test routing",
        confidence=0.95
    )
    
    # Export with metadata
    export = await session_service.export_conversation(
        session_id=session_id,
        include_metadata=True
    )
    
    assert export is not None
    assert export["session_id"] == session_id
    assert export["caller_phone"] == "555-123-4567"
    assert len(export["conversation"]) == 2
    assert "metadata" in export
    assert len(export["metadata"]["routing_history"]) > 0
    
    # Export without metadata
    export_no_meta = await session_service.export_conversation(
        session_id=session_id,
        include_metadata=False
    )
    
    assert "metadata" not in export_no_meta
    
    # Cleanup
    await session_service.delete_state(session_id)


# ============ Test Multi-Turn Conversation Flow ============

@pytest.mark.asyncio
async def test_multi_turn_conversation(session_service):
    """Test complete multi-turn conversation flow."""
    # Turn 1: Initial request
    state = WorkflowState(
        session_id=None,
        caller_phone="555-999-8888",
        speech_text="I need to schedule a cleaning",
        caller_type=CallerType.CLIENT,
        current_tier=AgentTier.L1,
        turn_count=1
    )
    
    session_id = await session_service.create_session(state)
    
    await session_service.append_message(
        session_id=session_id,
        role="user",
        text="I need to schedule a cleaning"
    )
    await session_service.append_message(
        session_id=session_id,
        role="assistant",
        text="I'd be happy to help. What date works for you?"
    )
    
    # Turn 2: Provide date
    state = await session_service.load_state(session_id)
    state.speech_text = "How about next Tuesday?"
    state.turn_count = 2
    state.current_tier = AgentTier.L2
    
    await session_service.save_state(session_id, state)
    await session_service.append_message(
        session_id=session_id,
        role="user",
        text="How about next Tuesday?"
    )
    await session_service.append_message(
        session_id=session_id,
        role="assistant",
        text="Tuesday works! What time would you prefer?"
    )
    
    # Turn 3: Provide time
    state = await session_service.load_state(session_id)
    state.speech_text = "10 AM would be great"
    state.turn_count = 3
    state.current_tier = AgentTier.L3
    
    await session_service.save_state(session_id, state)
    await session_service.append_message(
        session_id=session_id,
        role="user",
        text="10 AM would be great"
    )
    await session_service.append_message(
        session_id=session_id,
        role="assistant",
        text="Perfect! Your cleaning is scheduled for Tuesday at 10 AM."
    )
    
    # Verify final state
    final_state = await session_service.load_state(session_id)
    assert final_state.turn_count == 3
    assert len(final_state.conversation_history) == 6  # 3 user + 3 assistant
    assert final_state.current_tier == AgentTier.L3
    
    # Cleanup
    await session_service.delete_state(session_id)


# ============ Test Error Handling ============

@pytest.mark.asyncio
async def test_load_nonexistent_session(session_service):
    """Test loading a session that doesn't exist."""
    state = await session_service.load_state("nonexistent-session-id")
    assert state is None


@pytest.mark.asyncio
async def test_append_message_nonexistent_session(session_service):
    """Test appending message to nonexistent session."""
    success = await session_service.append_message(
        session_id="nonexistent-session-id",
        role="user",
        text="Hello"
    )
    
    # Should return False (session not found)
    assert success is False


@pytest.mark.asyncio
async def test_delete_nonexistent_session(session_service):
    """Test deleting a nonexistent session."""
    success = await session_service.delete_state("nonexistent-session-id")
    
    # Should return False (nothing to delete)
    assert success is False


@pytest.mark.asyncio
async def test_get_info_nonexistent_session(session_service):
    """Test getting info for nonexistent session."""
    info = await session_service.get_session_info("nonexistent-session-id")
    assert info is None


# ============ Run Tests ============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])