import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_registry_service import crud, schemas
from agent_registry_service.db.session import get_db
# from agent_registry_service.api import deps # For security

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/", 
    response_model=schemas.SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Subscription",
    description="Create a new webhook subscription for agent registry events."
)
async def create_subscription(
    subscription_in: schemas.SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(deps.get_current_active_user) # Add auth
):
    logger.info(f"Creating subscription for URL: {subscription_in.subscriber_url}")
    try:
        # TODO: Add validation? E.g., check if URL is reachable?
        subscription = await crud.create_subscription(db=db, obj_in=subscription_in)
        return subscription
    except Exception as e:
        logger.error(f"Error creating subscription: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create subscription")

@router.get(
    "/",
    response_model=List[schemas.SubscriptionResponse], # TODO: Paginated response?
    summary="List Subscriptions",
    description="List all active subscriptions (requires admin privileges)."
)
async def list_subscriptions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(deps.get_current_active_superuser) # Admin only? 
):
    logger.info("Listing active subscriptions")
    try:
        # Fetch only active ones by default, maybe add filter?
        subscriptions = await crud.get_active_subscriptions(db=db, limit=limit) # Simple list for now
        # TODO: Implement proper pagination if needed
        return subscriptions
    except Exception as e:
        logger.error(f"Error listing subscriptions: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list subscriptions")

@router.get(
    "/{subscription_id}", 
    response_model=schemas.SubscriptionResponse,
    summary="Get Subscription Details",
    description="Get details of a specific subscription."
)
async def get_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(deps.get_current_active_user) # Auth: User should only get their own?
):
    logger.info(f"Getting subscription {subscription_id}")
    subscription = await crud.get_subscription(db, subscription_id=subscription_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    # TODO: Add authorization check - does current_user own this subscription?
    return subscription

@router.put(
    "/{subscription_id}", 
    response_model=schemas.SubscriptionResponse,
    summary="Update Subscription",
    description="Update an existing subscription's URL, criteria, or active status."
)
async def update_subscription(
    subscription_id: UUID,
    subscription_in: schemas.SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(deps.get_current_active_user) # Auth + Ownership check
):
    logger.info(f"Updating subscription {subscription_id}")
    db_subscription = await crud.get_subscription(db, subscription_id=subscription_id)
    if not db_subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    # TODO: Add authorization check
    try:
        updated_subscription = await crud.update_subscription(db=db, db_obj=db_subscription, obj_in=subscription_in)
        return updated_subscription
    except Exception as e:
        logger.error(f"Error updating subscription {subscription_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update subscription")


@router.delete(
    "/{subscription_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Subscription",
    description="Deletes an existing subscription."
)
async def delete_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(deps.get_current_active_user) # Auth + Ownership check
):
    logger.info(f"Deleting subscription {subscription_id}")
    db_subscription = await crud.get_subscription(db, subscription_id=subscription_id)
    if not db_subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    # TODO: Add authorization check
    try:
        await crud.delete_subscription(db=db, subscription_id=subscription_id)
        return None # Return No Content
    except Exception as e:
        logger.error(f"Error deleting subscription {subscription_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete subscription") 