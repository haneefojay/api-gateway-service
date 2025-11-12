"""
Redis Client for API Gateway
Handles caching, status tracking, and idempotency
"""

import redis.asyncio as redis
import json
import logging
from typing import Dict, Any, Optional
from app.config import settings, get_redis_url

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client for caching and data storage"""
    
    def __init__(self):
        self.client = None
    
    async def connect(self):
        """Establish connection to Redis"""
        try:
            self.client = await redis.from_url(
                get_redis_url(),
                decode_responses=settings.REDIS_DECODE_RESPONSES,
                max_connections=10
            )
            
            # Test connection
            await self.client.ping()
            logger.info("✓ Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        try:
            if self.client:
                await self.client.close()
                logger.info("✓ Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")
    
    async def check_health(self) -> bool:
        """Check Redis connection health"""
        try:
            if self.client:
                await self.client.ping()
                return True
            return False
        except:
            return False
    
    # Notification Status Management
    async def set_notification_status(
        self,
        notification_id: str,
        status_data: Dict[str, Any]
    ) -> bool:
        """
        Store notification status in Redis
        
        Args:
            notification_id: Unique notification identifier
            status_data: Status information dictionary
            
        Returns:
            bool: True if stored successfully
        """
        try:
            key = f"notification:status:{notification_id}"
            await self.client.setex(
                key,
                settings.NOTIFICATION_STATUS_TTL,
                json.dumps(status_data)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set notification status: {str(e)}")
            return False
    
    async def get_notification_status(
        self,
        notification_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve notification status from Redis
        
        Args:
            notification_id: Unique notification identifier
            
        Returns:
            Dict with status data or None if not found
        """
        try:
            key = f"notification:status:{notification_id}"
            data = await self.client.get(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get notification status: {str(e)}")
            return None
    
    async def update_notification_status(
        self,
        notification_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update notification status
        
        Args:
            notification_id: Unique notification identifier
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if updated successfully
        """
        try:
            # Get existing status
            current = await self.get_notification_status(notification_id)
            if not current:
                return False
            
            # Merge updates
            current.update(updates)
            
            # Save back
            return await self.set_notification_status(notification_id, current)
        except Exception as e:
            logger.error(f"Failed to update notification status: {str(e)}")
            return False
    
    # Idempotency Management
    async def cache_idempotent_response(
        self,
        idempotency_key: str,
        response_data: Dict[str, Any],
        ttl: int = None
    ) -> bool:
        """
        Cache response for idempotent requests
        
        Args:
            idempotency_key: Unique request identifier
            response_data: Response to cache
            ttl: Time to live in seconds (default from settings)
            
        Returns:
            bool: True if cached successfully
        """
        try:
            key = f"idempotent:{idempotency_key}"
            ttl = ttl or settings.IDEMPOTENCY_TTL
            
            await self.client.setex(
                key,
                ttl,
                json.dumps(response_data)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache idempotent response: {str(e)}")
            return False
    
    async def get_idempotent_response(
        self,
        idempotency_key: str
    ) -> Optional[str]:
        """
        Retrieve cached response for idempotent request
        
        Args:
            idempotency_key: Unique request identifier
            
        Returns:
            Cached response or None
        """
        try:
            key = f"idempotent:{idempotency_key}"
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Failed to get idempotent response: {str(e)}")
            return None
    
    # User Notifications List (simplified implementation)
    async def get_user_notifications(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get list of user notifications (paginated)
        
        Args:
            user_id: User identifier
            page: Page number
            limit: Items per page
            
        Returns:
            Dictionary with items and total count
        """
        try:
            # In production, this would query a database
            # For now, we'll return a mock response
            # You can implement proper storage later
            
            pattern = f"notification:status:*"
            keys = []
            
            async for key in self.client.scan_iter(match=pattern, count=100):
                data = await self.client.get(key)
                if data:
                    notification = json.loads(data)
                    if notification.get("user_id") == user_id:
                        keys.append(notification)
            
            # Pagination
            total = len(keys)
            start = (page - 1) * limit
            end = start + limit
            items = keys[start:end]
            
            return {
                "items": items,
                "total": total
            }
        except Exception as e:
            logger.error(f"Failed to get user notifications: {str(e)}")
            return {"items": [], "total": 0}
    
    # Rate Limiting Support
    async def increment_rate_limit(
        self,
        key: str,
        window: int
    ) -> int:
        """
        Increment rate limit counter
        
        Args:
            key: Rate limit key (e.g., user_id)
            window: Time window in seconds
            
        Returns:
            Current count
        """
        try:
            rate_key = f"rate_limit:{key}"
            
            # Increment counter
            count = await self.client.incr(rate_key)
            
            # Set expiry on first request
            if count == 1:
                await self.client.expire(rate_key, window)
            
            return count
        except Exception as e:
            logger.error(f"Failed to increment rate limit: {str(e)}")
            return 0
    
    async def get_rate_limit_count(self, key: str) -> int:
        """Get current rate limit count"""
        try:
            rate_key = f"rate_limit:{key}"
            count = await self.client.get(rate_key)
            return int(count) if count else 0
        except:
            return 0