from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TokenPayload(BaseModel):
    """JWT token payload schema."""
    sub: str = Field(..., description="Subject (user ID)")
    exp: Optional[datetime] = Field(None, description="Expiration timestamp")
    iat: Optional[datetime] = Field(None, description="Issued at timestamp")
    aud: Optional[str] = Field(None, description="Audience")
    iss: Optional[str] = Field(None, description="Issuer")
    scope: Optional[str] = Field(None, description="Token scope")

class Token(BaseModel):
    """OAuth2 token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    scope: Optional[str] = None 