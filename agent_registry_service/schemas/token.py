from pydantic import BaseModel
from typing import Optional
from uuid import UUID # Import UUID if user ID is UUID

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None # Subject (e.g., username or user ID)
    # If using UUID for user ID:
    # sub: Optional[UUID] = None 