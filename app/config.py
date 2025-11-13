"""
Configuration settings for API Gateway Service
Railway-compatible with automatic service discovery
"""

from pydantic import BaseSettings, Field
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Service Configuration
    SERVICE_NAME: str = "api-gateway"
    SERVICE_PORT: int = Field(default=8000, env="PORT")  # Railway provides PORT
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # RabbitMQ Configuration
    # Railway provides these automatically when you add RabbitMQ service
    RABBITMQ_HOST: str = Field(default="localhost")
    RABBITMQ_PORT: int = Field(default=5672)
    RABBITMQ_USER: str = Field(default="guest")
    RABBITMQ_PASS: str = Field(default="guest")
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_EXCHANGE: str = "notifications.direct"
    RABBITMQ_EXCHANGE_TYPE: str = "direct"
    
    # Alternative: Parse from RABBITMQ_URL if Railway provides it
    RABBITMQ_URL: Optional[str] = None
    
    # Redis Configuration
    # Railway provides REDIS_URL (redis://default:password@host:port)
    REDIS_URL: Optional[str] = None
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DECODE_RESPONSES: bool = True
    
    # JWT Authentication
    JWT_SECRET: str = Field(..., min_length=32)  # Required, must be set
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600  # 1 hour in seconds
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Circuit Breaker
    CIRCUIT_BREAKER_FAIL_MAX: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60
    
    # Other Service URLs (for inter-service communication)
    USER_SERVICE_URL: str = "http://localhost:8001"
    TEMPLATE_SERVICE_URL: str = "http://localhost:8002"
    EMAIL_SERVICE_URL: str = "http://localhost:8003"
    PUSH_SERVICE_URL: str = "http://localhost:8004"
    
    # Notification Status TTL (in Redis)
    NOTIFICATION_STATUS_TTL: int = 604800  # 7 days in seconds
    
    # Idempotency Cache TTL
    IDEMPOTENCY_TTL: int = 86400  # 24 hours in seconds
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse REDIS_URL if provided (Railway format)
        if self.REDIS_URL and not self.REDIS_PASSWORD:
            self._parse_redis_url()
        # Parse RABBITMQ_URL if provided
        if self.RABBITMQ_URL:
            self._parse_rabbitmq_url()
    
    def _parse_redis_url(self):
        """Parse Railway's REDIS_URL format: redis://default:password@host:port/db"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.REDIS_URL)
            if parsed.hostname:
                self.REDIS_HOST = parsed.hostname
            if parsed.port:
                self.REDIS_PORT = parsed.port
            if parsed.password:
                self.REDIS_PASSWORD = parsed.password
            if parsed.path and len(parsed.path) > 1:
                self.REDIS_DB = int(parsed.path[1:])
        except Exception as e:
            print(f"Warning: Could not parse REDIS_URL: {e}")
    
    def _parse_rabbitmq_url(self):
        """Parse RABBITMQ_URL format: amqp://user:pass@host:port/vhost"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.RABBITMQ_URL)
            if parsed.hostname:
                self.RABBITMQ_HOST = parsed.hostname
            if parsed.port:
                self.RABBITMQ_PORT = parsed.port
            if parsed.username:
                self.RABBITMQ_USER = parsed.username
            if parsed.password:
                self.RABBITMQ_PASS = parsed.password
            if parsed.path and len(parsed.path) > 1:
                self.RABBITMQ_VHOST = parsed.path[1:]
        except Exception as e:
            print(f"Warning: Could not parse RABBITMQ_URL: {e}")

# Create settings instance
settings = Settings()

# RabbitMQ connection URL
def get_rabbitmq_url() -> str:
    """Construct RabbitMQ connection URL"""
    if settings.RABBITMQ_URL:
        return settings.RABBITMQ_URL
    return (
        f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}"
        f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/{settings.RABBITMQ_VHOST}"
    )

# Redis connection URL
def get_redis_url() -> str:
    """Construct Redis connection URL"""
    if settings.REDIS_URL:
        return settings.REDIS_URL
    if settings.REDIS_PASSWORD:
        return (
            f"redis://:{settings.REDIS_PASSWORD}"
            f"@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        )
    return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
