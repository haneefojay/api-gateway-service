"""
Response models for API Gateway
All models use snake_case naming convention
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

class PaginationMeta(BaseModel):
    """Pagination metadata for list responses"""
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Items per page")
    page: int = Field(..., description="Current page number")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    
    class Config:
        schema_extra = {
            "example": {
                "total": 100,
                "limit": 10,
                "page": 1,
                "total_pages": 10,
                "has_next": True,
                "has_previous": False
            }
        }

class StandardResponse(BaseModel):
    """Standard response format for all API endpoints"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if request failed")
    message: str = Field(..., description="Human-readable message")
    meta: Optional[PaginationMeta] = Field(None, description="Pagination metadata for list responses")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "notification_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "pending"
                },
                "error": None,
                "message": "Notification queued for processing",
                "meta": None
            }
        }

class NotificationStatusResponse(BaseModel):
    """Response model for notification status"""
    notification_id: str = Field(..., description="Unique notification identifier")
    status: str = Field(..., description="Current notification status")
    notification_type: str = Field(..., description="Type of notification")
    created_at: str = Field(..., description="Timestamp when notification was created")
    updated_at: Optional[str] = Field(None, description="Timestamp of last update")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    
    class Config:
        schema_extra = {
            "example": {
                "notification_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "sent",
                "notification_type": "email",
                "created_at": "2025-11-09T10:30:00Z",
                "updated_at": "2025-11-09T10:30:05Z",
                "error_message": None,
                "retry_count": 0
            }
        }

class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint"""
    status: str = Field(..., description="Overall service health status")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Current timestamp")
    checks: Dict[str, Any] = Field(..., description="Individual component health checks")
    version: str = Field(..., description="Service version")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "service": "api-gateway",
                "timestamp": "2025-11-09T10:30:00Z",
                "checks": {
                    "rabbitmq": True,
                    "redis": True,
                    "service": "up"
                },
                "version": "1.0.0"
            }
        }

class AuthResponse(BaseModel):
    """Response model for authentication"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }