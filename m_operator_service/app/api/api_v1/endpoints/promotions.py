from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
import logging

from m_operator_service.app.db.session import get_db
from m_operator_service.app.schemas.promotion import (
    PromotionApprovalResponse, PromotionApprovalUpdate, PromotionReviewResponse
)
from m_operator_service.app.services import promotion_service
# Placeholder for user dependency and permissions
# from m_operator_service.app.security import get_current_stakeholder, User

logger = logging.getLogger(__name__)
router = APIRouter()

# Placeholder User model for dependency signature
class User:
    id: UUID = UUID('00000000-0000-0000-0000-000000000000')

async def get_current_stakeholder() -> User:
    # Replace with actual dependency fetching user from token
    # and verifying stakeholder permissions
    return User()

@router.get("/reviews/{review_id}/approvals", response_model=List[PromotionApprovalResponse])
async def list_promotion_approvals(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_stakeholder) # Uncomment when ready
):
    """List all approval requests for a specific promotion review."""
    logger.info(f"Listing approvals for review {review_id}")
    approvals = await crud.promotion.get_approvals_by_review(db, review_id=review_id)
    return approvals

@router.post("/reviews/{review_id}/approvals", response_model=PromotionReviewResponse)
async def submit_promotion_approval(
    review_id: UUID,
    approval_in: PromotionApprovalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_stakeholder)
):
    """
    Submit an approval (approve/reject) for the current stakeholder.
    Updates the specific approval record and potentially the overall review status.
    """
    stakeholder_id = current_user.id # Get stakeholder ID from authenticated user
    logger.info(f"Submitting approval for review {review_id} by stakeholder {stakeholder_id}: Status={approval_in.status}")
    
    updated_review = await promotion_service.submit_approval(
        review_id=review_id, 
        stakeholder_id=stakeholder_id, 
        status=approval_in.status,
        notes=approval_in.notes,
        db=db
    )

    if updated_review is None:
         # This case happens if get_pending_approval returns None in the service
        logger.warning(f"No pending approval found or error during submission for review {review_id}, stakeholder {stakeholder_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No pending approval found for this stakeholder on this review."
        )

    logger.info(f"Approval submitted successfully for review {review_id}. Current review status: {updated_review.current_status}")
    # Need to fetch approvals again to populate the response model correctly
    full_review = await crud.promotion.get_promotion_review(db, review_id)
    return full_review

# --- Add Endpoints for initiating reviews (moved from agent_registry?) ---
# Example:
# @router.post("/reviews", response_model=PromotionReviewResponse, status_code=status.HTTP_201_CREATED)
# async def initiate_promotion_review(...):
#     # 1. Create the PromotionReview record using CRUD
#     # 2. Call promotion_service.initiate_promotion_review_workflow(new_review.id, db)
#     pass 