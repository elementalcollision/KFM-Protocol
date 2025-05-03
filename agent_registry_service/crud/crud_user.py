from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agent_registry_service.models.user import User
from agent_registry_service.schemas.user import UserCreate # Needed if creating users
from agent_registry_service.core.security import verify_password, get_password_hash

async def get_user_by_username(db: AsyncSession, *, username: str) -> Optional[User]:
    """Get a user by username."""
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()

async def authenticate_user(
    db: AsyncSession, *, username: str, password: str
) -> Optional[User]:
    """Authenticate a user."""
    user = await get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# Optional: Add create_user function if needed later
# async def create_user(db: AsyncSession, *, obj_in: UserCreate) -> User:
#     hashed_password = get_password_hash(obj_in.password)
#     db_obj = User(
#         username=obj_in.username,
#         hashed_password=hashed_password,
#         is_active=obj_in.is_active
#         # Add other fields
#     )
#     db.add(db_obj)
#     await db.commit()
#     await db.refresh(db_obj)
#     return db_obj 