"""
Rate Limiter for API Gateway
Prevents abuse and ensures fair usage
"""

import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter using Redis"""
    
    def __init__(self, redis_client):
        """
        Initialize rate limiter
        
        Args:
            redis_client: RedisClient instance
        """
        self.redis = redis_client
        self.max_requests = settings.RATE_LIMIT_REQUESTS
        self.window = settings.RATE_LIMIT_WINDOW
    
    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: Optional[int] = None,
        window: Optional[int] = None
    ) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            identifier: Unique identifier (user_id, IP, etc.)
            max_requests: Optional override for max requests
            window: Optional override for time window
            
        Returns:
            True if within limit, False if exceeded
        """
        try:
            max_req = max_requests or self.max_requests
            win = window or self.window
            
            # Increment counter
            current_count = await self.redis.increment_rate_limit(
                identifier,
                win
            )
            
            # Check if exceeded
            if current_count > max_req:
                logger.warning(
                    f"Rate limit exceeded for {identifier}: "
                    f"{current_count}/{max_req} in {win}s window"
                )
                return False
            
            # Log if approaching limit
            if current_count > max_req * 0.8:
                logger.info(
                    f"Rate limit warning for {identifier}: "
                    f"{current_count}/{max_req}"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            # On error, allow request (fail open)
            return True
    
    async def get_remaining_requests(self, identifier: str) -> int:
        """
        Get remaining requests for identifier
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Number of remaining requests
        """
        try:
            current_count = await self.redis.get_rate_limit_count(identifier)
            remaining = max(0, self.max_requests - current_count)
            return remaining
        except Exception as e:
            logger.error(f"Error getting remaining requests: {str(e)}")
            return self.max_requests
    
    async def reset_rate_limit(self, identifier: str) -> bool:
        """
        Manually reset rate limit for identifier
        
        Args:
            identifier: Unique identifier
            
        Returns:
            True if reset successfully
        """
        try:
            key = f"rate_limit:{identifier}"
            await self.redis.client.delete(key)
            logger.info(f"Rate limit reset for {identifier}")
            return True
        except Exception as e:
            logger.error(f"Error resetting rate limit: {str(e)}")
            return False