from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

from m_operator_service.app.models.enums import ApprovalStatus, PromotionStatus # Assuming enums are here

# --- Approval Schemas ---

class PromotionApprovalBase(BaseModel):
    review_id: UUID
    stakeholder_id: UUID
    role: str
    notes: Optional[str] = None

class PromotionApprovalCreate(PromotionApprovalBase):
    pass

class PromotionApprovalUpdate(BaseModel):
    status: ApprovalStatus
    notes: Optional[str] = None

class PromotionApprovalInDBBase(PromotionApprovalBase):
    id: UUID
    status: ApprovalStatus
    requested_at: datetime
    responded_at: Optional[datetime] = None

    class Config:
        orm_mode = True # Pydantic v1, use from_attributes = True for v2

class PromotionApprovalResponse(PromotionApprovalInDBBase):
    pass

# --- Review Schemas (Might need additions) ---
# Assuming a basic Review schema exists or needs creation

class PromotionReviewBase(BaseModel):
    agent_id: UUID
    requested_level: str # Placeholder
    initiator_id: UUID
    workflow_type: Optional[str] = "default"

class PromotionReviewCreate(PromotionReviewBase):
    pass

class PromotionReviewUpdate(BaseModel):
    current_status: Optional[PromotionStatus] = None
    rejection_reason: Optional[str] = None

class PromotionReviewInDBBase(PromotionReviewBase):
    id: UUID
    current_status: PromotionStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    class Config:
        orm_mode = True # Pydantic v1, use from_attributes = True for v2

class PromotionReviewResponse(PromotionReviewInDBBase):
    approvals: List[PromotionApprovalResponse] = [] # Include approvals in response 