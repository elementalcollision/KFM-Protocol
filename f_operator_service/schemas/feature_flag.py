from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

class TargetingRule(BaseModel):
    type: Literal["percentage", "agent_ids", "environment"] # Add more as needed
    value: Any

class FeatureFlagBase(BaseModel):
    name: str = Field(..., description="Unique name of the feature flag")
    description: Optional[str] = None
    is_active: bool = Field(False, description="Default state of the flag")
    # Add targeting rules schema if needed

class FeatureFlagCreate(FeatureFlagBase):
    pass

class FeatureFlagUpdate(BaseModel):
    description: Optional[str] = None
    is_active: Optional[bool] = None
    # Add targeting rules update schema if needed

class FeatureFlagResponse(FeatureFlagBase):
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class FeatureFlag(BaseModel):
    name: str = Field(..., description="Unique name for the feature flag")
    description: Optional[str] = None
    is_active: bool = Field(default=False, description="Whether the flag is globally active")
    rules: List[TargetingRule] = Field(default_factory=list, description="Optional targeting rules")

# Schema for evaluation context passed to is_flag_active
class FeatureFlagEvaluationContext(BaseModel):
    user_id: Optional[str] = None
    environment: Optional[str] = None
    # Add other relevant context attributes like tenant_id, session_id, etc.
    custom_attributes: Optional[Dict[str, Any]] = None

# Schema for the response from the evaluation endpoint (if created)
class FeatureFlagEvaluationResponse(BaseModel):
    flag_name: str
    is_active: bool
    variant: Optional[str] = None # For multivariate flags
    reason: Optional[str] = None # Explanation of why flag is active/inactive 