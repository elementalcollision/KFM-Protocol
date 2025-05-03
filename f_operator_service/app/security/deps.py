import logging
from typing import List, Optional, Callable, Coroutine, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError

from f_operator_service.core.config import get_settings
from f_operator_service.schemas.token import TokenPayload
from f_operator_service.schemas.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

# Define OAuth2 scheme pointing to the central auth service
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

async def get_token_payload(token: str = Depends(oauth2_scheme)) -> TokenPayload:
    """Decodes and validates the JWT token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: Subject (sub) missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token_data
    except JWTError as e:
        logger.warning(f"JWT Error decoding token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValidationError as e:
        logger.warning(f"Token payload validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(payload: TokenPayload = Depends(get_token_payload)) -> User:
    """
    Get current user details from token payload.
    In production, this would typically call a user service or database.
    """
    try:
        user_id = UUID(payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Mock permissions based on user ID
    # In production, these would come from a user service or database
    mock_permissions = []
    if str(user_id) == "00000000-0000-0000-0000-000000000001":  # Admin
        mock_permissions = [
            "templates:create", "templates:read", "templates:update", "templates:delete",
            "criteria:create", "criteria:read", "criteria:update", "criteria:delete",
            "promotion:review", "promotion:approve"
        ]
    elif str(user_id) == "00000000-0000-0000-0000-000000000002":  # Regular user
        mock_permissions = [
            "templates:read",
            "criteria:read",
            "promotion:review"
        ]

    user = User(
        id=user_id,
        is_active=True,
        permissions=mock_permissions,
        role="admin" if len(mock_permissions) > 3 else "user"
    )
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Verify the user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def check_permission(required_permission: str) -> Callable[..., Coroutine[Any, Any, None]]:
    """
    Create a dependency that checks for a specific permission.
    
    Usage:
        @router.post("/endpoint", dependencies=[Depends(check_permission("templates:create"))])
    """
    async def _permission_dependency(current_user: User = Depends(get_current_active_user)) -> None:
        if required_permission not in current_user.permissions:
            logger.warning(
                f"Permission denied for user '{current_user.id}'. "
                f"Required: '{required_permission}', "
                f"User has: {current_user.permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Requires: {required_permission}"
            )
        logger.debug(f"Permission check passed for user '{current_user.id}' (required: '{required_permission}')")
        return None

    return _permission_dependency 