from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID

class AdaptationRequest(BaseModel):
    """Schema for requesting an adaptation operation."""
    type: str = Field(..., description="Type of adaptation requested (e.g., 'code_refactor', 'model_finetune', 'feature_toggle')")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Specific parameters for the adaptation type")
    triggering_entity_id: Optional[UUID] = Field(None, description="Optional ID of the entity triggering the adaptation")
    justification: Optional[str] = Field(None, description="Reason or goal for the adaptation")

class AdaptationResponse(BaseModel):
    """Schema for the response after initiating an adaptation."""
    agent_id: UUID
    adaptation_id: UUID = Field(..., description="Unique ID for tracking this specific adaptation task/operation")
    status: str = Field(default="PENDING", description="Initial status of the adaptation task (e.g., PENDING, RUNNING, COMPLETED, FAILED)")
    message: Optional[str] = None 