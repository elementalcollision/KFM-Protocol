from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional
import logging

# Assuming imports - adjust as needed
from m_operator_service.app.db.session import get_db
from m_operator_service.app.schemas.maintenance import (
    MaintenanceReviewCreate, MaintenanceReviewUpdate, MaintenanceReviewResponse
)
from m_operator_service.app.models.enums import ReviewStatus, ReviewType, ReviewOutcome
from m_operator_service.app.services import maintenance_service
# Placeholder for user dependency
# from m_operator_service.app.security import get_current_active_user, User 

logger = logging.getLogger(__name__)
router = APIRouter()

# Placeholder User model
class User:
    id: UUID = UUID('00000000-0000-0000-0000-000000000000') 
async def get_current_active_user() -> User:
    return User()

@router.post("/reviews", response_model=MaintenanceReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance_review(
    review_in: MaintenanceReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user) # Add permission check later
):
    """(Manually) Create a new maintenance review."""
    logger.info(f"Manually creating maintenance review for agent {review_in.agent_id}")
    review = await maintenance_service.create_manual_review(db, review_in=review_in)
    if not review:
        # This case depends on CRUD implementation, but good practice
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create review")
    return review

@router.get("/reviews/{review_id}", response_model=MaintenanceReviewResponse)
async def get_maintenance_review(
    review_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get details of a specific maintenance review."""
    logger.info(f"Getting maintenance review {review_id}")
    review = await maintenance_service.get_review(db, review_id=review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance review not found")
    return review

@router.put("/reviews/{review_id}/complete", response_model=MaintenanceReviewResponse)
async def complete_maintenance_review(
    review_id: UUID = Path(...),
    outcome: ReviewOutcome = Query(...),
    notes: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user) # Add permission check later
):
    """Mark a maintenance review as complete."""
    logger.info(f"Completing maintenance review {review_id} with outcome {outcome}")
    # Check if review exists first (optional, service might do it)
    # existing_review = await maintenance_service.get_review(db, review_id)
    # if not existing_review:
    #    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    # if existing_review['status'] == ReviewStatus.COMPLETED:
    #    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review already completed")
        
    updated_review = await maintenance_service.complete_review(
        db, review_id=review_id, outcome=outcome, notes=notes
    )
    if not updated_review:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance review not found or could not be completed")
    return updated_review

@router.get("/agents/{agent_id}/reviews", response_model=List[MaintenanceReviewResponse])
async def list_agent_maintenance_reviews(
    agent_id: UUID = Path(...),
    status: Optional[ReviewStatus] = Query(None, description="Filter by review status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all maintenance reviews for a specific agent."""
    logger.info(f"Listing maintenance reviews for agent {agent_id}, status: {status}")
    reviews = await maintenance_service.get_reviews_by_agent_id(db, agent_id=agent_id, status=status)
    return reviews 