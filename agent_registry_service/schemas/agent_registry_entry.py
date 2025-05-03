import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

from pydantic import BaseModel, Field

# Replicate Enum here or import from models if preferred and safe
# Keeping it separate can avoid circular dependencies
class AgentState(str, Enum):
    STABLE = "STABLE"
    EXPERIMENTAL = "EXPERIMENTAL"
    # Ensure this matches the Enum in models


# Base properties shared by all related schemas
class AgentRegistryEntryBase(BaseModel):
    type: str = Field(..., description="Type or category of the agent")
    state: AgentState = Field(AgentState.EXPERIMENTAL, description="Current state of the agent")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities the agent possesses")
    metadata_: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="metadata", description="Arbitrary key-value metadata associated with the agent")

    class Config:
        orm_mode = True # Compatibility with ORM model
        use_enum_values = True # Use enum values in serialization
        allow_population_by_field_name = True # Allow using 'metadata' instead of 'metadata_' when creating


# Properties required for creating a new entry
class AgentCreateSchema(AgentRegistryEntryBase):
    pass # Inherits all fields from base


# Properties required for updating an existing entry (all optional)
class AgentUpdateSchema(BaseModel):
    type: Optional[str] = None
    state: Optional[AgentState] = None
    capabilities: Optional[List[str]] = None
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")

    class Config:
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True


# Properties returned by the API (includes ID and timestamps)
class AgentRegistryEntry(AgentRegistryEntryBase):
    id: uuid.UUID = Field(..., description="Unique identifier for the agent entry")
    created_at: datetime = Field(..., description="Timestamp when the entry was created")
    updated_at: datetime = Field(..., description="Timestamp when the entry was last updated")

    class Config:
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True


# --- Schemas for Discovery Endpoint --- 

class DiscoverySortOptions(str, Enum):
    CREATED_AT_ASC = "created_at_asc"
    CREATED_AT_DESC = "created_at_desc"
    UPDATED_AT_ASC = "updated_at_asc"
    UPDATED_AT_DESC = "updated_at_desc"
    TYPE_ASC = "type_asc"
    TYPE_DESC = "type_desc"
    # Add other sortable fields as needed

class CapabilityMatchType(str, Enum):
    EXACT = "exact" # Agent must have all listed capabilities
    ANY = "any"   # Agent must have at least one of the listed capabilities
    # FUZZY = "fuzzy" # Placeholder for potential fuzzy matching enhancement

class DiscoveryPagination(BaseModel):
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")

class DiscoveryCriteria(BaseModel):
    type: Optional[str] = Field(None, description="Filter by agent type (exact match)")
    state: Optional[AgentState] = Field(None, description="Filter by exact agent state")
    capabilities: Optional[List[str]] = Field(None, description="List of capabilities to filter by")
    capability_match_type: CapabilityMatchType = Field(CapabilityMatchType.EXACT, description="How to match capabilities (exact means all must match)")
    metadata_filters: Optional[Dict[str, Any]] = Field(None, description="Filter by exact key-value pairs in metadata")
    include_states: Optional[List[AgentState]] = Field(None, description="Override default states (STABLE, EXPERIMENTAL) to include specific states")
    pagination: DiscoveryPagination = Field(default_factory=DiscoveryPagination)
    sort_by: Optional[DiscoverySortOptions] = Field(DiscoverySortOptions.CREATED_AT_DESC, description="Field and direction to sort results by")

    class Config:
        use_enum_values = True

class PaginatedAgentResponse(BaseModel):
    items: List[AgentRegistryEntry]
    total: int
    limit: int
    skip: int 