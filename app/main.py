"""
API Gateway Service for Distributed Notification System
Entry point for all notification requests
Handles authentication, routing, and status tracking
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from datetime import datetime
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.utils import rabbitmq_publisher, redis_client, circuit_breaker
from app.config import settings

from app.route import notification, auth_validation

app = FastAPI(
    title="API Gateway Service",
    description="Entry point for Distributed Notification System",
    version="1.0.0"
)

# Track startup state in app state
app.state.startup_complete = False

# Configure OpenAPI security scheme for Swagger UI Authorize button
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="API Gateway Service",
        version="1.0.0",
        description="Entry point for Distributed Notification System",
        routes=app.routes,
    )
    
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token (get one from /api/v1/auth/login)"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all requests for distributed tracing"""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    
    logger.info(
        f"Incoming request: {request.method} {request.url.path} "
        f"[Correlation-ID: {correlation_id}]"
    )
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standard response format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": exc.detail,
            "message": exc.detail,
            "meta": None
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "meta": None
        }
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Check service health and dependencies"""
    
    # During startup phase, return 200 OK to prevent health check failures
    # This allows the container to stay alive while dependencies initialize
    if not app.state.startup_complete:
        return {
            "status": "starting",
            "service": "api-gateway",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "message": "Service initializing..."
        }
    
    # Once startup is complete, check dependencies
    checks = {
        "rabbitmq": await circuit_breaker.check_rabbitmq_health(),
        "redis": await redis_client.check_health(),
        "service": "up"
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "service": "api-gateway",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "version": "1.0.0"
    }


app.include_router(notification.router)
app.include_router(auth_validation.router)


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    logger.info("Starting API Gateway Service...")
    try:
        await rabbitmq_publisher.connect()
        await redis_client.connect()
        logger.info("✓ RabbitMQ and Redis connections established")
        app.state.startup_complete = True
        logger.info("✓ Startup complete - service is ready")
    except Exception as e:
        logger.error(f"Failed to initialize connections: {str(e)}")
        # Don't raise - allow service to start in degraded mode
        # Health check will report degraded status once startup_complete is True
        app.state.startup_complete = True

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    logger.info("Shutting down API Gateway Service...")
    try:
        await rabbitmq_publisher.disconnect()
        await redis_client.disconnect()
        logger.info("✓ Connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "API Gateway",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
        "health_check": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.ENVIRONMENT == "development"
    )
