# ==================== src/api/test_router.py ====================

"""
Comprehensive Router Tests

Tests for all API routers including auth, admin, webhooks, and core functionality.
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# Import routers
from src.api.call_router import router as call_router
from src.api.session_router import router as session_router
from src.api.feedback_router import router as feedback_router
from src.api.improvement_router import router as improvement_router
from src.api.auth_router import router as auth_router
from src.api.admin_router import router as admin_router
from src.api.webhook_router import router as webhook_router


# ============ Fixtures ============

@pytest.fixture
def app():
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(call_router)
    app.include_router(session_router, prefix="/sessions")
    app.include_router(feedback_router, prefix="/feedback")
    app.include_router(improvement_router, prefix="/improvements")
    app.include_router(auth_router, prefix="/auth")
    app.include_router(admin_router, prefix="/admin")
    app.include_router(webhook_router, prefix="/webhooks")
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_services():
    """Mock service container"""
    services = Mock()
    services.workflow_runner = AsyncMock()
    services.session_service = AsyncMock()
    services.feedback_service = AsyncMock()
    services.db_service = Mock()
    services.db_service.db = AsyncMock()
    return services


@pytest.fixture
def auth_token():
    """Generate test auth token"""
    from src.api.auth_router import create_access_token
    return create_access_token({"sub": "test_user_123", "email": "test@example.com", "role": "user"})


@pytest.fixture
def admin_token():
    """Generate test admin token"""
    from src.api.auth_router import create_access_token
    return create_access_token({"sub": "admin_123", "email": "admin@example.com", "role": "admin"})


# ============ Call Router Tests ============

class TestCallRouter:
    """Tests for call processing router"""
    
    @patch('src.api.call_router.get_services')
    def test_process_call_success(self, mock_get_services, client, mock_services):
        """Test successful call processing"""
        # Setup
        mock_get_services.return_value = mock_services
        
        mock_result = Mock()
        mock_result.session_id = "session_123"
        mock_result.caller_type = Mock(value="client")
        mock_result.intent_name = "scheduling"
        mock_result.response_text = "How can I help you?"
        mock_result.current_tier = Mock(value="L1")
        mock_result.conversation_history = []
        mock_result.requires_human_escalation = False
        mock_result.ticket_id = None
        mock_result.next_action = None
        
        mock_services.workflow_runner.process_call = AsyncMock(return_value=mock_result)
        mock_services.session_service.load_session = AsyncMock(return_value=None)
        mock_services.session_service.save_session = AsyncMock()
        mock_services.session_service.cleanup_expired_sessions = AsyncMock()
        
        # Execute
        response = client.post("/process-call", json={
            "caller_phone": "555-1234",
            "speech_text": "I need to schedule a cleaning",
            "call_sid": "call_123"
        })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] == "session_123"
        assert data["caller_type"] == "client"
        assert data["intent"] == "scheduling"
        assert "help" in data["response"].lower()
    
    def test_process_call_missing_fields(self, client):
        """Test call processing with missing required fields"""
        response = client.post("/process-call", json={
            "caller_phone": "555-1234"
            # Missing speech_text and call_sid
        })
        
        assert response.status_code == 422  # Validation error
    
    @patch('src.api.call_router.get_services')
    def test_process_call_with_existing_session(self, mock_get_services, client, mock_services):
        """Test continuing existing session"""
        mock_get_services.return_value = mock_services
        
        existing_state = {"session_id": "session_123", "turn_count": 2}
        mock_services.session_service.load_session = AsyncMock(return_value=existing_state)
        
        mock_result = Mock()
        mock_result.session_id = "session_123"
        mock_result.caller_type = Mock(value="client")
        mock_result.intent_name = "billing"
        mock_result.response_text = "I can help with that"
        mock_result.current_tier = Mock(value="L2")
        mock_result.conversation_history = [{"role": "user", "text": "previous message"}]
        mock_result.requires_human_escalation = False
        mock_result.ticket_id = None
        mock_result.next_action = None
        
        mock_services.workflow_runner.process_call = AsyncMock(return_value=mock_result)
        mock_services.session_service.save_session = AsyncMock()
        mock_services.session_service.cleanup_expired_sessions = AsyncMock()
        
        response = client.post("/process-call", json={
            "caller_phone": "555-1234",
            "speech_text": "What about my bill?",
            "call_sid": "call_123",
            "session_id": "session_123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session_123"
        assert data["turn_count"] == 1  # From conversation_history


# ============ Session Router Tests ============

class TestSessionRouter:
    """Tests for session management router"""
    
    @patch('src.api.session_router.get_services')
    def test_get_session_info_success(self, mock_get_services, client, mock_services):
        """Test retrieving session information"""
        mock_get_services.return_value = mock_services
        
        session_info = {
            "session_id": "session_123",
            "created_at": "2025-10-01T10:00:00Z",
            "updated_at": "2025-10-01T10:05:00Z",
            "current_tier": "L2",
            "current_agent": "client_receptionist_l2",
            "turn_count": 3,
            "caller_type": "client",
            "caller_phone": "555-1234",
            "conversation_turns": 3,
            "routing_path": ["L1", "L2"],
            "requires_human_escalation": False
        }
        
        mock_services.session_service.get_session_info = AsyncMock(return_value=session_info)
        
        response = client.get("/sessions/session_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session_123"
        assert data["turn_count"] == 3
        assert data["current_tier"] == "L2"
    
    @patch('src.api.session_router.get_services')
    def test_get_session_not_found(self, mock_get_services, client, mock_services):
        """Test retrieving non-existent session"""
        mock_get_services.return_value = mock_services
        mock_services.session_service.get_session_info = AsyncMock(return_value=None)
        
        response = client.get("/sessions/nonexistent_session")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch('src.api.session_router.get_services')
    def test_delete_session_success(self, mock_get_services, client, mock_services):
        """Test deleting a session"""
        mock_get_services.return_value = mock_services
        mock_services.session_service.delete_session = AsyncMock(return_value=True)
        
        response = client.delete("/sessions/session_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()
    
    @patch('src.api.session_router.get_services')
    def test_export_session(self, mock_get_services, client, mock_services):
        """Test exporting session conversation"""
        mock_get_services.return_value = mock_services
        
        export_data = {
            "session_id": "session_123",
            "messages": [
                {"role": "user", "text": "Hello"},
                {"role": "agent", "text": "Hi, how can I help?"}
            ],
            "metadata": {
                "created_at": "2025-10-01T10:00:00Z",
                "total_turns": 2
            }
        }
        
        mock_services.session_service.export_conversation = AsyncMock(return_value=export_data)
        
        response = client.get("/sessions/session_123/export?include_metadata=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session_123"
        assert len(data["messages"]) == 2
    
    @patch('src.api.session_router.get_services')
    def test_cleanup_sessions(self, mock_get_services, client, mock_services):
        """Test manual session cleanup"""
        mock_get_services.return_value = mock_services
        mock_services.session_service.cleanup_expired_sessions = AsyncMock(return_value=5)
        
        response = client.post("/sessions/cleanup")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["sessions_cleaned"] == 5


# ============ Feedback Router Tests ============

class TestFeedbackRouter:
    """Tests for feedback collection router"""
    
    @patch('src.api.feedback_router.get_services')
    def test_submit_feedback_thumbs_up(self, mock_get_services, client, mock_services):
        """Test submitting positive feedback"""
        mock_get_services.return_value = mock_services
        
        mock_feedback = Mock()
        mock_feedback.feedback_id = "fb_123"
        
        mock_services.feedback_service.collect_feedback = AsyncMock(return_value=mock_feedback)
        
        response = client.post("/feedback", json={
            "session_id": "session_123",
            "feedback_type": "thumbs_up",
            "agent_name": "receptionist_l1",
            "rating": 5,
            "intent": "scheduling"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["feedback_id"] == "fb_123"
        assert "thank you" in data["message"].lower()
    
    @patch('src.api.feedback_router.get_services')
    def test_submit_feedback_with_text(self, mock_get_services, client, mock_services):
        """Test submitting feedback with text comment"""
        mock_get_services.return_value = mock_services
        
        mock_feedback = Mock()
        mock_feedback.feedback_id = "fb_456"
        
        mock_services.feedback_service.collect_feedback = AsyncMock(return_value=mock_feedback)
        
        response = client.post("/feedback", json={
            "session_id": "session_123",
            "feedback_type": "thumbs_down",
            "agent_name": "billing_agent_l3",
            "rating": 2,
            "feedback_text": "Did not resolve my issue",
            "category": "resolution",
            "intent": "billing"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @patch('src.api.feedback_router.get_services')
    def test_submit_escalation_feedback(self, mock_get_services, client, mock_services):
        """Test submitting escalation feedback"""
        mock_get_services.return_value = mock_services
        
        mock_feedback = Mock()
        mock_feedback.feedback_id = "fb_esc_123"
        
        mock_services.feedback_service.collect_escalation_feedback = AsyncMock(return_value=mock_feedback)
        
        response = client.post("/feedback/escalation", json={
            "ticket_id": "ticket_001",
            "session_id": "session_123",
            "escalation_reason": "Complex technical issue",
            "was_escalation_necessary": True,
            "user_satisfaction": 4,
            "resolved": True,
            "resolution_time_minutes": 30
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "escalation" in data["message"].lower()
    
    @patch('src.api.feedback_router.get_services')
    def test_get_feedback_summary(self, mock_get_services, client, mock_services):
        """Test retrieving feedback summary"""
        mock_get_services.return_value = mock_services
        
        summary = {
            "period_days": 7,
            "total_feedback": 100,
            "positive_feedback": 80,
            "negative_feedback": 15,
            "neutral_feedback": 5,
            "positive_rate": 0.8,
            "avg_rating": 4.2
        }
        
        mock_services.feedback_service.get_feedback_summary = AsyncMock(return_value=summary)
        
        response = client.get("/feedback/summary?days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_feedback"] == 100
        assert data["positive_rate"] == 0.8
    
    @patch('src.api.feedback_router.get_services')
    def test_get_feedback_analytics(self, mock_get_services, client, mock_services):
        """Test generating comprehensive analytics"""
        mock_get_services.return_value = mock_services
        
        mock_analytics = Mock()
        mock_analytics.model_dump = Mock(return_value={
            "total_feedback_count": 500,
            "positive_feedback_count": 400,
            "negative_feedback_count": 80,
            "avg_rating": 4.3,
            "feedback_by_agent": {
                "receptionist_l1": {"total": 200, "positive": 180}
            },
            "top_issues": [
                {"category": "understanding", "count": 25}
            ]
        })
        
        mock_services.feedback_service.generate_analytics = AsyncMock(return_value=mock_analytics)
        
        response = client.get("/feedback/analytics?period_days=30")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_feedback_count"] == 500
        assert data["avg_rating"] == 4.3


# ============ Improvement Router Tests ============

class TestImprovementRouter:
    """Tests for improvement opportunities router"""
    
    @patch('src.api.improvement_router.get_services')
    def test_get_improvement_opportunities(self, mock_get_services, client, mock_services):
        """Test listing improvement opportunities"""
        mock_get_services.return_value = mock_services
        
        opportunities = [
            {
                "opportunity_id": "opp_1",
                "agent_name": "billing_agent",
                "issue_description": "High negative feedback rate",
                "priority": "high",
                "status": "open"
            },
            {
                "opportunity_id": "opp_2",
                "agent_name": "receptionist_l1",
                "issue_description": "Misclassification pattern",
                "priority": "medium",
                "status": "open"
            }
        ]
        
        mock_services.feedback_service.get_improvement_opportunities = AsyncMock(return_value=opportunities)
        
        response = client.get("/improvements?status=open&priority=high")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["opportunities"]) == 2
    
    @patch('src.api.improvement_router.get_services')
    def test_update_improvement_opportunity(self, mock_get_services, client, mock_services):
        """Test updating an improvement opportunity"""
        mock_get_services.return_value = mock_services
        mock_services.feedback_service.update_improvement_opportunity = AsyncMock()
        
        response = client.put("/improvements/opp_1", params={
            "status": "in_progress",
            "assigned_to": "developer@example.com",
            "resolution_notes": "Working on prompt improvements"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "updated" in data["message"].lower()


# ============ Auth Router Tests ============

class TestAuthRouter:
    """Tests for authentication router"""
    
    @patch('src.api.auth_router.get_services')
    def test_register_user(self, mock_get_services, client, mock_services):
        """Test user registration"""
        mock_get_services.return_value = mock_services
        
        # Mock database operations
        mock_services.db_service.db.users.find_one = AsyncMock(return_value=None)
        mock_services.db_service.db.users.insert_one = AsyncMock()
        
        response = client.post("/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User",
            "role": "user"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["is_active"] is True
        assert "user_id" in data
    
    @patch('src.api.auth_router.get_services')
    def test_register_duplicate_email(self, mock_get_services, client, mock_services):
        """Test registration with existing email"""
        mock_get_services.return_value = mock_services
        
        # Mock existing user
        mock_services.db_service.db.users.find_one = AsyncMock(return_value={"email": "existing@example.com"})
        
        response = client.post("/auth/register", json={
            "email": "existing@example.com",
            "password": "password123",
            "full_name": "Duplicate User",
            "role": "user"
        })
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    @patch('src.api.auth_router.get_services')
    def test_login_success(self, mock_get_services, client, mock_services):
        """Test successful login"""
        mock_get_services.return_value = mock_services
        
        from src.api.auth_router import hash_password
        
        # Mock user with hashed password
        mock_user = {
            "user_id": "user_123",
            "email": "user@example.com",
            "password_hash": hash_password("correctpassword"),
            "role": "user",
            "is_active": True
        }
        
        mock_services.db_service.db.users.find_one = AsyncMock(return_value=mock_user)
        
        response = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "correctpassword"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
    
    @patch('src.api.auth_router.get_services')
    def test_login_wrong_password(self, mock_get_services, client, mock_services):
        """Test login with wrong password"""
        mock_get_services.return_value = mock_services
        
        from src.api.auth_router import hash_password
        
        mock_user = {
            "user_id": "user_123",
            "email": "user@example.com",
            "password_hash": hash_password("correctpassword"),
            "is_active": True
        }
        
        mock_services.db_service.db.users.find_one = AsyncMock(return_value=mock_user)
        
        response = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_get_current_user_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/auth/me")
        
        assert response.status_code == 403  # No credentials


# ============ Admin Router Tests ============

class TestAdminRouter:
    """Tests for admin router"""
    
    @patch('src.api.admin_router.get_services')
    @patch('src.api.admin_router.get_current_admin_user')
    def test_list_users(self, mock_get_admin, mock_get_services, client, mock_services):
        """Test listing users (admin only)"""
        mock_get_services.return_value = mock_services
        mock_get_admin.return_value = {"user_id": "admin_123", "role": "admin"}
        
        mock_users = [
            {"user_id": "user_1", "email": "user1@example.com", "role": "user", "_id": "123"},
            {"user_id": "user_2", "email": "user2@example.com", "role": "user", "_id": "456"}
        ]
        
        mock_services.db_service.db.users.count_documents = AsyncMock(return_value=2)
        mock_cursor = Mock()
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=mock_users)
        mock_services.db_service.db.users.find = Mock(return_value=mock_cursor)
        
        response = client.get("/admin/users?page=1&page_size=20")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["users"]) == 2
    
    @patch('src.api.admin_router.get_services')
    @patch('src.api.admin_router.get_current_admin_user')
    def test_get_system_stats(self, mock_get_admin, mock_get_services, client, mock_services):
        """Test getting system statistics"""
        mock_get_services.return_value = mock_services
        mock_get_admin.return_value = {"user_id": "admin_123", "role": "admin"}
        
        mock_services.db_service.db.users.count_documents = AsyncMock(side_effect=[100, 95])
        mock_services.db_service.db.sessions.count_documents = AsyncMock(return_value=50)
        mock_services.db_service.db.conversation_logs.count_documents = AsyncMock(return_value=25)
        mock_services.db_service.db.user_feedback.count_documents = AsyncMock(return_value=200)
        mock_services.db_service.db.escalation_tickets.count_documents = AsyncMock(return_value=5)
        
        response = client.get("/admin/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 100
        assert data["active_users"] == 95
        assert data["total_sessions"] == 50


# ============ Webhook Router Tests ============

class TestWebhookRouter:
    """Tests for webhook router"""
    
    @patch('src.api.webhook_router.get_services')
    def test_twilio_voice_webhook_ringing(self, mock_get_services, client, mock_services):
        """Test Twilio voice webhook with ringing status"""
        mock_get_services.return_value = mock_services
        
        response = client.post("/webhooks/twilio/voice", data={
            "CallSid": "call_123",
            "From": "+15551234567",
            "CallStatus": "ringing"
        })
        
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "<Gather" in response.text
        assert "Welcome" in response.text
    
    @patch('src.api.webhook_router.get_services')
    def test_twilio_sms_webhook(self, mock_get_services, client, mock_services):
        """Test Twilio SMS webhook"""
        mock_get_services.return_value = mock_services
        
        mock_result = Mock()
        mock_result.response_text = "Thank you for your message. I can help with that."
        mock_services.workflow_runner.process_call = AsyncMock(return_value=mock_result)
        
        response = client.post("/webhooks/twilio/sms", data={
            "MessageSid": "msg_123",
            "From": "+15551234567",
            "Body": "I need help with my appointment"
        })
        
        assert response.status_code == 200
        assert "<Message>" in response.text
        assert "Thank you" in response.text
    
    @patch('src.api.webhook_router.get_services')
    def test_slack_url_verification(self, mock_get_services, client, mock_services):
        """Test Slack URL verification challenge"""
        mock_get_services.return_value = mock_services
        
        response = client.post("/webhooks/slack/events", json={
            "type": "url_verification",
            "challenge": "test_challenge_string"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == "test_challenge_string"
    
    @patch('src.api.webhook_router.get_services')
    def test_generic_webhook(self, mock_get_services, client, mock_services):
        """Test generic webhook handler"""
        mock_get_services.return_value = mock_services
        
        response = client.post("/webhooks/generic", json={
            "event_type": "call.incoming",
            "data": {
                "caller_phone": "555-1234",
                "call_id": "call_123"
            },
            "timestamp": "2025-10-01T10:00:00Z"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event_type"] == "call.incoming"
    
    def test_webhook_test_endpoint(self, client):
        """Test webhook test endpoint"""
        response = client.get("/webhooks/test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "available_webhooks" in data


# ============ Integration Tests ============

class TestIntegration:
    """Integration tests across multiple routers"""
    
    @patch('src.api.call_router.get_services')
    @patch('src.api.feedback_router.get_services')
    def test_call_and_feedback_flow(self, mock_feedback_services, mock_call_services, client, mock_services):
        """Test complete flow: call processing -> feedback submission"""
        # Setup mocks
        mock_call_services.return_value = mock_services
        mock_feedback_services.return_value = mock_services
        
        # Process call
        mock_result = Mock()
        mock_result.session_id = "session_integration_123"
        mock_result.caller_type = Mock(value="client")
        mock_result.intent_name = "scheduling"
        mock_result.response_text = "I can help you schedule"
        mock_result.current_tier = Mock(value="L1")
        mock_result.conversation_history = []
        mock_result.requires_human_escalation = False
        mock_result.ticket_id = None
        mock_result.next_action = None
        
        mock_services.workflow_runner.process_call = AsyncMock(return_value=mock_result)
        mock_services.session_service.load_session = AsyncMock(return_value=None)
        mock_services.session_service.save_session = AsyncMock()
        mock_services.session_service.cleanup_expired_sessions = AsyncMock()
        
        call_response = client.post("/process-call", json={
            "caller_phone": "555-1234",
            "speech_text": "I need to schedule",
            "call_sid": "call_integration_123"
        })
        
        assert call_response.status_code == 200
        session_id = call_response.json()["session_id"]
        
        # Submit feedback
        mock_feedback = Mock()
        mock_feedback.feedback_id = "fb_integration_123"
        mock_services.feedback_service.collect_feedback = AsyncMock(return_value=mock_feedback)
        
        feedback_response = client.post("/feedback", json={
            "session_id": session_id,
            "feedback_type": "thumbs_up",
            "agent_name": "receptionist_l1",
            "rating": 5,
            "intent": "scheduling"
        })
        
        assert feedback_response.status_code == 200
        assert feedback_response.json()["success"] is True


# ============ Run Tests ============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])