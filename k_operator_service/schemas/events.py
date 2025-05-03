from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class EventMeta(BaseModel):
    """Metadata common to all events."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_service: str = "k-operator-service"

class AgentStateChangeEvent(BaseModel):
    """Base model for events related to agent state changes triggered by K-Operator."""
    meta: EventMeta
    agent_id: str
    triggering_user: Optional[str] = None # User ID if triggered by user action
    context: Optional[Dict[str, Any]] = None # Context provided in the K-Op request

class AgentDeprecatedEvent(AgentStateChangeEvent):
    """Event published when an agent is successfully deprecated."""
    meta: EventMeta = Field(default_factory=lambda: EventMeta(event_type="agent.deprecated"))
    new_state: str = "DEPRECATED"

class AgentArchivedEvent(AgentStateChangeEvent):
    """Event published when an agent is successfully archived."""
    meta: EventMeta = Field(default_factory=lambda: EventMeta(event_type="agent.archived"))
    new_state: str = "ARCHIVED"

class AgentDeletionRequestedEvent(AgentStateChangeEvent):
    """Event published when deletion of an agent is successfully requested/confirmed via K-Operator."""
    meta: EventMeta = Field(default_factory=lambda: EventMeta(event_type="agent.deletion.requested"))
    # Note: Actual deletion might happen asynchronously based on this event 