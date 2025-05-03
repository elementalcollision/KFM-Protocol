from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional

from m_operator_service.app.models.promotion import PromotionReview, PromotionApproval
from m_operator_service.app.schemas.promotion import (
    PromotionReviewCreate, PromotionReviewUpdate, 
    PromotionApprovalCreate, PromotionApprovalUpdate
)

# --- PromotionReview CRUD ---

async def get_promotion_review(db: AsyncSession, review_id: UUID) -> Optional[PromotionReview]:
    """Get a single promotion review by ID, loading approvals."""
    stmt = select(PromotionReview).options(selectinload(PromotionReview.approvals)).where(PromotionReview.id == review_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def create_promotion_review(db: AsyncSession, obj_in: PromotionReviewCreate) -> PromotionReview:
    """Create a new promotion review."""
    db_obj = PromotionReview(**obj_in.dict())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_promotion_review(db: AsyncSession, db_obj: PromotionReview, obj_in: PromotionReviewUpdate) -> PromotionReview:
    """Update an existing promotion review."""
    update_data = obj_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

# --- PromotionApproval CRUD ---

async def create_approval(db: AsyncSession, obj_in: PromotionApprovalCreate) -> PromotionApproval:
    """Create a new promotion approval record."""
    db_obj = PromotionApproval(**obj_in.dict())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_approvals_by_review(db: AsyncSession, review_id: UUID) -> List[PromotionApproval]:
    """Get all approval records for a specific review."""
    stmt = select(PromotionApproval).where(PromotionApproval.review_id == review_id).order_by(PromotionApproval.approval_order)
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_pending_approval(db: AsyncSession, review_id: UUID, stakeholder_id: UUID) -> Optional[PromotionApproval]:
    """Get a specific pending approval record for a stakeholder and review."""
    stmt = select(PromotionApproval).where(
        PromotionApproval.review_id == review_id,
        PromotionApproval.stakeholder_id == stakeholder_id,
        PromotionApproval.status == 'PENDING' # Assuming PENDING enum value
    )
    result = await db.execute(stmt)
    return result.scalars().first()

async def update_approval_status(db: AsyncSession, db_obj: PromotionApproval, obj_in: PromotionApprovalUpdate) -> PromotionApproval:
    """Update the status and notes of an approval record."""
    update_data = obj_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    # Explicitly set responded_at when status changes from PENDING
    if db_obj.status != 'PENDING' and 'status' in update_data and update_data['status'] != 'PENDING':
        from datetime import datetime, timezone
        setattr(db_obj, 'responded_at', datetime.now(timezone.utc))
        
    await db.commit()
    await db.refresh(db_obj)
    return db_obj 