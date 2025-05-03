from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Dict, Optional
import logging
import httpx # Added

from m_operator_service.app import crud
from m_operator_service.app.models.promotion import PromotionReview
from m_operator_service.app.models.enums import ApprovalStatus, PromotionStatus # Adjusted import
from m_operator_service.app.schemas.promotion import PromotionApprovalCreate, PromotionApprovalUpdate
from m_operator_service.app.core.config import settings # For workflow config & URLs

logger = logging.getLogger(__name__)

async def initiate_promotion_review_workflow(review_id: UUID, db: AsyncSession):
    """Starts the approval workflow for a given review."""
    review = await crud.promotion.get_promotion_review(db, review_id)
    if not review:
        logger.error(f"PromotionReview not found: {review_id}")
        return

    # Determine stakeholders based on workflow type
    stakeholder_ids_roles = _get_stakeholders_for_review(review)
    
    # Create pending approval records
    await assign_approvals(review_id, stakeholder_ids_roles, db)

    # Trigger notifications (Placeholder)
    await _notify_stakeholders(review_id, stakeholder_ids_roles, db)

async def assign_approvals(review_id: UUID, stakeholder_ids_roles: List[Dict[str, UUID | str]], db: AsyncSession):
    """Creates pending PromotionApproval records for the specified stakeholders."""
    for item in stakeholder_ids_roles:
        approval_in = PromotionApprovalCreate(
            review_id=review_id,
            stakeholder_id=item['id'],
            role=item['role']
        )
        await crud.promotion.create_approval(db, obj_in=approval_in)
        logger.info(f"Created pending approval for stakeholder {item['id']} (role: {item['role']}) on review {review_id}")

async def submit_approval(review_id: UUID, stakeholder_id: UUID, status: ApprovalStatus, notes: Optional[str], db: AsyncSession) -> Optional[PromotionReview]:
    """Processes a stakeholder's approval/rejection and updates review status."""
    # Find the pending approval
    pending_approval = await crud.promotion.get_pending_approval(db, review_id, stakeholder_id)
    if not pending_approval:
        logger.warning(f"No pending approval found for stakeholder {stakeholder_id} on review {review_id}")
        return None # Or raise HTTPException(404) in API layer

    # Update the approval record
    approval_update = PromotionApprovalUpdate(status=status, notes=notes)
    # TODO: Add ProvenanceContext/Audit log wrapper here
    updated_approval = await crud.promotion.update_approval_status(db, pending_approval, approval_update)
    logger.info(f"Approval status updated for stakeholder {stakeholder_id} on review {review_id} to {status}")

    # Check if the review is now complete (approved/rejected)
    review = await check_review_signoff_completion(review_id, db)
    return review

async def check_review_signoff_completion(review_id: UUID, db: AsyncSession) -> PromotionReview:
    """Checks if all required approvals are met and updates the review status."""
    review = await crud.promotion.get_promotion_review(db, review_id)
    if not review:
        raise ValueError(f"Review {review_id} not found during completion check.")

    # Already in a final state?
    if review.current_status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.CANCELLED]:
        return review

    all_approvals = await crud.promotion.get_approvals_by_review(db, review_id)
    workflow_config = _get_workflow_config(review.workflow_type)

    required_roles = [r['role'] for r in workflow_config['roles'] if r.get('required', True)]
    approved_roles = {a.role for a in all_approvals if a.status == ApprovalStatus.APPROVED}
    rejected_roles = {a.role for a in all_approvals if a.status == ApprovalStatus.REJECTED}

    # Check for rejection from a required role
    if any(role in rejected_roles for role in required_roles):
        rejection = next((a for a in all_approvals if a.role in required_roles and a.status == ApprovalStatus.REJECTED), None)
        reason = f"Rejected by {rejection.role}: {rejection.notes}" if rejection else "Rejected by required role"
        # TODO: Add ProvenanceContext/Audit log wrapper here
        await crud.promotion.update_promotion_review(db, review, {"current_status": ApprovalStatus.REJECTED, "rejection_reason": reason})
        logger.info(f"Promotion review {review_id} REJECTED.")
        return review

    # Check for approval threshold if defined
    if "threshold" in workflow_config:
        approved_count = len(approved_roles)
        if approved_count >= workflow_config["threshold"]:
             # TODO: Add ProvenanceContext/Audit log wrapper here
            await crud.promotion.update_promotion_review(db, review, {"current_status": ApprovalStatus.APPROVED})
            logger.info(f"Promotion review {review_id} APPROVED (threshold met).")
            await _trigger_promotion_actions(review, db) # Placeholder
            return review
    # Check if all required roles have approved
    elif all(role in approved_roles for role in required_roles):
         # TODO: Add ProvenanceContext/Audit log wrapper here
        await crud.promotion.update_promotion_review(db, review, {"current_status": ApprovalStatus.APPROVED})
        logger.info(f"Promotion review {review_id} APPROVED (all required roles)." )
        await _trigger_promotion_actions(review, db) # Placeholder
        return review

    # Otherwise, still pending
    return review

# --- Helper/Private Functions ---

def _get_stakeholders_for_review(review: PromotionReview) -> List[Dict[str, UUID | str]]:
    """Determines the required stakeholders based on config."""
    # Placeholder: Replace with logic to query user roles/groups based on review type/level
    # Example: Find users with specific roles (e.g., 'SECURITY_REVIEWER')
    workflow_config = _get_workflow_config(review.workflow_type)
    stakeholders = []
    for role_config in workflow_config.get('roles', []):
        # Replace with actual user lookup logic based on role
        placeholder_user_id = UUID('00000000-0000-0000-0000-000000000001') 
        stakeholders.append({"id": placeholder_user_id, "role": role_config['role']})
    logger.debug(f"Determined stakeholders for review {review.id}: {stakeholders}")
    return stakeholders

def _get_workflow_config(workflow_type: str) -> Dict:
    """Loads the approval workflow configuration."""
    # Access settings loaded from config/default-config.yaml
    config = settings.APPROVAL_WORKFLOWS.get(workflow_type, settings.APPROVAL_WORKFLOWS.get("default"))
    if not config:
        logger.error(f"Approval workflow config not found for type '{workflow_type}' or default.")
        return {"roles": []} # Return empty default
    return config

async def _notify_stakeholders(review_id: UUID, stakeholders: List[Dict], db: AsyncSession):
    """Placeholder for sending notifications (e.g., email, Slack)."""
    # Integrate with background task system (Celery, FastAPI BackgroundTasks)
    logger.info(f"Placeholder: Notifying stakeholders for review {review_id}: {stakeholders}")
    # Example: tasks.send_approval_request_notification.delay(review_id, [s['id'] for s in stakeholders])
    pass

async def _trigger_promotion_actions(review: PromotionReview, db: AsyncSession):
    """Triggers actions upon successful promotion: state update, etc."""
    agent_id = review.agent_id
    target_state = review.requested_level # Assuming this holds the target state like 'STABLE'
    logger.info(f"Triggering promotion actions for approved review {review.id} (agent: {agent_id}) to state: {target_state}")

    # 1. Call Agent Registry Service to update state
    registry_url = f"{settings.AGENT_REGISTRY_SERVICE_URL}/api/v1/agents/{agent_id}/state"
    state_update_payload = {"lifecycle_state": target_state}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(registry_url, json=state_update_payload)
            response.raise_for_status() # Raise exception for 4xx/5xx errors
            logger.info(f"Successfully updated agent {agent_id} state to {target_state} via Agent Registry.")
        except httpx.RequestError as e:
            logger.error(f"Error calling Agent Registry Service for agent {agent_id} state update: {e}")
            # TODO: Implement retry or compensation logic? Mark review as failed?
            # For now, just log the error. The review remains APPROVED locally.
            return # Stop further actions if state update fails
        except httpx.HTTPStatusError as e:
            logger.error(f"Agent Registry Service returned error for agent {agent_id} state update: {e.response.status_code} - {e.response.text}")
            # TODO: Handle specific errors (e.g., 404 Not Found, 400 Invalid State Transition)
            return

    # 2. Integrate Discovery Enablement (Placeholder)
    # If Discovery Service needs explicit notification:
    # discovery_url = f"{settings.DISCOVERY_SERVICE_URL}/api/v1/agents/{agent_id}/enable"
    # try: ... call discovery service ...
    logger.info(f"Placeholder: Ensuring agent {agent_id} is discoverable.")

    # 3. Integrate Resource Allocation (Placeholder)
    # If Resource Management Service needs explicit notification:
    # resource_url = f"{settings.RESOURCE_SERVICE_URL}/api/v1/agents/{agent_id}/allocate"
    # resource_payload = {"level": target_state, ...}
    # try: ... call resource service ...
    logger.info(f"Placeholder: Triggering resource allocation for agent {agent_id} at level {target_state}.")

    # TODO: Consider atomicity/rollback if subsequent steps fail after state change. 