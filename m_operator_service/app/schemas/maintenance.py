from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime, date
from typing import Optional

from m_operator_service.app.models.enums import ReviewStatus, ReviewType, ReviewOutcome

class MaintenanceReviewBase(BaseModel):
    agent_id: UUID
    review_type: ReviewType = ReviewType.PERIODIC
    scheduled_date: Optional[date] = None # Often set by service
    due_date: Optional[date] = None       # Often set by service
    notes: Optional[str] = None

class MaintenanceReviewCreate(MaintenanceReviewBase):
    # Allow optional manual setting, but usually service sets these
    pass 

class MaintenanceReviewUpdate(BaseModel):
    status: Optional[ReviewStatus] = None
    completed_date: Optional[datetime] = None
    outcome: Optional[ReviewOutcome] = None
    notes: Optional[str] = None
    next_review_date: Optional[date] = None

class MaintenanceReviewInDBBase(MaintenanceReviewBase):
    id: UUID
    status: ReviewStatus
    scheduled_date: datetime
    due_date: datetime
    completed_date: Optional[datetime] = None
    outcome: Optional[ReviewOutcome] = None
    next_review_date: Optional[datetime] = None
    created_at: datetime # Assuming model has this
    updated_at: Optional[datetime] = None # Assuming model has this

    class Config:
        orm_mode = True # Pydantic v1, use from_attributes = True for v2

class MaintenanceReviewResponse(MaintenanceReviewInDBBase):
    pass 