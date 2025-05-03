import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, HttpUrl

# Import criteria fields from agent_registry_entry or redefine if needed
from .agent_registry_entry import AgentState, CapabilityMatchType 

# Criteria used for filtering which agent changes trigger notification
# Similar to DiscoveryCriteria, but might be slightly different (e.g., no pagination/sorting)
class SubscriptionCriteria(BaseModel):
    type: Optional[str] = Field(None, description="Filter by agent type (exact match)")
    state: Optional[AgentState] = Field(None, description="Filter by exact agent state")
    capabilities: Optional[List[str]] = Field(None, description="List of capabilities to filter by")
    capability_match_type: CapabilityMatchType = Field(CapabilityMatchType.EXACT, description="How to match capabilities")
    metadata_filters: Optional[Dict[str, Any]] = Field(None, description="Filter by exact key-value pairs in metadata")
    # Removed: include_states, pagination, sort_by - these don't apply to event matching

    class Config:
        use_enum_values = True

# Base schema for subscription properties
class SubscriptionBase(BaseModel):
    subscriber_url: HttpUrl = Field(..., description="Webhook URL for sending notifications")
    criteria: SubscriptionCriteria = Field(..., description="Criteria for triggering notifications")
    is_active: bool = Field(True, description="Whether the subscription is currently active")

# Schema for creating a new subscription
class SubscriptionCreate(SubscriptionBase):
    pass # Inherits all from base

# Schema for updating an existing subscription
class SubscriptionUpdate(BaseModel):
    subscriber_url: Optional[HttpUrl] = None
    criteria: Optional[SubscriptionCriteria] = None
    is_active: Optional[bool] = None

# Schema for representing a subscription returned by the API
class SubscriptionResponse(SubscriptionBase):
    id: uuid.UUID
    last_notified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True 