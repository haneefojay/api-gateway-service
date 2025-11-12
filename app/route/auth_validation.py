from fastapi import APIRouter, HTTPException, Header
import logging

from app.utils import auth_handler
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.models.responses import StandardResponse


router = APIRouter(
    tags=["Authentication"]
)

@router.post(
    "/api/v1/auth/verify",
    response_model=StandardResponse
)
async def verify_token(token: str = Header(..., alias="Authorization")):
    """
    Verify JWT token validity
    Note: Tokens are issued by User Service, Gateway only validates them
    """
    try:
        if not token.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid token format")
        
        token = token.replace("Bearer ", "")
        payload = auth_handler.verify_token(token)
        
        return StandardResponse(
            success=True,
            data={"valid": True, "user_id": payload.get("user_id")},
            message="Token is valid",
            error=None,
            meta=None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")