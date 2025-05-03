from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from datetime import datetime
from uuid import UUID

# Replicate Enum from models or define separately
class ExperimentStatusEnum(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExperimentVariant(BaseModel):
    name: str = Field(..., description="Name of the variant (e.g., 'control', 'treatmentA')")
    description: Optional[str] = Field(None, description="Description of the variant")
    weight: float = Field(..., ge=0, le=1, description="Percentage of traffic allocated (0.0-1.0)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Variant-specific parameters")


class SuccessCriterion(BaseModel):
    metric: str = Field(..., description="Name of the metric to track")
    direction: Literal["increase", "decrease"] = Field(..., description="Desired direction of change")
    threshold: float = Field(..., description="Minimum relative change required for success")
    minimum_sample_size: Optional[int] = Field(None, description="Minimum observations needed before evaluation")


class ExperimentAudience(BaseModel):
    percentage: Optional[float] = Field(None, ge=0, le=100, description="Overall percentage of traffic (0-100)")
    user_segments: Optional[List[str]] = Field(None, description="List of user segment identifiers to include")
    environments: Optional[List[str]] = Field(None, description="List of environment names to include")


# Schema for creating an experiment
class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Unique name for the experiment")
    description: Optional[str] = Field(None, max_length=500)
    feature_flag: str = Field(..., description="Associated feature flag name")
    variants: List[ExperimentVariant] = Field(..., min_items=2, description="List of variants (control + treatment(s))")
    success_criteria: List[SuccessCriterion] = Field(..., min_items=1, description="Criteria for determining success")
    audience: Optional[ExperimentAudience] = Field(None, description="Targeting rules for the experiment")
    duration_days: Optional[int] = Field(14, gt=0, description="Default experiment duration in days")


# Schema for updating an experiment (mostly configurations)
class ExperimentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    feature_flag: Optional[str] = None
    variants: Optional[List[ExperimentVariant]] = Field(None, min_items=2)
    success_criteria: Optional[List[SuccessCriterion]] = Field(None, min_items=1)
    audience: Optional[ExperimentAudience] = None
    duration_days: Optional[int] = Field(None, gt=0)


# Schema for the full Experiment object returned by API
class ExperimentResponse(ExperimentCreate):
    id: int
    status: ExperimentStatusEnum
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    results: Optional[Dict[str, Any]] = None # Analysis results
    conclusion: Optional[str] = None # Final outcome

    class Config:
        orm_mode = True
        use_enum_values = True


# Schema for starting/stopping/pausing
class ExperimentActionRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for the action")


# Schema for concluding an experiment
class ExperimentConcludeRequest(BaseModel):
    success: Optional[bool] = Field(None, description="Manual override for success/failure determination")
    reason: str = Field(..., description="Reason for concluding the experiment") 