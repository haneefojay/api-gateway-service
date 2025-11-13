"""
Configuration settings for API Gateway Service
Uses environment variables with sensible defaults
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Service Configuration
    SERVICE_NAME: str
    SERVICE_PORT: int
    ENVIRONMENT: str
    DEBUG: bool
    
    # RabbitMQ Configuration
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USER: str
    RABBITMQ_PASS: str
    RABBITMQ_VHOST: str
    RABBITMQ_EXCHANGE: str
    RABBITMQ_EXCHANGE_TYPE: str
    
    # Redis Configuration
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int 
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DECODE_RESPONSES: bool
    
    # JWT Authentication
    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRATION: int
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int
    RATE_LIMIT_WINDOW: int
    
    # Circuit Breaker
    CIRCUIT_BREAKER_FAIL_MAX: int = 5  # failures before opening
    CIRCUIT_BREAKER_TIMEOUT: int = 60  # timeout duration in seconds
    
    # Other Service URLs (for inter-service communication)
    USER_SERVICE_URL: str = "http://localhost:8001"
    TEMPLATE_SERVICE_URL: str = "http://localhost:8002"
    EMAIL_SERVICE_URL: str = "http://localhost:8003"
    PUSH_SERVICE_URL: str = "http://localhost:8004"
    
    # Notification Status TTL (in Redis)
    NOTIFICATION_STATUS_TTL: int
    
    # Idempotency Cache TTL
    IDEMPOTENCY_TTL: int
    
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
    return (
        f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}"
        f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/{settings.RABBITMQ_VHOST}"
    )

# Redis connection URL
def get_redis_url() -> str:
    """Construct Redis connection URL"""
    if settings.REDIS_PASSWORD:
        return (
            f"redis://:{settings.REDIS_PASSWORD}"
            f"@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        )
    return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
