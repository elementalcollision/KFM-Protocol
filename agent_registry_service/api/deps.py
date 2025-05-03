from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from agent_registry_service.core.config import settings
from agent_registry_service.core import security # Added security import
from agent_registry_service.db.session import get_db
from agent_registry_service.models import user as models_user # Alias to avoid name clash
from agent_registry_service.schemas import token as schemas_token
from agent_registry_service.crud import user as crud_user # Alias

# Define the OAuth2 scheme relative to the API base path
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token" # Point to the correct login endpoint
)

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models_user.User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        # Use TokenPayload for validation
        token_data = schemas_token.TokenPayload(**payload) 
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Ensure token_data.sub is not None before using it
    if token_data.sub is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials (missing sub)",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = await crud_user.get_user_by_username(db, username=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_current_active_user(
    current_user: models_user.User = Depends(get_current_user),
) -> models_user.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# You can add dependencies for roles/permissions later, e.g.:
# def get_current_active_superuser(
#     current_user: models.User = Depends(get_current_active_user),
# ) -> models.User:
#     if not crud.user.is_superuser(current_user):
#         raise HTTPException(
#             status_code=403, detail="The user doesn't have enough privileges"
#         )
#     return current_user 