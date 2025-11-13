from fastapi import APIRouter, HTTPException, Header, Request, status, Security
from fastapi.security import HTTPBearer
from datetime import datetime
import uuid
import json
import logging

from app.utils import rabbitmq_publisher, rate_limiter, redis_client, auth_handler, circuit_breaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from app.models.requests import (
    NotificationRequest, 
    StatusUpdateRequest
)


from app.models.responses import StandardResponse, PaginationMeta

# Security scheme for Swagger UI
security = HTTPBearer()

router = APIRouter(
    tags=["Notification"]
)


# Main notification endpoint (updated to match team format)
@router.post(
    "/api/v1/notifications/",
    response_model=StandardResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Security(security)],
)
async def send_notification(
    request: NotificationRequest,
    req: Request,
    credentials = Security(security)
):
    """
    Send notification via email or push
    Returns immediately with notification ID (async processing)
    
    Request format matches team specification:
    - notification_type: email | push
    - user_id: UUID
    - template_code: str (template identifier)
    - variables: UserData (name, link, meta)
    - request_id: str (for idempotency)
    - priority: int (1-5)
    - metadata: Optional[dict]
    """
    try:
        # 1. Verify authentication
        token = credentials.credentials
        payload = auth_handler.verify_token(token)
        authenticated_user_id = payload.get("user_id")
        
        # 2. Check rate limiting
        if not await rate_limiter.check_rate_limit(authenticated_user_id):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # 3. Check idempotency using request_id
        request_id = request.request_id
        cached_response = await redis_client.get_idempotent_response(request_id)
        if cached_response:
            logger.info(f"Returning cached response for request_id: {request_id}")
            return StandardResponse(**json.loads(cached_response))
        
        # 4. Generate notification ID
        notification_id = str(uuid.uuid4())
        correlation_id = req.state.correlation_id
        
        # 5. Prepare message for queue (team format)
        message = {
            "notification_id": notification_id,
            "correlation_id": correlation_id,
            "user_id": str(request.user_id),
            "notification_type": request.notification_type,
            "template_code": request.template_code,
            "variables": {
                "name": request.variables.name,
                "link": str(request.variables.link),
                "meta": request.variables.meta
            },
            "priority": request.priority,
            "metadata": request.metadata,
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        
        # 6. Route to appropriate queue based on notification type
        routing_key = f"notification.{request.notification_type}"
        
        # 7. Publish to RabbitMQ with circuit breaker
        try:
            await circuit_breaker.call(
                rabbitmq_publisher.publish_message,
                exchange="notifications.direct",
                routing_key=routing_key,
                message=message
            )
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Notification service temporarily unavailable"
            )
        
        # 8. Store initial status in Redis
        await redis_client.set_notification_status(
            notification_id,
            {
                "notification_id": notification_id,
                "status": "pending",
                "notification_type": request.notification_type,
                "created_at": datetime.utcnow().isoformat(),
                "user_id": str(request.user_id),
                "template_code": request.template_code
            }
        )
        
        # 9. Prepare response
        response_data = StandardResponse(
            success=True,
            data={
                "notification_id": notification_id,
                "status": "pending",
                "request_id": request_id,
                "notification_type": request.notification_type
            },
            message="Notification queued for processing",
            error=None,
            meta=None
        )
        
        # 10. Cache response for idempotency (24 hours)
        await redis_client.cache_idempotent_response(
            request_id,
            response_data.dict(),
            ttl=86400
        )
        
        logger.info(
            f"Notification queued: {notification_id} "
            f"[Type: {request.notification_type}, User: {request.user_id}, "
            f"Template: {request.template_code}]"
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process notification request"
        )

@router.get(
    "/api/v1/notifications/{notification_id}/status",
    response_model=StandardResponse,
    dependencies=[Security(security)]
)
async def get_notification_status(
    notification_id: str,
    credentials = Security(security)
):
    """Get the current status of a notification"""
    try:
        # Verify authentication
        token = credentials.credentials
        auth_handler.verify_token(token)
        
        # Get status from Redis
        status_data = await redis_client.get_notification_status(notification_id)
        
        if not status_data:
            raise HTTPException(
                status_code=404,
                detail=f"Notification {notification_id} not found"
            )
        
        return StandardResponse(
            success=True,
            data=status_data,
            message="Notification status retrieved",
            error=None,
            meta=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notification status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve status")

# Status update endpoint for Email/Push services
@router.post(
    "/api/v1/{notification_preference}/status/",
    response_model=StandardResponse,
    dependencies=[Security(security)]
)
async def update_notification_status(
    notification_preference: str,
    request: StatusUpdateRequest
):
    """
    Update notification status (called by Email/Push services)
    
    notification_preference: 'email' or 'push' (service identifier)
    
    Request body:
    - notification_id: str
    - status: delivered | pending | failed
    - timestamp: Optional[datetime]
    - error: Optional[str]
    """
    try:
        # Optional authentication for internal services
        # You can add service-to-service authentication here if needed
        
        # Validate notification_preference
        if notification_preference not in ["email", "push"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid notification preference. Must be 'email' or 'push'"
            )
        
        # Prepare status update
        status_update = {
            "notification_id": request.notification_id,
            "status": request.status,
            "notification_type": notification_preference,
            "updated_at": request.timestamp or datetime.utcnow().isoformat(),
            "error_message": request.error
        }
        
        # Update status in Redis
        success = await redis_client.update_notification_status(
            request.notification_id,
            status_update
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Notification {request.notification_id} not found"
            )
        
        logger.info(
            f"Status updated for {request.notification_id}: "
            f"{request.status} [{notification_preference}]"
        )
        
        return StandardResponse(
            success=True,
            data={
                "notification_id": request.notification_id,
                "status": request.status,
                "updated": True
            },
            message="Notification status updated successfully",
            error=None,
            meta=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update notification status"
        )

@router.get(
    "/api/v1/notifications",
    response_model=StandardResponse,
    dependencies=[Security(security)]
)
async def list_notifications(
    page: int = 1,
    limit: int = 10,
    credentials = Security(security)
):
    """List all notifications for the authenticated user"""
    try:
        # Verify authentication
        token = credentials.credentials
        payload = auth_handler.verify_token(token)
        user_id = payload.get("user_id")
        
        # Get notifications from Redis (in production, might use a database)
        notifications = await redis_client.get_user_notifications(
            user_id, 
            page, 
            limit
        )
        
        total = notifications.get("total", 0)
        total_pages = (total + limit - 1) // limit
        
        return StandardResponse(
            success=True,
            data=notifications.get("items", []),
            message="Notifications retrieved",
            error=None,
            meta=PaginationMeta(
                total=total,
                limit=limit,
                page=page,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing notifications: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")