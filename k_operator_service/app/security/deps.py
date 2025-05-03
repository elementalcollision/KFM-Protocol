import logging
from typing import List, Optional, Callable, Coroutine, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError

# Adjust imports based on actual project structure
from k_operator_service.core.config import settings
from k_operator_service.schemas.token import TokenPayload
from k_operator_service.schemas.user import User

logger = logging.getLogger(__name__)

# Define the OAuth2 scheme. tokenUrl is the endpoint clients use to get a token.
# This URL might point to a central auth service or an endpoint within Agent Registry Service.
# For K Operator, it primarily *consumes* tokens, so the exact URL here is less critical
# unless K Operator also provides a login mechanism (unlikely).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/placeholder/token")

async def get_token_payload(token: str = Depends(oauth2_scheme)) -> TokenPayload:
    """Decodes the JWT token and returns the payload if valid."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        # TODO: Add more validation? (e.g., check `aud` audience claim)
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
    Placeholder function to represent fetching user details based on token subject.

    **ASSUMPTION:** In a real system, this would likely call an external User Service
    or query a shared user database based on `payload.sub` to get the actual user
    details, including their permissions.

    For this implementation, it returns a mock User object with example permissions
    based on the user ID (sub).
    """
    user_id = payload.sub
    logger.debug(f"Simulating fetching user details for user_id: {user_id}")

    # --- MOCK PERMISSIONS --- #
    # Replace this with actual permission fetching logic
    mock_permissions = []
    if user_id == "k_operator_admin":
        mock_permissions = ["k_operator:deprecate", "k_operator:archive", "k_operator:delete"]
    elif user_id == "k_operator_user":
        mock_permissions = ["k_operator:deprecate"] # Example limited user
    elif user_id == "policy_engine_service": # Example service account
        mock_permissions = ["k_operator:deprecate", "k_operator:archive"]
    # --- END MOCK PERMISSIONS --- #

    # Construct the placeholder User object
    # Assume user is active unless proven otherwise by the real fetching logic
    user = User(id=user_id, is_active=True, permissions=mock_permissions)
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Checks if the fetched user is active."""
    if not current_user.is_active:
        logger.warning(f"Authentication attempt by inactive user: {current_user.id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def check_permission(required_permission: str) -> Callable[..., Coroutine[Any, Any, None]]:
    """
    Factory function that returns a dependency checking for a specific permission.

    The returned dependency expects an injected `User` object (typically via
    `Depends(get_current_active_user)`) and raises an HTTPException if the
    user lacks the `required_permission`. It returns `None` on success.

    Args:
        required_permission: The permission string required for the endpoint.

    Returns:
        An awaitable dependency function for use with FastAPI's Depends.
    """
    async def _permission_dependency(current_user: User = Depends(get_current_active_user)) -> None:
        """Dependency function that performs the actual permission check. Returns None on success."""
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
        # No return value needed, successful execution implies permission granted
        return None # Explicitly return None

    return _permission_dependency 