"""
Authentication handler for API Gateway
JWT token generation and validation
"""

from datetime import datetime, timedelta
from typing import Dict
from jose import JWTError, jwt
from fastapi import HTTPException, status
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class AuthHandler:
    """Handle JWT authentication"""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration = settings.JWT_EXPIRATION
    
    
    def verify_token(self, token: str) -> Dict:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verify token type
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
            
        except JWTError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    

    def create_refresh_token(self, data: Dict) -> str:
        """
        Create refresh token (longer expiration)
        
        Args:
            data: Payload data
            
        Returns:
            Encoded refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        return jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm
        )