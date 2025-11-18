"""
JWT Authentication for MCP Server.
"""

from jose import JWTError, jwt
import logging

from mcp_server.config import settings

logger = logging.getLogger(__name__)


class User:
    """User model extracted from JWT."""
    
    def __init__(self, user_id: str, scopes: list[str]):
        self.user_id = user_id
        self.scopes = scopes


def verify_jwt_token(token: str) -> dict:
    """
    Verify JWT token and return decoded payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded JWT payload
        
    Raises:
        ValueError: If token is invalid, expired, or missing required claims
    """
    try:
        # Decode and verify JWT
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
            }
        )
        
        # Verify issuer
        if payload.get("iss") != settings.JWT_ISSUER:
            logger.warning(f"Invalid issuer: {payload.get('iss')}")
            raise ValueError("Invalid token issuer")
        
        # Extract required claims
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Missing 'sub' claim in JWT")
            raise ValueError("Missing user identifier in token")
        
        # Extract scopes
        scopes = payload.get("scopes", [])
        if not isinstance(scopes, list):
            scopes = []
        
        logger.info(f"Token verified for user_id: {user_id}, scopes: {scopes}")
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise ValueError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        raise ValueError(f"Token verification failed: {str(e)}")
