from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from agent_registry_service.models.agent import LifecycleStateEnum

# Shared properties
class AgentBase(BaseModel):
    type: str = Field(..., description="Type of the agent (e.g., 'Software Artifact', 'AI Model')")
    version: str = Field(..., description="Version identifier (e.g., '1.2.3', git hash)")
    owner: Optional[str] = Field(None, description="Identifier for the owner/team")
    maintainer: Optional[str] = Field(None, description="Identifier for the maintainer/team")
    lifecycle_state: Optional[LifecycleStateEnum] = Field(LifecycleStateEnum.NEW, description="Current lifecycle state")

    class Config:
        use_enum_values = True # Serialize enums to their values

# Properties to receive via API on creation
class AgentCreate(AgentBase):
    # Allow setting state on creation, default to NEW if not provided
    lifecycle_state: LifecycleStateEnum = Field(LifecycleStateEnum.NEW, description="Initial lifecycle state")
    pass # All fields from AgentBase are required or have defaults

# Properties to receive via API on update (all optional)
class AgentUpdate(BaseModel):
    type: Optional[str] = None
    version: Optional[str] = None
    owner: Optional[str] = None
    maintainer: Optional[str] = None
    lifecycle_state: Optional[LifecycleStateEnum] = None

    class Config:
        use_enum_values = True

# Properties shared by models stored in DB
class AgentInDBBase(AgentBase):
    unique_id: UUID
    creation_timestamp: datetime

    class Config:
        from_attributes = True # Pydantic V2 way to enable ORM mode

# Properties to return to client
class Agent(AgentInDBBase):
    pass # Include all fields from AgentInDBBase

# Additional properties stored in DB
class AgentInDB(AgentInDBBase):
    pass # Same as Agent for now

# Schema for paginated list response
class AgentListResponse(BaseModel):
    items: List[Agent]
    total: int
    # Consider adding limit, offset/page, next/prev info if needed

# Schema for updating only the lifecycle state
class AgentStateUpdate(BaseModel):
    lifecycle_state: LifecycleStateEnum 