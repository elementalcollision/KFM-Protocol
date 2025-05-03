from fastapi import APIRouter, Depends, HTTPException, status, Path
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from f_operator_service.db.session import get_db
from f_operator_service.schemas.promotion import (
    PromotionInitiateRequest, PromotionReviewResponse, EvidenceSubmissionRequest, PromotionChecklistItemResponse, ChecklistItemStatusUpdate
)
# Provenance imports
from f_operator_service.app.services.provenance_service import get_provenance_service
from f_operator_service.schemas.provenance import ProvenanceRecordCreate

router = APIRouter()

@router.post("/agents/{agent_id}/promote", response_model=PromotionReviewResponse, status_code=status.HTTP_201_CREATED)
async def initiate_promotion_review(
    agent_id: UUID,
    request: PromotionInitiateRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # TODO: Add auth
):
    """
    Initiate a promotion review for the specified agent.
    """
    try:
        from f_operator_service.models.promotion import PromotionReview, PromotionStatus, AgentLevel, PromotionChecklistItem, ChecklistItemStatus
        import uuid
        from datetime import datetime

        # Create PromotionReview
        review = PromotionReview(
            agent_id=agent_id,
            requested_level=request.requested_level,
            current_status=PromotionStatus.INITIATED,
            initiator_id=request.initiator_id,
            reason=request.reason,
        )
        db.add(review)
        await db.flush()  # Get review.id before commit

        # Generate checklist items (hardcoded template for now)
        checklist_templates = [
            {"description": "All required documentation submitted.", "required": True},
            {"description": "Peer review completed.", "required": True}
        ]
        checklist_items = []
        for template in checklist_templates:
            item = PromotionChecklistItem(
                review_id=review.id,
                description=template["description"],
                required=template["required"],
                status=ChecklistItemStatus.PENDING,
                evidence_submitted=False
            )
            db.add(item)
            checklist_items.append(item)
        await db.commit()
        await db.refresh(review)
        for item in checklist_items:
            await db.refresh(item)

        # Provenance logging
        provenance_service = get_provenance_service()
        try:
            prov_record = ProvenanceRecordCreate(
                entity_id=agent_id,
                operation_type="promotion_review_initiated",
                operation_id=review.id,
                user_id=request.initiator_id,
                parent_entity_id=None,
                parameters=request.model_dump(),
                outcome_status="success",
                outcome_details=None,
                approval_status=None,
                approver_id=None,
                approval_timestamp=None,
                approval_notes=None
            )
            await provenance_service.create_provenance_record(db, prov_record)
        except Exception as prov_err:
            import logging
            logging.getLogger(__name__).error(f"Failed to log provenance for promotion review: {prov_err}")

        return PromotionReviewResponse(
            review_id=review.id,
            agent_id=review.agent_id,
            current_status=review.current_status.value,
            created_at=review.created_at or datetime.utcnow(),
            checklist_items=[PromotionChecklistItemResponse(
                id=item.id,
                review_id=item.review_id,
                criteria_id=item.criteria_id,
                description=item.description,
                required=item.required,
                status=item.status.value,
                evidence_submitted=item.evidence_submitted,
                created_at=item.created_at,
                updated_at=item.updated_at
            ) for item in checklist_items]
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to initiate promotion review: {e}")

@router.post("/promotion-reviews/{review_id}/evidence", status_code=status.HTTP_201_CREATED)
async def submit_evidence(
    review_id: UUID,
    request: EvidenceSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # TODO: Add auth
):
    """
    Submit evidence for a specific promotion review criteria.
    """
    try:
        from f_operator_service.models.promotion import PromotionEvidence, EvidenceType, PromotionChecklistItem, ChecklistItemStatus
        from f_operator_service.schemas.promotion import PromotionChecklistItemResponse
        import json
        from datetime import datetime
        from sqlalchemy.future import select

        # TODO: Validate review exists (stub for now)
        # Example: review = await get_review_or_404(review_id, db)
        # For now, assume review exists

        # Store PromotionEvidence
        evidence = PromotionEvidence(
            review_id=review_id,
            criteria_id=request.criteria_id,
            evidence_type=EvidenceType(request.evidence_type),
            description=request.description,
            attachments=json.dumps([a.model_dump() for a in request.attachments]) if request.attachments else None,
            submitted_by=request.submitted_by,
            # submitted_at is auto-set
        )
        db.add(evidence)

        # Update checklist item
        checklist_result = await db.execute(
            select(PromotionChecklistItem).where(
                PromotionChecklistItem.review_id == review_id,
                PromotionChecklistItem.criteria_id == request.criteria_id
            )
        )
        checklist_item = checklist_result.scalar_one_or_none()
        if not checklist_item:
            await db.rollback()
            raise HTTPException(status_code=404, detail="Checklist item not found for this criteria")
        checklist_item.evidence_submitted = True
        checklist_item.status = ChecklistItemStatus.IN_REVIEW
        checklist_item.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(evidence)
        await db.refresh(checklist_item)

        # Provenance logging
        provenance_service = get_provenance_service()
        try:
            prov_record = ProvenanceRecordCreate(
                entity_id=review_id,  # The review is the entity for evidence
                operation_type="promotion_evidence_submitted",
                operation_id=evidence.id,
                user_id=request.submitted_by,
                parent_entity_id=None,
                parameters=request.model_dump(),
                outcome_status="success",
                outcome_details=None,
                approval_status=None,
                approver_id=None,
                approval_timestamp=None,
                approval_notes=None
            )
            await provenance_service.create_provenance_record(db, prov_record)
        except Exception as prov_err:
            import logging
            logging.getLogger(__name__).error(f"Failed to log provenance for evidence submission: {prov_err}")

        return PromotionChecklistItemResponse(
            id=checklist_item.id,
            review_id=checklist_item.review_id,
            criteria_id=checklist_item.criteria_id,
            description=checklist_item.description,
            required=checklist_item.required,
            status=checklist_item.status.value,
            evidence_submitted=checklist_item.evidence_submitted,
            created_at=checklist_item.created_at,
            updated_at=checklist_item.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit evidence: {e}")

@router.get("/promotion-reviews/{review_id}", response_model=PromotionReviewResponse)
async def get_promotion_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch the status and details of a promotion review.
    """
    try:
        from f_operator_service.models.promotion import PromotionReview, PromotionEvidence, PromotionChecklistItem
        from sqlalchemy.future import select
        import uuid
        from datetime import datetime

        # Fetch PromotionReview
        result = await db.execute(select(PromotionReview).where(PromotionReview.id == review_id))
        review = result.scalar_one_or_none()
        if not review:
            raise HTTPException(status_code=404, detail="Promotion review not found")

        # Fetch related checklist items
        checklist_result = await db.execute(select(PromotionChecklistItem).where(PromotionChecklistItem.review_id == review_id))
        checklist_items = checklist_result.scalars().all()

        return PromotionReviewResponse(
            review_id=review.id,
            agent_id=review.agent_id,
            current_status=review.current_status.value,
            created_at=review.created_at or datetime.utcnow(),
            checklist_items=[PromotionChecklistItemResponse(
                id=item.id,
                review_id=item.review_id,
                criteria_id=item.criteria_id,
                description=item.description,
                required=item.required,
                status=item.status.value,
                evidence_submitted=item.evidence_submitted,
                created_at=item.created_at,
                updated_at=item.updated_at
            ) for item in checklist_items]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch promotion review: {e}")

@router.patch("/promotion-reviews/{review_id}/checklist/{item_id}/status", response_model=PromotionChecklistItemResponse)
async def update_checklist_item_status(
    review_id: UUID,
    item_id: UUID,
    status_update: ChecklistItemStatusUpdate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # TODO: Add auth
):
    """
    Update the status of a specific checklist item for a promotion review.
    """
    try:
        from f_operator_service.models.promotion import PromotionChecklistItem, ChecklistItemStatus
        from datetime import datetime
        from sqlalchemy.future import select

        result = await db.execute(
            select(PromotionChecklistItem).where(
                PromotionChecklistItem.id == item_id,
                PromotionChecklistItem.review_id == review_id
            )
        )
        checklist_item = result.scalar_one_or_none()
        if not checklist_item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        checklist_item.status = status_update.status
        checklist_item.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(checklist_item)
        return PromotionChecklistItemResponse(
            id=checklist_item.id,
            review_id=checklist_item.review_id,
            criteria_id=checklist_item.criteria_id,
            description=checklist_item.description,
            required=checklist_item.required,
            status=checklist_item.status.value,
            evidence_submitted=checklist_item.evidence_submitted,
            created_at=checklist_item.created_at,
            updated_at=checklist_item.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update checklist item status: {e}") 