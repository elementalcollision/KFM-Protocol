from typing import Dict, List, Optional
from pydantic import Field, BaseModel

from .base import RequestData, ResponseData


class AgentListRequest(RequestData):
    """
    Request to list all agents, with optional filtering parameters.
    """
    payload: Dict = Field(
        default={},
        description="Optional filtering parameters",
        example={"status": "active"}
    )


class AgentDetail(BaseModel):
    """
    Agent details structure.
    """
    id: str = Field(..., description="Unique agent identifier", example="agent-123")
    name: str = Field(..., description="Agent name", example="Test Agent")
    status: str = Field(..., description="Agent status", example="active")
    # Add more fields as needed


class AgentListResponse(ResponseData):
    """
    Response containing a list of agents and metadata.
    """
    payload: Dict[str, List[AgentDetail]] = Field(
        ...,
        description="Dictionary containing 'agents' list and metadata",
        example={"agents": [{"id": "agent-123", "name": "Test Agent", "status": "active"}]}
    )


class AgentStateRequest(RequestData):
    """
    Request to get or update an agent's state.
    """
    payload: Dict = Field(
        ...,
        description="Agent state data or query parameters",
        example={"state": "idle"}
    )


class AgentStateResponse(ResponseData):
    """
    Response containing an agent's state.
    """
    payload: Dict = Field(
        ...,
        description="Agent state information",
        example={"state": "idle", "last_updated": "2024-06-01T12:00:00Z"}
    ) 