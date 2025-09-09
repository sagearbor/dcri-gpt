import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.unit
class TestSettings:
    """Test suite for application settings and configuration."""
    
    def test_default_settings(self, test_settings):
        """Test that default settings are properly loaded."""
        assert test_settings.APP_NAME == "DCRI GPT"
        assert test_settings.APP_VERSION == "1.0.0"
        assert test_settings.ENVIRONMENT == "testing"
        assert test_settings.DEBUG is True
        assert test_settings.JWT_ALGORITHM == "HS256"
        assert test_settings.JWT_EXPIRATION_MINUTES == 1440
    
    def test_cors_origins_parsing_list(self):
        """Test CORS origins parsing from list."""
        settings = Settings(
            JWT_SECRET_KEY="test-secret-key-for-testing-only-32-characters-long",
            CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
        )
        assert len(settings.CORS_ORIGINS) == 2
        assert "http://localhost:3000" in settings.CORS_ORIGINS
    
    def test_cors_origins_parsing_json_string(self):
        """Test CORS origins parsing from JSON string."""
        settings = Settings(
            JWT_SECRET_KEY="test-secret-key-for-testing-only-32-characters-long",
            CORS_ORIGINS='["http://localhost:3000", "http://localhost:5173"]'
        )
        assert len(settings.CORS_ORIGINS) == 2
        assert "http://localhost:3000" in settings.CORS_ORIGINS
    
    def test_cors_origins_parsing_single_string(self):
        """Test CORS origins parsing from single string."""
        settings = Settings(
            JWT_SECRET_KEY="test-secret-key-for-testing-only-32-characters-long",
            CORS_ORIGINS="http://localhost:3000"
        )
        assert len(settings.CORS_ORIGINS) == 1
        assert settings.CORS_ORIGINS[0] == "http://localhost:3000"
    
    def test_jwt_secret_key_validation_secure(self):
        """Test JWT secret key validation with secure key."""
        settings = Settings(
            JWT_SECRET_KEY="this-is-a-very-secure-secret-key-for-testing"
        )
        assert len(settings.JWT_SECRET_KEY) >= 32
    
    def test_jwt_secret_key_validation_default_raises_error(self):
        """Test JWT secret key validation rejects default value."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(JWT_SECRET_KEY="your-secret-key-change-this-in-production")
        
        assert "Please set a secure JWT_SECRET_KEY" in str(exc_info.value)
    
    def test_jwt_secret_key_validation_too_short(self):
        """Test JWT secret key validation rejects short keys."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(JWT_SECRET_KEY="short-key")
        
        assert "at least 32 characters long" in str(exc_info.value)
    
    def test_database_url_configuration(self):
        """Test database URL configuration."""
        settings = Settings(
            JWT_SECRET_KEY="test-secret-key-for-testing-only-32-characters-long",
            DATABASE_URL="postgresql://user:pass@localhost/db"
        )
        assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
    
    def test_azure_settings_optional(self):
        """Test that Azure settings are optional."""
        settings = Settings(
            JWT_SECRET_KEY="test-secret-key-for-testing-only-32-characters-long"
        )
        assert settings.AZURE_OPENAI_API_KEY is None
        assert settings.AZURE_KEY_VAULT_URL is None
        assert settings.AZURE_CLIENT_ID is None
    
    def test_redis_url_configuration(self):
        """Test Redis URL configuration."""
        settings = Settings(
            JWT_SECRET_KEY="test-secret-key-for-testing-only-32-characters-long",
            REDIS_URL="redis://redis-server:6380/1"
        )
        assert settings.REDIS_URL == "redis://redis-server:6380/1"
    
    @patch.dict(os.environ, {
        "JWT_SECRET_KEY": "env-var-secret-key-for-testing-32-chars",
        "APP_NAME": "Test App",
        "DEBUG": "false"
    })
    def test_settings_from_environment(self):
        """Test settings loaded from environment variables."""
        settings = Settings()
        assert settings.JWT_SECRET_KEY == "env-var-secret-key-for-testing-32-chars"
        assert settings.APP_NAME == "Test App"
        assert settings.DEBUG is False
    
    def test_log_level_configuration(self):
        """Test log level configuration."""
        settings = Settings(
            JWT_SECRET_KEY="test-secret-key-for-testing-only-32-characters-long",
            LOG_LEVEL="DEBUG"
        )
        assert settings.LOG_LEVEL == "DEBUG"