import pytest
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.models.bot import CustomBot


def create_test_session_with_messages(
    db: Session,
    user: User,
    title: str = "Test Session",
    message_contents: List[str] = None
) -> ChatSession:
    """Helper to create a session with messages"""
    session = ChatSession(
        user_id=user.id,
        title=title,
        created_at=datetime.utcnow()
    )
    db.add(session)
    db.flush()
    
    if message_contents:
        for i, content in enumerate(message_contents):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            message = ChatMessage(
                session_id=session.id,
                role=role,
                content=content,
                timestamp=datetime.utcnow() + timedelta(minutes=i)
            )
            db.add(message)
    
    db.commit()
    db.refresh(session)
    return session


class TestSessionEndpoints:
    """Test session listing and retrieval endpoints"""
    
    def test_list_user_sessions(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test listing sessions for authenticated user"""
        # Create test sessions
        session1 = create_test_session_with_messages(
            db_session, test_user, "First Session", ["Hello", "Hi there"]
        )
        session2 = create_test_session_with_messages(
            db_session, test_user, "Second Session", ["Question", "Answer"]
        )
        
        # Get sessions
        response = client.get("/api/v1/sessions", headers=normal_user_token_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
        assert any(s["title"] == "First Session" for s in data)
        assert any(s["title"] == "Second Session" for s in data)
        assert all(s["message_count"] == 2 for s in data)
    
    def test_list_sessions_pagination(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test session listing with pagination"""
        # Create multiple sessions
        for i in range(25):
            create_test_session_with_messages(
                db_session, test_user, f"Session {i}", [f"Message {i}"]
            )
        
        # Get first page
        response = client.get(
            "/api/v1/sessions?skip=0&limit=10",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        # Get second page
        response = client.get(
            "/api/v1/sessions?skip=10&limit=10",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        # Get third page
        response = client.get(
            "/api/v1/sessions?skip=20&limit=10",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
    
    def test_user_session_isolation(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        test_user2: User,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str]
    ):
        """Test that users can only see their own sessions"""
        # Create sessions for both users
        session1 = create_test_session_with_messages(
            db_session, test_user, "User 1 Session", ["User 1 message"]
        )
        session2 = create_test_session_with_messages(
            db_session, test_user2, "User 2 Session", ["User 2 message"]
        )
        
        # User 1 should only see their session
        response = client.get("/api/v1/sessions", headers=normal_user_token_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "User 1 Session"
        
        # User 2 should only see their session
        response = client.get("/api/v1/sessions", headers=second_user_token_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "User 2 Session"
    
    def test_get_session_messages(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test retrieving messages for a specific session"""
        session = create_test_session_with_messages(
            db_session,
            test_user,
            "Test Session",
            ["Hello AI", "Hello human", "How are you?", "I'm doing well"]
        )
        
        response = client.get(
            f"/api/v1/sessions/{session.id}/messages",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        
        messages = response.json()
        assert len(messages) == 4
        assert messages[0]["content"] == "Hello AI"
        assert messages[0]["role"] == "user"
        assert messages[1]["content"] == "Hello human"
        assert messages[1]["role"] == "assistant"
    
    def test_get_session_messages_with_role_filter(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test filtering messages by role"""
        session = create_test_session_with_messages(
            db_session,
            test_user,
            "Test Session",
            ["User msg 1", "AI msg 1", "User msg 2", "AI msg 2"]
        )
        
        # Get only user messages
        response = client.get(
            f"/api/v1/sessions/{session.id}/messages?role_filter=user",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 2
        assert all(m["role"] == "user" for m in messages)
        
        # Get only assistant messages
        response = client.get(
            f"/api/v1/sessions/{session.id}/messages?role_filter=assistant",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 2
        assert all(m["role"] == "assistant" for m in messages)
    
    def test_cannot_access_other_users_session_messages(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        test_user2: User,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str]
    ):
        """Test that users cannot access other users' session messages"""
        session = create_test_session_with_messages(
            db_session, test_user, "Private Session", ["Private message"]
        )
        
        # User 2 tries to access User 1's session messages
        response = client.get(
            f"/api/v1/sessions/{session.id}/messages",
            headers=second_user_token_headers
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestSearchEndpoints:
    """Test search functionality"""
    
    def test_search_messages(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test searching through message content"""
        # Create sessions with specific content
        session1 = create_test_session_with_messages(
            db_session,
            test_user,
            "Python Discussion",
            ["How do I use Python decorators?", "Decorators are functions that modify other functions"]
        )
        session2 = create_test_session_with_messages(
            db_session,
            test_user,
            "JavaScript Talk",
            ["What is JavaScript closure?", "A closure is a function that has access to outer scope"]
        )
        
        # Search for "Python"
        response = client.get(
            "/api/v1/search?q=Python",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"] == "Python"
        assert len(data["messages"]) > 0
        assert any("Python" in msg["content"] for msg in data["messages"])
        assert len(data["sessions"]) == 1  # Session title matches
    
    def test_search_sessions(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test searching through session titles"""
        session1 = create_test_session_with_messages(
            db_session, test_user, "Machine Learning Basics", ["ML content"]
        )
        session2 = create_test_session_with_messages(
            db_session, test_user, "Deep Learning Advanced", ["DL content"]
        )
        session3 = create_test_session_with_messages(
            db_session, test_user, "Web Development", ["Web content"]
        )
        
        # Search for "Learning"
        response = client.get(
            "/api/v1/search?q=Learning&search_type=sessions",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["sessions"]) == 2
        assert all("Learning" in s["title"] for s in data["sessions"])
        assert len(data["messages"]) == 0  # Only searching sessions
    
    def test_search_with_filters(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test search with date and bot filters"""
        # Create bot
        bot = CustomBot(
            name="Test Bot",
            system_prompt="Test",
            model_name="gpt-4",
            user_id=test_user.id
        )
        db_session.add(bot)
        db_session.flush()
        
        # Create sessions with different dates and bots
        old_date = datetime.utcnow() - timedelta(days=30)
        recent_date = datetime.utcnow() - timedelta(days=1)
        
        old_session = ChatSession(
            user_id=test_user.id,
            title="Old Session",
            created_at=old_date
        )
        db_session.add(old_session)
        db_session.flush()
        
        old_message = ChatMessage(
            session_id=old_session.id,
            role=MessageRole.USER,
            content="Old search term",
            timestamp=old_date
        )
        db_session.add(old_message)
        
        recent_session = ChatSession(
            user_id=test_user.id,
            title="Recent Session",
            bot_id=bot.id,
            created_at=recent_date
        )
        db_session.add(recent_session)
        db_session.flush()
        
        recent_message = ChatMessage(
            session_id=recent_session.id,
            role=MessageRole.USER,
            content="Recent search term",
            timestamp=recent_date
        )
        db_session.add(recent_message)
        
        db_session.commit()
        
        # Search with date filter
        date_from = (datetime.utcnow() - timedelta(days=7)).isoformat()
        response = client.get(
            f"/api/v1/search?q=search&date_from={date_from}",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 1
        assert "Recent" in data["messages"][0]["content"]
        
        # Search with bot filter
        response = client.get(
            f"/api/v1/search?q=search&bot_id={bot.id}",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 1
        assert "Recent" in data["messages"][0]["content"]
    
    def test_search_user_isolation(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        test_user2: User,
        normal_user_token_headers: Dict[str, str],
        second_user_token_headers: Dict[str, str]
    ):
        """Test that search results are isolated per user"""
        # Create content for both users
        session1 = create_test_session_with_messages(
            db_session,
            test_user,
            "User 1 Secret",
            ["User 1 confidential information"]
        )
        session2 = create_test_session_with_messages(
            db_session,
            test_user2,
            "User 2 Secret",
            ["User 2 confidential information"]
        )
        
        # User 1 searches for "confidential"
        response = client.get(
            "/api/v1/search?q=confidential",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 1
        assert "User 1" in data["messages"][0]["content"]
        assert "User 2" not in str(data)
        
        # User 2 searches for "confidential"
        response = client.get(
            "/api/v1/search?q=confidential",
            headers=second_user_token_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 1
        assert "User 2" in data["messages"][0]["content"]
        assert "User 1" not in str(data)
    
    def test_search_pagination(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test search results pagination"""
        # Create many messages with search term
        session = create_test_session_with_messages(
            db_session,
            test_user,
            "Big Session",
            [f"Message {i} with search term" for i in range(30)]
        )
        
        # Get first page
        response = client.get(
            "/api/v1/search?q=search&skip=0&limit=10",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 10
        
        # Get second page
        response = client.get(
            "/api/v1/search?q=search&skip=10&limit=10",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 10
    
    def test_advanced_search_options(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test advanced search with case sensitivity and whole word matching"""
        session = create_test_session_with_messages(
            db_session,
            test_user,
            "Test Session",
            ["The PYTHON programming language", "pythonic code style", "I love Python!"]
        )
        
        # Case-sensitive search
        response = client.get(
            "/api/v1/advanced-search?q=PYTHON&case_sensitive=true",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 1
        assert "PYTHON" in data["messages"][0]["content"]
        
        # Case-insensitive search
        response = client.get(
            "/api/v1/advanced-search?q=python&case_sensitive=false",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 3
    
    def test_search_match_snippets(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        normal_user_token_headers: Dict[str, str]
    ):
        """Test that search returns match snippets with context"""
        long_content = "This is a very long message " * 10 + "with SEARCHTERM in the middle " + "and more content after " * 10
        
        session = create_test_session_with_messages(
            db_session,
            test_user,
            "Test Session",
            [long_content]
        )
        
        response = client.get(
            "/api/v1/search?q=SEARCHTERM",
            headers=normal_user_token_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 1
        
        snippet = data["messages"][0]["match_snippet"]
        assert "SEARCHTERM" in snippet
        assert "..." in snippet  # Should have ellipsis for truncated content
        assert len(snippet) < len(long_content)  # Snippet should be shorter than full content