from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class AgentLevel(str, Enum):
    EXPERIMENTAL = "EXPERIMENTAL"
    CANDIDATE = "CANDIDATE"
    STABLE = "STABLE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"

class PromotionStatus(str, Enum):
    INITIATED = "INITIATED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"

class EvidenceType(str, Enum):
    DOCUMENT = "DOCUMENT"
    LINK = "LINK"
    NOTE = "NOTE"
    OTHER = "OTHER"

class AttachmentReference(BaseModel):
    url: str
    filename: Optional[str] = None
    content_type: Optional[str] = None

class ChecklistItemStatus(str, Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    WAIVED = "WAIVED"

class PromotionChecklistItemCreate(BaseModel):
    description: str
    required: bool = True
    criteria_id: Optional[UUID] = None

class PromotionChecklistItemResponse(BaseModel):
    id: UUID
    review_id: UUID
    criteria_id: Optional[UUID] = None
    description: str
    required: bool
    status: ChecklistItemStatus
    evidence_submitted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

class PromotionInitiateRequest(BaseModel):
    reason: str
    requested_level: AgentLevel
    initiator_id: UUID

class PromotionReviewResponse(BaseModel):
    review_id: UUID
    agent_id: UUID
    current_status: PromotionStatus
    created_at: datetime
    checklist_items: List[PromotionChecklistItemResponse]

class EvidenceSubmissionRequest(BaseModel):
    criteria_id: UUID
    evidence_type: EvidenceType
    description: str
    attachments: Optional[List[AttachmentReference]] = None
    submitted_by: UUID

class ChecklistItemStatusUpdate(BaseModel):
    status: ChecklistItemStatus
    notes: Optional[str] = None 