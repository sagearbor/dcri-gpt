import pytest
from fastapi import status
from datetime import datetime


@pytest.mark.api
class TestHealthEndpoints:
    """Test suite for health check endpoints."""
    
    def test_health_check(self, client):
        """Test the /api/v1/health endpoint returns healthy status."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "DCRI GPT"
        assert data["version"] == "1.0.0"
        assert data["environment"] == "testing"
        
        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(data["timestamp"])
        except ValueError:
            pytest.fail("Invalid timestamp format")
    
    def test_readiness_check_development(self, client):
        """Test the /api/v1/ready endpoint in development mode."""
        response = client.get("/api/v1/ready")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "ready" in data
        assert data["ready"] is True  # In development/testing, always ready
        assert data["api"] is True
        assert data["database"] is False  # Not yet implemented
        assert data["redis"] is False     # Not yet implemented
    
    @pytest.mark.asyncio
    async def test_health_check_async(self, async_client):
        """Test the health endpoint with async client."""
        response = await async_client.get("/api/v1/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_root_endpoint(self, client):
        """Test the root endpoint returns welcome message."""
        response = client.get("/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "message" in data
        assert "DCRI GPT" in data["message"]
        assert data["version"] == "1.0.0"
        assert "docs" in data
    
    def test_health_endpoint_response_time(self, client):
        """Test that health endpoint responds quickly."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/health")
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        # Health check should respond in less than 100ms
        assert (end_time - start_time) < 0.1
    
    def test_health_endpoint_headers(self, client):
        """Test that health endpoint returns expected headers."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == status.HTTP_200_OK
        assert "content-type" in response.headers
        assert response.headers["content-type"] == "application/json"