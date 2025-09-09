import pytest
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient
import os
import tempfile
from unittest.mock import patch, MagicMock

# Set test environment variables before importing app
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-32-characters-long"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "true"

from app.main import app
from app.core.config import Settings
from app.core.database import SessionLocal, Base, engine
from app.core.security import create_access_token, get_password_hash
from app.models.user import User


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_settings():
    """Override settings for testing."""
    test_settings = Settings(
        JWT_SECRET_KEY="test-secret-key-for-testing-only-32-characters-long",
        DATABASE_URL="sqlite:///:memory:",
        ENVIRONMENT="testing",
        DEBUG=True,
        REDIS_URL="redis://localhost:6379/1",
        CORS_ORIGINS=["http://testserver"],
    )
    return test_settings


@pytest.fixture(scope="function")
def client() -> Generator:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def mock_openai():
    """Mock OpenAI API calls."""
    with patch("openai.ChatCompletion.create") as mock:
        mock.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="Mocked AI response",
                        role="assistant"
                    )
                )
            ],
            usage=MagicMock(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15
            )
        )
        yield mock


@pytest.fixture(scope="function")
def mock_azure_keyvault():
    """Mock Azure Key Vault client."""
    with patch("azure.keyvault.secrets.SecretClient") as mock:
        mock_client = MagicMock()
        mock_client.get_secret.return_value = MagicMock(value="mock-secret-value")
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis client."""
    with patch("redis.Redis") as mock:
        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        mock_redis_client.delete.return_value = 1
        mock.return_value = mock_redis_client
        yield mock_redis_client


@pytest.fixture(scope="function")
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "is_active": True,
        "is_admin": False
    }


@pytest.fixture(scope="function")
def sample_bot_data():
    """Sample bot data for testing."""
    return {
        "name": "Test Bot",
        "system_prompt": "You are a helpful AI assistant for testing.",
        "model_name": "gpt-4",
        "is_public": False
    }


@pytest.fixture(scope="function")
def sample_chat_message():
    """Sample chat message for testing."""
    return {
        "role": "user",
        "content": "Hello, this is a test message",
        "session_id": None
    }


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Clean up all tables
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Clean up test database after each test."""
    yield
    # No cleanup needed for in-memory database


@pytest.fixture(scope="function")
def test_user(db_session) -> User:
    """Create a test user."""
    user = User(
        email="testuser@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user2(db_session) -> User:
    """Create a second test user."""
    user = User(
        email="testuser2@example.com",
        username="testuser2",
        hashed_password=get_password_hash("testpassword456"),
        full_name="Test User 2",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin_user(db_session) -> User:
    """Create a test admin user."""
    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def normal_user_token_headers(test_user: User) -> dict:
    """Generate authorization headers for a normal user."""
    access_token = create_access_token(data={"sub": test_user.username, "user_id": test_user.id})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def second_user_token_headers(test_user2: User) -> dict:
    """Generate authorization headers for the second user."""
    access_token = create_access_token(data={"sub": test_user2.username, "user_id": test_user2.id})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def admin_token_headers(test_admin_user: User) -> dict:
    """Generate authorization headers for an admin user."""
    access_token = create_access_token(data={"sub": test_admin_user.username, "user_id": test_admin_user.id})
    return {"Authorization": f"Bearer {access_token}"}