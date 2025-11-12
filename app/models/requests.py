"""
Request models for API Gateway
All models use snake_case naming convention
Matches team-agreed format specifications
"""

from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Dict, Any, Optional
from enum import Enum
from uuid import UUID
import uuid

class NotificationType(str, Enum):
    """Supported notification types"""
    email = "email"
    push = "push"

class UserData(BaseModel):
    """User data for template variables"""
    name: str = Field(..., description="User's name")
    link: HttpUrl = Field(..., description="Action link for notification")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Doe",
                "link": "https://example.com/verify/abc123",
                "meta": {"source": "web", "campaign": "welcome"}
            }
        }

class NotificationRequest(BaseModel):
    """Request model for sending notifications"""
    notification_type: NotificationType = Field(
        ...,
        description="Type of notification to send"
    )
    user_id: UUID = Field(
        ...,
        description="Target user UUID"
    )
    template_code: str = Field(
        ...,
        description="Template code or path to use for notification"
    )
    variables: UserData = Field(
        ...,
        description="User data variables for template"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request identifier for idempotency"
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Notification priority (1=lowest, 5=highest)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata for notification"
    )
    
    @validator("template_code")
    def validate_template_code(cls, v):
        """Validate template_code is not empty"""
        if not v or not v.strip():
            raise ValueError("template_code cannot be empty")
        return v.strip()
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "notification_type": "email",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "template_code": "welcome_email",
                "variables": {
                    "name": "John Doe",
                    "link": "https://example.com/verify/abc123",
                    "meta": {"source": "signup"}
                },
                "request_id": "unique-request-12345",
                "priority": 2,
                "metadata": {"campaign": "onboarding", "version": "v2"}
            }
        }

class NotificationStatus(str, Enum):
    """Notification status values"""
    delivered = "delivered"
    pending = "pending"
    failed = "failed"

class StatusUpdateRequest(BaseModel):
    """Request model for updating notification status (from Email/Push services)"""
    notification_id: str = Field(..., description="Unique notification identifier")
    status: NotificationStatus = Field(..., description="Current notification status")
    timestamp: Optional[str] = Field(None, description="Status update timestamp (ISO 8601)")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "notification_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "delivered",
                "timestamp": "2025-11-09T10:30:00Z",
                "error": None
            }
        }