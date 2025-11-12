from app.core.rabbitmq import RabbitMQPublisher
from app.core.redis_client import RedisClient
from app.core.auth import AuthHandler
from app.core.rate_limiter import RateLimiter
from app.core.circuit_breaker import CircuitBreaker

rabbitmq_publisher = RabbitMQPublisher()
redis_client = RedisClient()
auth_handler = AuthHandler()
rate_limiter = RateLimiter(redis_client)
circuit_breaker = CircuitBreaker()