"""
Configuration settings for API Gateway Service
Railway-compatible with automatic service discovery
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Service Configuration
    SERVICE_NAME: str = "api-gateway"
    SERVICE_PORT: int = Field(default=8000, validation_alias="PORT")  # Railway provides PORT
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = Field(default="localhost")
    RABBITMQ_PORT: Optional[int] = Field(default=5672)  # Make optional
    RABBITMQ_USER: str = Field(default="guest")
    RABBITMQ_PASS: str = Field(default="guest")
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_EXCHANGE: str = "notifications.direct"
    RABBITMQ_EXCHANGE_TYPE: str = "direct"
    RABBITMQ_URL: Optional[str] = None  # Railway provides this
    
    # Redis Configuration
    REDIS_URL: Optional[str] = None  # Railway provides this
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: Optional[int] = Field(default=6379)  # Make optional
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DECODE_RESPONSES: bool = True
    
    # JWT Authentication
    JWT_SECRET: str = Field(default="change-this-in-production-make-it-very-long-and-random")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Circuit Breaker
    CIRCUIT_BREAKER_FAIL_MAX: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60
    
    # Other Service URLs
    USER_SERVICE_URL: str = "http://localhost:8001"
    TEMPLATE_SERVICE_URL: str = "http://localhost:8002"
    EMAIL_SERVICE_URL: str = "http://localhost:8003"
    PUSH_SERVICE_URL: str = "http://localhost:8004"
    
    # TTLs
    NOTIFICATION_STATUS_TTL: int = 604800
    IDEMPOTENCY_TTL: int = 86400
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @field_validator('RABBITMQ_PORT', 'REDIS_PORT', mode='before')
    @classmethod
    def parse_port(cls, v):
        """Handle empty string ports from Railway"""
        if v == '' or v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Allow population by field name and alias
        populate_by_name = True

    def model_post_init(self, __context):
        """Parse connection URLs after initialization"""
        # Parse REDIS_URL if provided (Railway format)
        if self.REDIS_URL:
            self._parse_redis_url()
        
        # Parse RABBITMQ_URL if provided
        if self.RABBITMQ_URL:
            self._parse_rabbitmq_url()
        
        # Set defaults if still None
        if self.RABBITMQ_PORT is None:
            self.RABBITMQ_PORT = 5672
        if self.REDIS_PORT is None:
            self.REDIS_PORT = 6379
    
    def _parse_redis_url(self):
        """Parse Railway's REDIS_URL format"""
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
                try:
                    self.REDIS_DB = int(parsed.path[1:])
                except:
                    pass
        except Exception as e:
            print(f"Warning: Could not parse REDIS_URL: {e}")
    
    def _parse_rabbitmq_url(self):
        """Parse RABBITMQ_URL format"""
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

# Connection URL helpers
def get_rabbitmq_url() -> str:
    """Construct RabbitMQ connection URL"""
    if settings.RABBITMQ_URL:
        return settings.RABBITMQ_URL
    return (
        f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}"
        f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/{settings.RABBITMQ_VHOST}"
    )

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
