import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.models.feedback import MessageFeedback
from app.models.usage import TokenUsageLog


@pytest.fixture
def admin_user(db: Session):
    """Create an admin user for testing."""
    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def regular_user(db: Session):
    """Create a regular user for testing."""
    user = User(
        email="user@example.com",
        username="regularuser",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_auth_headers(client: TestClient, admin_user):
    """Get auth headers for admin user."""
    from app.core.auth import create_access_token
    token = create_access_token(data={"sub": admin_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def regular_auth_headers(client: TestClient, regular_user):
    """Get auth headers for regular user."""
    from app.core.auth import create_access_token
    token = create_access_token(data={"sub": regular_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_data(db: Session, regular_user):
    """Create sample data for testing."""
    # Create sessions and messages
    session = ChatSession(
        user_id=regular_user.id,
        title="Test Session"
    )
    db.add(session)
    db.commit()
    
    message = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="Test response",
        token_count=10
    )
    db.add(message)
    db.commit()
    
    # Create feedback
    feedback = MessageFeedback(
        message_id=message.id,
        user_id=regular_user.id,
        rating=1,
        comment="Good response"
    )
    db.add(feedback)
    
    # Create usage log
    usage_log = TokenUsageLog(
        user_id=regular_user.id,
        session_id=session.id,
        model_name="gpt-4",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
        cost=0.05
    )
    db.add(usage_log)
    
    db.commit()
    
    return {
        "session": session,
        "message": message,
        "feedback": feedback,
        "usage_log": usage_log
    }


class TestAdminEndpoints:
    """Test admin API endpoints."""
    
    def test_admin_usage_overview(self, client, admin_auth_headers, sample_data):
        """Test GET /api/v1/admin/usage/overview endpoint."""
        response = client.get(
            "/api/v1/admin/usage/overview",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_tokens" in data
        assert "total_cost" in data
        assert "active_users" in data
        assert "total_sessions" in data
        assert "top_users" in data
        assert "model_usage" in data
        assert "daily_trend" in data
        
        assert data["total_tokens"] >= 300
        assert data["total_cost"] >= 0.05
        assert data["active_users"] >= 1
    
    def test_admin_usage_overview_requires_admin(self, client, regular_auth_headers):
        """Test that usage overview requires admin privileges."""
        response = client.get(
            "/api/v1/admin/usage/overview",
            headers=regular_auth_headers
        )
        
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]
    
    def test_admin_list_users(self, client, admin_auth_headers, regular_user):
        """Test GET /api/v1/admin/users endpoint."""
        response = client.get(
            "/api/v1/admin/users",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check user structure
        user_data = next((u for u in data if u["id"] == regular_user.id), None)
        assert user_data is not None
        assert user_data["email"] == regular_user.email
        assert "session_count" in user_data
        assert "total_tokens" in user_data
        assert "total_cost" in user_data
    
    def test_admin_list_users_pagination(self, client, admin_auth_headers):
        """Test user list pagination."""
        response = client.get(
            "/api/v1/admin/users?skip=0&limit=5",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5
    
    def test_admin_list_users_requires_admin(self, client, regular_auth_headers):
        """Test that listing users requires admin privileges."""
        response = client.get(
            "/api/v1/admin/users",
            headers=regular_auth_headers
        )
        
        assert response.status_code == 403
    
    def test_admin_get_feedback(self, client, admin_auth_headers, sample_data):
        """Test GET /api/v1/admin/feedback endpoint."""
        response = client.get(
            "/api/v1/admin/feedback",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "items" in data
        assert "statistics" in data
        
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        
        # Check feedback structure
        feedback_item = data["items"][0]
        assert "id" in feedback_item
        assert "rating" in feedback_item
        assert "comment" in feedback_item
        assert "user" in feedback_item
        assert "message" in feedback_item
        assert "session" in feedback_item
        
        # Check statistics
        stats = data["statistics"]
        assert "total_feedback" in stats
        assert "positive_count" in stats
        assert "negative_count" in stats
        assert "positive_percentage" in stats
        assert "negative_percentage" in stats
    
    def test_admin_get_feedback_with_filter(self, client, admin_auth_headers, sample_data):
        """Test feedback filtering by rating."""
        response = client.get(
            "/api/v1/admin/feedback?rating_filter=1",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should have rating 1
        for item in data["items"]:
            assert item["rating"] == 1
    
    def test_admin_get_feedback_requires_admin(self, client, regular_auth_headers):
        """Test that viewing feedback requires admin privileges."""
        response = client.get(
            "/api/v1/admin/feedback",
            headers=regular_auth_headers
        )
        
        assert response.status_code == 403
    
    def test_admin_update_user_status(self, client, admin_auth_headers, regular_user):
        """Test PATCH /api/v1/admin/users/{user_id}/status endpoint."""
        # Deactivate user
        response = client.patch(
            f"/api/v1/admin/users/{regular_user.id}/status",
            params={"is_active": False},
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert "deactivated successfully" in data["message"]
        
        # Reactivate user
        response = client.patch(
            f"/api/v1/admin/users/{regular_user.id}/status",
            params={"is_active": True},
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        assert "activated successfully" in data["message"]
    
    def test_admin_cannot_modify_own_status(self, client, admin_auth_headers, admin_user):
        """Test that admin cannot modify their own status."""
        response = client.patch(
            f"/api/v1/admin/users/{admin_user.id}/status",
            params={"is_active": False},
            headers=admin_auth_headers
        )
        
        assert response.status_code == 400
        assert "Cannot modify your own admin status" in response.json()["detail"]
    
    def test_admin_update_nonexistent_user(self, client, admin_auth_headers):
        """Test updating status of non-existent user."""
        response = client.patch(
            "/api/v1/admin/users/99999/status",
            params={"is_active": False},
            headers=admin_auth_headers
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_admin_get_platform_statistics(self, client, admin_auth_headers, sample_data):
        """Test GET /api/v1/admin/stats/summary endpoint."""
        response = client.get(
            "/api/v1/admin/stats/summary",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
        assert "chat" in data
        assert "bots" in data
        assert "usage" in data
        
        # Check users stats
        assert "total" in data["users"]
        assert "active" in data["users"]
        assert "inactive" in data["users"]
        
        # Check chat stats
        assert "total_sessions" in data["chat"]
        assert "total_messages" in data["chat"]
        assert "avg_messages_per_session" in data["chat"]
        
        # Check usage stats
        assert "total_tokens" in data["usage"]
        assert "total_cost" in data["usage"]
        assert "models_used" in data["usage"]
    
    def test_admin_stats_requires_admin(self, client, regular_auth_headers):
        """Test that platform statistics require admin privileges."""
        response = client.get(
            "/api/v1/admin/stats/summary",
            headers=regular_auth_headers
        )
        
        assert response.status_code == 403


class TestAdminAuthentication:
    """Test admin authentication and authorization."""
    
    def test_all_admin_endpoints_require_auth(self, client):
        """Test that all admin endpoints require authentication."""
        endpoints = [
            "/api/v1/admin/usage/overview",
            "/api/v1/admin/users",
            "/api/v1/admin/feedback",
            "/api/v1/admin/stats/summary"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
    
    def test_all_admin_endpoints_require_admin_role(self, client, regular_auth_headers):
        """Test that all admin endpoints require admin role."""
        endpoints = [
            "/api/v1/admin/usage/overview",
            "/api/v1/admin/users",
            "/api/v1/admin/feedback",
            "/api/v1/admin/stats/summary"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=regular_auth_headers)
            assert response.status_code == 403
            assert "Admin privileges required" in response.json()["detail"]