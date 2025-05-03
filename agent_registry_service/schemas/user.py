from pydantic import BaseModel
from typing import Optional
from uuid import UUID

# Shared properties
class UserBase(BaseModel):
    username: str
    is_active: Optional[bool] = True
    # Add email, full_name etc. if needed

# Properties to receive via API on creation (if creating users via API)
class UserCreate(UserBase):
    password: str

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None

# Properties shared by models stored in DB
class UserInDBBase(UserBase):
    id: UUID
    hashed_password: str

    class Config:
        from_attributes = True

# Properties to return to client
class User(UserInDBBase):
    pass # Excludes hashed_password

# Additional properties stored in DB
class UserInDB(UserInDBBase):
    pass 