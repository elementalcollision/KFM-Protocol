from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class User(BaseModel):
    """User schema with permissions."""
    id: UUID = Field(..., description="User ID")
    is_active: bool = Field(True, description="Whether the user is active")
    permissions: List[str] = Field(default_factory=list, description="List of permission strings")
    name: Optional[str] = Field(None, description="User's display name")
    email: Optional[str] = Field(None, description="User's email address")
    role: Optional[str] = Field(None, description="User's role") 