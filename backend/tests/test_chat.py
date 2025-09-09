import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.models.user import User
from app.services.llm_gateway import LLMGateway


class TestLLMGateway:
    def test_llm_gateway_initialization(self):
        gateway = LLMGateway(model_name="gpt-4o-mini")
        assert gateway.model_name == "gpt-4o-mini"
        assert gateway.deployment_name is not None
    
    def test_token_counting(self):
        gateway = LLMGateway()
        text = "Hello, this is a test message."
        token_count = gateway.count_tokens(text)
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_messages_token_counting(self):
        gateway = LLMGateway()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        token_count = gateway.count_messages_tokens(messages)
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_cost_estimation(self):
        gateway = LLMGateway(model_name="gpt-4o-mini")
        cost = gateway.estimate_cost(prompt_tokens=100, completion_tokens=50)
        assert cost > 0
        assert isinstance(cost, float)


class TestChatEndpoints:
    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.is_active = True
        return user
    
    @pytest.fixture
    def mock_session(self):
        session = MagicMock(spec=ChatSession)
        session.id = 1
        session.user_id = 1
        session.bot_id = None
        session.title = "Test Session"
        session.created_at = "2024-01-01T00:00:00"
        session.updated_at = None
        return session
    
    def test_chat_new_session(self, client, db_session, mock_user):
        with patch('app.api.v1.chat.get_current_active_user', return_value=mock_user), \
             patch.object(db_session, 'query') as mock_query, \
             patch.object(db_session, 'add') as mock_add, \
             patch.object(db_session, 'commit') as mock_commit, \
             patch.object(db_session, 'refresh') as mock_refresh, \
             patch('app.api.v1.chat.LLMGateway') as MockLLMGateway:
            
            mock_gateway = MockLLMGateway.return_value
            
            async def mock_stream():
                yield "Hello"
                yield " there!"
            
            mock_gateway.get_streaming_completion = AsyncMock(return_value=mock_stream())
            mock_gateway.count_tokens.return_value = 10
            mock_gateway.count_messages_tokens.return_value = 20
            mock_gateway.estimate_cost.return_value = 0.001
            mock_gateway.model_name = "gpt-4o-mini"
            
            response = client.post(
                "/api/v1/chat",
                json={"content": "Hello, AI!", "session_id": None},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            mock_add.assert_called()
            mock_commit.assert_called()
    
    def test_chat_existing_session(self, client, db_session, mock_user, mock_session):
        with patch('app.api.v1.chat.get_current_active_user', return_value=mock_user), \
             patch.object(db_session, 'query') as mock_query, \
             patch('app.api.v1.chat.LLMGateway') as MockLLMGateway:
            
            mock_query.return_value.filter.return_value.first.return_value = mock_session
            mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = []
            
            mock_gateway = MockLLMGateway.return_value
            
            async def mock_stream():
                yield "Response"
            
            mock_gateway.get_streaming_completion = AsyncMock(return_value=mock_stream())
            mock_gateway.count_tokens.return_value = 10
            mock_gateway.count_messages_tokens.return_value = 20
            mock_gateway.estimate_cost.return_value = 0.001
            mock_gateway.model_name = "gpt-4o-mini"
            
            response = client.post(
                "/api/v1/chat",
                json={"content": "Continue conversation", "session_id": 1},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
    
    def test_chat_session_not_found(self, client, db_session, mock_user):
        with patch('app.api.v1.chat.get_current_active_user', return_value=mock_user), \
             patch.object(db_session, 'query') as mock_query:
            
            mock_query.return_value.filter.return_value.first.return_value = None
            
            response = client.post(
                "/api/v1/chat",
                json={"content": "Hello", "session_id": 999},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Session not found" in response.json()["detail"]
    
    def test_get_sessions(self, client, db_session, mock_user):
        with patch('app.api.v1.chat.get_current_active_user', return_value=mock_user), \
             patch.object(db_session, 'query') as mock_query:
            
            mock_session1 = MagicMock()
            mock_session1.id = 1
            mock_session1.user_id = 1
            mock_session1.title = "Session 1"
            mock_session1.bot_id = None
            mock_session1.created_at = "2024-01-01T00:00:00"
            mock_session1.updated_at = None
            
            mock_query.return_value.outerjoin.return_value.filter.return_value.group_by.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
                (mock_session1, 5)
            ]
            
            response = client.get(
                "/api/v1/sessions",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == 1
            assert data[0]["message_count"] == 5
    
    def test_get_session_with_messages(self, client, db_session, mock_user, mock_session):
        with patch('app.api.v1.chat.get_current_active_user', return_value=mock_user), \
             patch.object(db_session, 'query') as mock_query:
            
            mock_message = MagicMock(spec=ChatMessage)
            mock_message.id = 1
            mock_message.session_id = 1
            mock_message.role = MessageRole.USER
            mock_message.content = "Test message"
            mock_message.token_count = 5
            mock_message.timestamp = "2024-01-01T00:00:00"
            
            mock_query.return_value.filter.return_value.first.return_value = mock_session
            mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_message]
            
            response = client.get(
                "/api/v1/sessions/1",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 1
            assert len(data["messages"]) == 1
            assert data["message_count"] == 1
    
    def test_get_session_not_found(self, client, db_session, mock_user):
        with patch('app.api.v1.chat.get_current_active_user', return_value=mock_user), \
             patch.object(db_session, 'query') as mock_query:
            
            mock_query.return_value.filter.return_value.first.return_value = None
            
            response = client.get(
                "/api/v1/sessions/999",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Session not found" in response.json()["detail"]
    
    def test_delete_session(self, client, db_session, mock_user, mock_session):
        with patch('app.api.v1.chat.get_current_active_user', return_value=mock_user), \
             patch.object(db_session, 'query') as mock_query, \
             patch.object(db_session, 'delete') as mock_delete, \
             patch.object(db_session, 'commit') as mock_commit:
            
            mock_query.return_value.filter.return_value.first.return_value = mock_session
            
            response = client.delete(
                "/api/v1/sessions/1",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_204_NO_CONTENT
            mock_delete.assert_called_once_with(mock_session)
            mock_commit.assert_called_once()
    
    def test_delete_session_not_found(self, client, db_session, mock_user):
        with patch('app.api.v1.chat.get_current_active_user', return_value=mock_user), \
             patch.object(db_session, 'query') as mock_query:
            
            mock_query.return_value.filter.return_value.first.return_value = None
            
            response = client.delete(
                "/api/v1/sessions/999",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Session not found" in response.json()["detail"]


class TestStreamingResponse:
    @pytest.mark.asyncio
    async def test_streaming_completion(self):
        with patch('app.services.llm_gateway.AsyncAzureOpenAI') as MockClient:
            mock_client = MockClient.return_value
            
            async def mock_create(**kwargs):
                class MockChunk:
                    def __init__(self, content):
                        self.choices = [MagicMock()]
                        self.choices[0].delta.content = content
                
                chunks = [MockChunk("Hello"), MockChunk(" "), MockChunk("world")]
                for chunk in chunks:
                    yield chunk
            
            mock_client.chat.completions.create = mock_create
            
            gateway = LLMGateway()
            result = []
            async for chunk in gateway.get_streaming_completion([{"role": "user", "content": "Hi"}]):
                result.append(chunk)
            
            assert "".join(result) == "Hello world"


class TestSessionTitleGeneration:
    def test_generate_title_short_message(self):
        from app.api.v1.chat import generate_session_title
        
        title = generate_session_title("Hello AI")
        assert title == "Hello AI"
    
    def test_generate_title_long_message(self):
        from app.api.v1.chat import generate_session_title
        
        long_message = "This is a very long message that should be truncated to create a session title"
        title = generate_session_title(long_message)
        assert title.endswith("...")
        assert len(title.split()) <= 9  # 8 words + "..."


class TestTokenUsageTracking:
    @pytest.mark.asyncio
    async def test_save_token_usage(self, db_session):
        from app.api.v1.chat import save_token_usage
        
        with patch.object(db_session, 'add') as mock_add, \
             patch.object(db_session, 'commit') as mock_commit:
            
            await save_token_usage(
                db_session,
                user_id=1,
                session_id=1,
                bot_id=None,
                model_name="gpt-4o-mini",
                prompt_tokens=100,
                completion_tokens=50,
                cost=0.001
            )
            
            mock_add.assert_called_once()
            mock_commit.assert_called_once()
            
            # Check that TokenUsageLog was created with correct values
            call_args = mock_add.call_args[0][0]
            assert call_args.user_id == 1
            assert call_args.session_id == 1
            assert call_args.prompt_tokens == 100
            assert call_args.completion_tokens == 50
            assert call_args.total_tokens == 150
            assert call_args.cost == 0.001