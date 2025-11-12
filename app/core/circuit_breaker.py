"""
Circuit Breaker pattern implementation
Prevents cascading failures in distributed system
"""

import logging
from datetime import datetime
from typing import Callable, Any
from enum import Enum
from app.config import settings

logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(
        self,
        fail_max: int = None,
        timeout_duration: int = None
    ):
        """
        Initialize circuit breaker
        
        Args:
            fail_max: Maximum failures before opening circuit
            timeout_duration: Seconds before attempting recovery
        """
        self.fail_max = fail_max or settings.CIRCUIT_BREAKER_FAIL_MAX
        self.timeout_duration = timeout_duration or settings.CIRCUIT_BREAKER_TIMEOUT
        
        # State tracking
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._should_attempt_reset():
                logger.info("Circuit breaker entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
            else:
                logger.warning("Circuit breaker is OPEN, rejecting request")
                raise Exception("Service temporarily unavailable (circuit breaker open)")
        
        try:
            # Execute function
            result = await func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker test successful, closing circuit")
                self._on_success()
            
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            
            return result
            
        except Exception as e:
            # Failure - increment counter
            self._on_failure()
            logger.error(f"Circuit breaker caught error: {str(e)}")
            raise
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.info("Circuit breaker closed after successful recovery")
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        logger.warning(
            f"Circuit breaker failure count: {self.failure_count}/{self.fail_max}"
        )
        
        # Open circuit if threshold reached
        if self.failure_count >= self.fail_max:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Will retry after {self.timeout_duration}s"
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout_duration
    
    async def check_rabbitmq_health(self) -> bool:
        """Check RabbitMQ health (used by health endpoint)"""
        try:
            if self.state == CircuitState.OPEN:
                return False
            return True
        except:
            return False
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": (
                self.last_failure_time.isoformat()
                if self.last_failure_time else None
            )
        }
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        logger.info("Circuit breaker manually reset")