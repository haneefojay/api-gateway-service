"""
Unit tests for API Gateway Service
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from core.auth import AuthHandler

# Test client
client = TestClient(app)

# Mock dependencies
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock external dependencies for testing"""
    
    with patch('main.rabbitmq_publisher') as mock_rabbitmq, \
         patch('main.redis_client') as mock_redis, \
         patch('main.rate_limiter') as mock_rate_limiter, \
         patch('main.circuit_breaker') as mock_circuit_breaker:
        
        # Mock RabbitMQ
        mock_rabbitmq.connect = AsyncMock()
        mock_rabbitmq.publish_message = AsyncMock(return_value=True)
        mock_rabbitmq.check_health = AsyncMock(return_value=True)
        
        # Mock Redis
        mock_redis.connect = AsyncMock()
        mock_redis.check_health = AsyncMock(return_value=True)
        mock_redis.set_notification_status = AsyncMock(return_value=True)
        mock_redis.get_notification_status = AsyncMock(return_value={
            "status": "pending",
            "notification_type": "email",
            "created_at": "2025-11-09T10:00:00Z"
        })
        mock_redis.cache_idempotent_response = AsyncMock(return_value=True)
        mock_redis.get_idempotent_response = AsyncMock(return_value=None)
        
        # Mock rate limiter
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=True)
        
        # Mock circuit breaker
        mock_circuit_breaker.call = AsyncMock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
        mock_circuit_breaker.check_rabbitmq_health = AsyncMock(return_value=True)
        
        yield

class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check_success(self):
        """Test successful health check"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "api-gateway"
        assert "checks" in data
        assert "timestamp" in data

class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_success(self):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
    
    def test_login_missing_email(self):
        """Test login with missing email"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "password": "password123"
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_verify_token_invalid_format(self):
        """Test token verification with invalid format"""
        response = client.post(
            "/api/v1/auth/verify",
            headers={"Authorization": "InvalidFormat"}
        )
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False

class TestNotifications:
    """Test notification endpoints"""
    
    def get_auth_token(self):
        """Helper to get auth token"""
        auth_handler = AuthHandler()
        return auth_handler.create_access_token(
            data={"sub": "test@example.com", "user_id": "test-user-123"}
        )
    
    def test_send_notification_success(self):
        """Test sending notification successfully"""
        token = self.get_auth_token()
        
        response = client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "user-123",
                "notification_type": "email",
                "template_id": "welcome_email",
                "variables": {"name": "John Doe"},
                "priority": "normal",
                "idempotency_key": "test-key-123"
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert "notification_id" in data["data"]
        assert data["data"]["status"] == "pending"
    
    def test_send_notification_missing_auth(self):
        """Test sending notification without authentication"""
        response = client.post(
            "/api/v1/notifications/send",
            json={
                "user_id": "user-123",
                "notification_type": "email",
                "template_id": "welcome_email",
                "variables": {"name": "John Doe"}
            }
        )
        
        assert response.status_code == 422  # Missing auth header
    
    def test_send_notification_invalid_type(self):
        """Test sending notification with invalid type"""
        token = self.get_auth_token()
        
        response = client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "user-123",
                "notification_type": "invalid",
                "template_id": "welcome_email",
                "variables": {}
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_notification_status(self):
        """Test getting notification status"""
        token = self.get_auth_token()
        
        response = client.get(
            "/api/v1/notifications/test-notification-id/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data["data"]
    
    def test_list_notifications(self):
        """Test listing notifications"""
        token = self.get_auth_token()
        
        response = client.get(
            "/api/v1/notifications?page=1&limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "meta" in data
        assert data["meta"]["page"] == 1
        assert data["meta"]["limit"] == 10

class TestResponseFormat:
    """Test standard response format"""
    
    def test_response_format_structure(self):
        """Test all responses follow standard format"""
        response = client.get("/health")
        assert response.status_code == 200
        
        # Health endpoint has different format, test with auth
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "error" in data
        assert "message" in data
        assert "meta" in data
    
    def test_snake_case_convention(self):
        """Test response uses snake_case"""
        auth_handler = AuthHandler()
        token = auth_handler.create_access_token(
            data={"sub": "test@example.com", "user_id": "test-123"}
        )
        
        response = client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "user-123",
                "notification_type": "email",
                "template_id": "welcome",
                "variables": {}
            }
        )
        
        data = response.json()
        # Check keys use snake_case
        assert "notification_id" in str(data)
        assert "notificationId" not in str(data)

class TestErrorHandling:
    """Test error handling"""
    
    def test_404_not_found(self):
        """Test 404 error handling"""
        response = client.get("/non-existent-endpoint")
        assert response.status_code == 404
    
    def test_validation_error_format(self):
        """Test validation errors return proper format"""
        response = client.post(
            "/api/v1/auth/login",
            json={"invalid": "data"}
        )
        
        assert response.status_code == 422

class TestRateLimiting:
    """Test rate limiting (basic tests)"""
    
    @patch('main.rate_limiter')
    def test_rate_limit_exceeded(self, mock_rate_limiter):
        """Test rate limit exceeded response"""
        mock_rate_limiter.check_rate_limit = AsyncMock(return_value=False)
        
        auth_handler = AuthHandler()
        token = auth_handler.create_access_token(
            data={"sub": "test@example.com", "user_id": "test-123"}
        )
        
        response = client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "user-123",
                "notification_type": "email",
                "template_id": "welcome",
                "variables": {}
            }
        )
        
        # Should get rate limit error
        assert response.status_code in [429, 503]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])