# API Gateway Service

Entry point for the Distributed Notification System. Handles authentication, request routing, and notification status tracking.

## Features

- ✅ JWT Authentication
- ✅ Request validation and routing
- ✅ RabbitMQ message publishing
- ✅ Redis-based status tracking
- ✅ Rate limiting (100 requests/minute)
- ✅ Circuit breaker pattern
- ✅ Idempotency handling
- ✅ Correlation ID tracking
- ✅ Health checks
- ✅ snake_case naming convention

## Tech Stack

- **Python 3.13**
- **FastAPI** - Web framework
- **RabbitMQ** - Message queue
- **Redis** - Caching and status storage
- **JWT** - Authentication
- **Docker** - Containerization

## Project Structure

```
api-gateway/
├── app/
|   ├── core/
|   |   ├── __init__.py
|   |   ├── auth.py              # JWT authentication
|   |   ├── circuit_breaker.py   # Circuit breaker pattern
|   |   ├── rabbitmq.py          # RabbitMQ publisher
|   |   ├── rate_limiter.py      # Rate limiting
|   |   └── redis_client.py      # Redis operations
|   ├── models/
│   |   ├── __init__.py
│   |   ├── requests.py          # Request models
│   |   └── responses.py         # Response models
|   ├── config.py                # Configuration settings
|   ├── main.py                  # Main application
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker configuration
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

## Installation

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd api-gateway
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Start required services** (RabbitMQ and Redis)
```bash
# Using Docker
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

6. **Run the application**
```bash
uvicorn main:app --reload --port 8000
```

### Docker Deployment

1. **Build Docker image**
```bash
docker build -t api-gateway:latest .
```

2. **Run container**
```bash
docker run -d \
  --name api-gateway \
  -p 8000:8000 \
  --env-file .env \
  api-gateway:latest
```

## API Endpoints

### Authentication


#### Verify Token
```http
POST /api/v1/auth/verify
Authorization: Bearer <token>

Response:
{
  "success": true,
  "data": {
    "valid": true,
    "user_id": "user-id"
  },
  "message": "Token is valid",
  "error": null,
  "meta": null
}
```

### Notifications

#### Send Notification
```http
POST /api/v1/notifications/send
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "notification_type": "email",
  "template_id": "welcome_email",
  "variables": {
    "name": "John Doe",
    "link": "https://example.com/verify"
  },
  "priority": "normal",
  "idempotency_key": "unique-key-12345"
}

Response (202 Accepted):
{
  "success": true,
  "data": {
    "notification_id": "notif-uuid",
    "status": "pending",
    "message": "Email notification queued successfully"
  },
  "message": "Notification queued for processing",
  "error": null,
  "meta": null
}
```

#### Get Notification Status
```http
GET /api/v1/notifications/{notification_id}/status
Authorization: Bearer <token>

Response:
{
  "success": true,
  "data": {
    "notification_id": "notif-uuid",
    "status": "sent",
    "notification_type": "email",
    "created_at": "2025-11-09T10:30:00Z",
    "updated_at": "2025-11-09T10:30:05Z"
  },
  "message": "Notification status retrieved",
  "error": null,
  "meta": null
}
```

#### List Notifications
```http
GET /api/v1/notifications?page=1&limit=10
Authorization: Bearer <token>

Response:
{
  "success": true,
  "data": [...],
  "message": "Notifications retrieved",
  "error": null,
  "meta": {
    "total": 100,
    "limit": 10,
    "page": 1,
    "total_pages": 10,
    "has_next": true,
    "has_previous": false
  }
}
```

### Health Check

```http
GET /health

Response:
{
  "status": "healthy",
  "service": "api-gateway",
  "timestamp": "2025-11-09T10:30:00Z",
  "checks": {
    "rabbitmq": true,
    "redis": true,
    "service": "up"
  },
  "version": "1.0.0"
}
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| SERVICE_PORT | Service port | 8000 |
| RABBITMQ_HOST | RabbitMQ host | localhost |
| RABBITMQ_PORT | RabbitMQ port | 5672 |
| REDIS_HOST | Redis host | localhost |
| REDIS_PORT | Redis port | 6379 |
| JWT_SECRET | JWT secret key | (change in production!) |
| RATE_LIMIT_REQUESTS | Max requests per window | 100 |
| RATE_LIMIT_WINDOW | Rate limit window (seconds) | 60 |

## Key Features Explained

### 1. Circuit Breaker
Prevents cascading failures when RabbitMQ is down:
- Opens after 5 consecutive failures
- Blocks requests for 60 seconds
- Half-open state tests recovery

### 2. Rate Limiting
Prevents abuse:
- 100 requests per 60 seconds per user
- Redis-based tracking
- Configurable limits

### 3. Idempotency
Prevents duplicate notifications:
- Uses `idempotency_key` from request
- Caches responses for 24 hours
- Returns cached response for duplicate requests

### 4. Correlation ID
Enables distributed tracing:
- Generated for each request
- Passed through all services
- Included in logs and headers

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_main.py
```

## Monitoring

### Logs
```bash
# View application logs
tail -f logs/api-gateway.log

# In Docker
docker logs -f api-gateway
```

### Metrics to Monitor
- Request rate
- Error rate
- Response time
- Circuit breaker state
- Queue depth
- Rate limit hits

## Troubleshooting

### RabbitMQ Connection Failed
```bash
# Check RabbitMQ is running
docker ps | grep rabbitmq

# Check RabbitMQ logs
docker logs rabbitmq

# Test connection
curl http://localhost:15672  # Management UI
```

### Redis Connection Failed
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli ping  # Should return PONG
```

### Rate Limit Issues
```bash
# Reset rate limit for user
redis-cli DEL rate_limit:user-id
```

## Development

### Adding New Endpoints
1. Define request/response models in `models/`
2. Add endpoint in `main.py`
3. Add tests
4. Update documentation

### Code Style
- Follow PEP 8
- Use snake_case for all variables/functions
- Add docstrings to all functions
- Type hints required

## Production Deployment

### Security Checklist
- [ ] Change JWT_SECRET to strong random value
- [ ] Use HTTPS
- [ ] Set DEBUG=false
- [ ] Configure proper CORS origins
- [ ] Enable firewall rules
- [ ] Set up monitoring and alerts
- [ ] Configure log rotation
- [ ] Use secrets management (not .env file)

### Performance
- Horizontal scaling: Run multiple instances behind load balancer
- Redis connection pooling: max_connections=10
- RabbitMQ persistent connections
- Health checks for orchestration

## API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Support

For issues or questions:
- Check logs first
- Review health check endpoint
- Verify environment variables
- Check RabbitMQ and Redis connectivity

## License

HNG Internship Stage 4 Project