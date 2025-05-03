from pydantic import BaseModel, Field, conint
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

from .promotion import AgentLevel

class TemplateStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"

class CriteriaType(str, Enum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    OPTIONAL = "OPTIONAL"

class ChecklistCriteriaBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    criteria_type: CriteriaType = Field(default=CriteriaType.REQUIRED)
    order: conint(ge=0)  # Ensure order is non-negative
    evidence_required: bool = True

class ChecklistCriteriaCreate(ChecklistCriteriaBase):
    pass

class ChecklistCriteriaUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    criteria_type: Optional[CriteriaType] = None
    order: Optional[conint(ge=0)] = None
    evidence_required: Optional[bool] = None

class ChecklistCriteriaResponse(ChecklistCriteriaBase):
    id: UUID
    template_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ChecklistTemplateBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    target_level: AgentLevel
    version: conint(ge=1) = Field(default=1)  # Ensure version is at least 1
    status: TemplateStatus = Field(default=TemplateStatus.DRAFT)

class ChecklistTemplateCreate(ChecklistTemplateBase):
    criteria: List[ChecklistCriteriaCreate]

class ChecklistTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    target_level: Optional[AgentLevel] = None
    status: Optional[TemplateStatus] = None
    archived_at: Optional[datetime] = None

class ChecklistTemplateResponse(ChecklistTemplateBase):
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    criteria: List[ChecklistCriteriaResponse]

    class Config:
        from_attributes = True

# For bulk operations or list responses
class ChecklistTemplateListResponse(BaseModel):
    templates: List[ChecklistTemplateResponse]
    total: int 