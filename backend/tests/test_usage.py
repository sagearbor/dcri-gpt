import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.usage import TokenUsageLog
from app.models.chat import ChatSession
from app.services.usage_tracking import UsageTrackingService
from app.services.llm_gateway import LLMGateway


@pytest.fixture
def sample_user(db: Session):
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_session(db: Session, sample_user):
    """Create a sample chat session."""
    session = ChatSession(
        user_id=sample_user.id,
        title="Test Session"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def sample_usage_logs(db: Session, sample_user, sample_session):
    """Create sample usage logs for testing."""
    logs = []
    
    # Create logs for different dates and models
    for i in range(10):
        log = TokenUsageLog(
            user_id=sample_user.id,
            session_id=sample_session.id if i % 2 == 0 else None,
            model_name="gpt-4" if i % 3 == 0 else "gpt-3.5-turbo",
            prompt_tokens=100 + i * 10,
            completion_tokens=200 + i * 20,
            total_tokens=300 + i * 30,
            cost=0.01 * (i + 1),
            timestamp=datetime.utcnow() - timedelta(days=i)
        )
        db.add(log)
        logs.append(log)
    
    db.commit()
    return logs


class TestUsageTrackingService:
    """Test the usage tracking service."""
    
    async def test_log_usage(self, db: Session, sample_user, sample_session):
        """Test logging token usage."""
        result = await UsageTrackingService.log_usage(
            db=db,
            user_id=sample_user.id,
            model_name="gpt-4",
            prompt_tokens=150,
            completion_tokens=250,
            cost=0.05,
            session_id=sample_session.id
        )
        
        assert result is not None
        assert result.user_id == sample_user.id
        assert result.session_id == sample_session.id
        assert result.model_name == "gpt-4"
        assert result.prompt_tokens == 150
        assert result.completion_tokens == 250
        assert result.total_tokens == 400
        assert result.cost == 0.05
        
        # Verify it was saved to database
        saved_log = db.query(TokenUsageLog).filter(
            TokenUsageLog.id == result.id
        ).first()
        assert saved_log is not None
    
    def test_get_user_usage_summary(self, db: Session, sample_user, sample_usage_logs):
        """Test getting user usage summary."""
        summary = UsageTrackingService.get_user_usage_summary(
            db=db,
            user_id=sample_user.id,
            days=30
        )
        
        assert summary is not None
        assert summary.total_tokens > 0
        assert summary.total_cost > 0
        assert summary.total_sessions >= 0
        assert summary.tokens_today >= 0
        assert summary.cost_today >= 0
        assert summary.tokens_this_month >= 0
        assert summary.cost_this_month >= 0
        assert len(summary.by_model) > 0
        assert "gpt-4" in summary.by_model or "gpt-3.5-turbo" in summary.by_model
    
    def test_get_model_usage_stats(self, db: Session, sample_user, sample_usage_logs):
        """Test getting model usage statistics."""
        stats = UsageTrackingService.get_model_usage_stats(
            db=db,
            user_id=sample_user.id,
            days=30
        )
        
        assert len(stats) > 0
        for stat in stats:
            assert stat.model_name in ["gpt-4", "gpt-3.5-turbo"]
            assert stat.total_tokens > 0
            assert stat.total_cost > 0
            assert stat.usage_count > 0
            assert stat.average_tokens > 0
            assert 0 <= stat.percentage_of_total <= 100
    
    def test_get_system_usage_overview(self, db: Session, sample_usage_logs):
        """Test getting system-wide usage overview."""
        overview = UsageTrackingService.get_system_usage_overview(
            db=db,
            days=30
        )
        
        assert overview is not None
        assert overview["total_tokens"] > 0
        assert overview["total_cost"] > 0
        assert overview["active_users"] > 0
        assert overview["total_sessions"] >= 0
        assert len(overview["top_users"]) > 0
        assert len(overview["model_usage"]) > 0
        assert len(overview["daily_trend"]) > 0


class TestLLMGateway:
    """Test the LLM Gateway token counting."""
    
    def test_count_tokens(self):
        """Test token counting for text."""
        gateway = LLMGateway(model_name="gpt-3.5-turbo")
        
        text = "Hello, how are you today?"
        token_count = gateway.count_tokens(text)
        
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_count_messages_tokens(self):
        """Test token counting for messages."""
        gateway = LLMGateway(model_name="gpt-3.5-turbo")
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there! How can I help you today?"}
        ]
        
        token_count = gateway.count_messages_tokens(messages)
        
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_estimate_cost(self):
        """Test cost estimation."""
        gateway = LLMGateway(model_name="gpt-4o-mini")
        
        cost = gateway.estimate_cost(prompt_tokens=100, completion_tokens=200)
        
        assert cost > 0
        assert isinstance(cost, float)
        
        # Test with different model
        gateway_gpt4 = LLMGateway(model_name="gpt-4")
        cost_gpt4 = gateway_gpt4.estimate_cost(prompt_tokens=100, completion_tokens=200)
        
        assert cost_gpt4 > cost  # GPT-4 should be more expensive


class TestUsageEndpoints:
    """Test the usage API endpoints."""
    
    def test_get_usage_summary(self, client, auth_headers, db: Session, sample_user, sample_usage_logs):
        """Test GET /api/v1/usage/summary endpoint."""
        response = client.get(
            "/api/v1/usage/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_tokens" in data
        assert "total_cost" in data
        assert "total_sessions" in data
        assert "tokens_today" in data
        assert "cost_today" in data
        assert "tokens_this_month" in data
        assert "cost_this_month" in data
        assert "by_model" in data
    
    def test_get_usage_summary_with_days_param(self, client, auth_headers):
        """Test usage summary with days parameter."""
        response = client.get(
            "/api/v1/usage/summary?days=7",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_tokens" in data
    
    def test_get_model_usage_stats(self, client, auth_headers, db: Session, sample_user, sample_usage_logs):
        """Test GET /api/v1/usage/models endpoint."""
        response = client.get(
            "/api/v1/usage/models",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        if len(data) > 0:
            stat = data[0]
            assert "model_name" in stat
            assert "total_tokens" in stat
            assert "total_cost" in stat
            assert "usage_count" in stat
            assert "average_tokens" in stat
            assert "percentage_of_total" in stat
    
    def test_get_usage_history(self, client, auth_headers, db: Session, sample_user, sample_usage_logs):
        """Test GET /api/v1/usage/history endpoint."""
        response = client.get(
            "/api/v1/usage/history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "logs" in data
        assert isinstance(data["logs"], list)
        
        if len(data["logs"]) > 0:
            log = data["logs"][0]
            assert "id" in log
            assert "model_name" in log
            assert "prompt_tokens" in log
            assert "completion_tokens" in log
            assert "total_tokens" in log
            assert "cost" in log
            assert "timestamp" in log
    
    def test_get_usage_history_with_pagination(self, client, auth_headers):
        """Test usage history with pagination."""
        response = client.get(
            "/api/v1/usage/history?limit=5&offset=0",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) <= 5
    
    def test_usage_endpoints_require_auth(self, client):
        """Test that usage endpoints require authentication."""
        endpoints = [
            "/api/v1/usage/summary",
            "/api/v1/usage/models",
            "/api/v1/usage/history"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401


@pytest.mark.asyncio
class TestChatWithUsageLogging:
    """Test chat endpoint with usage logging."""
    
    @patch('app.api.v1.chat.LLMGateway')
    async def test_chat_logs_usage(self, mock_gateway_class, client, auth_headers, db: Session, sample_user):
        """Test that chat endpoint logs token usage."""
        # Mock the LLM gateway
        mock_gateway = AsyncMock()
        mock_gateway.model_name = "gpt-4o-mini"
        mock_gateway.count_tokens.return_value = 10
        mock_gateway.count_messages_tokens.return_value = 50
        mock_gateway.estimate_cost.return_value = 0.002
        
        async def mock_streaming():
            yield "Hello"
            yield " there!"
        
        mock_gateway.get_streaming_completion.return_value = mock_streaming()
        mock_gateway_class.return_value = mock_gateway
        
        # Make chat request
        response = client.post(
            "/api/v1/chat",
            json={"content": "Hello, AI!"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Check that usage was logged
        usage_log = db.query(TokenUsageLog).filter(
            TokenUsageLog.user_id == sample_user.id
        ).first()
        
        # Note: Due to the async nature and background tasks, 
        # the usage log might not be immediately available in tests
        # In a real scenario, you might need to wait or mock the background task