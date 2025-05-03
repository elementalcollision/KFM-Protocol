from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AgentIdentifier(BaseModel):
    """Schema for identifying a single agent."""
    agent_id: str = Field(..., description="Unique identifier of the agent.")

class AgentOperationRequest(BaseModel):
    """Schema for requests involving operations on multiple agents."""
    agent_ids: List[str] = Field(..., description="List of unique identifiers for the agents to operate on.", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context or reason for the operation.")

class OperationStatus(BaseModel):
    """Schema for reporting the status of an operation on a single agent."""
    agent_id: str
    success: bool
    message: Optional[str] = None

class BatchOperationResponse(BaseModel):
    """Schema for the response of a batch operation on agents."""
    results: List[OperationStatus] = Field(..., description="List of results for each agent processed.")

# Example usage (optional, for clarity):
# Request to deprecate agents 'agent-123' and 'agent-456'
# req = AgentOperationRequest(agent_ids=['agent-123', 'agent-456'], context={'reason': 'Superseded by new version'})

# Response indicating success for agent-123 and failure for agent-456
# resp = BatchOperationResponse(results=[
#     OperationStatus(agent_id='agent-123', success=True, message='State transitioned to DEPRECATED'),
#     OperationStatus(agent_id='agent-456', success=False, message='Agent not found or invalid state')
# ]) 