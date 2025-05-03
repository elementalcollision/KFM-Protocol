from typing import Any, Dict, Optional, List
from uuid import UUID
import logging

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agent_registry_service.models.subscription import Subscription
from agent_registry_service.schemas.subscription import SubscriptionCreate, SubscriptionUpdate

logger = logging.getLogger(__name__)


async def get_subscription(db: AsyncSession, subscription_id: UUID) -> Optional[Subscription]:
    """Get a single subscription by ID."""
    logger.debug(f"Fetching subscription {subscription_id}")
    try:
        result = await db.execute(
            select(Subscription).filter(Subscription.id == subscription_id)
        )
        sub = result.scalars().first()
        if not sub:
            logger.debug(f"Subscription {subscription_id} not found.")
        return sub
    except Exception as e:
        logger.error(f"Error fetching subscription {subscription_id}: {e}", exc_info=True)
        raise

async def get_active_subscriptions(db: AsyncSession, limit: int = 1000) -> List[Subscription]:
    """Get all active subscriptions (with a limit to avoid loading too many)."""
    logger.debug(f"Fetching active subscriptions (limit={limit})")
    try:
        result = await db.execute(
            select(Subscription).filter(Subscription.is_active == True).limit(limit)
        )
        subs = list(result.scalars().all())
        logger.debug(f"Fetched {len(subs)} active subscriptions.")
        return subs
    except Exception as e:
        logger.error(f"Error fetching active subscriptions: {e}", exc_info=True)
        raise


async def create_subscription(db: AsyncSession, *, obj_in: SubscriptionCreate) -> Subscription:
    """Create a new subscription."""
    logger.info(f"Creating subscription for URL: {obj_in.subscriber_url}")
    try:
        # Pydantic v2 model_dump()
        db_obj = Subscription(**obj_in.model_dump())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.info(f"Subscription {db_obj.id} created successfully.")
        return db_obj
    except Exception as e:
        logger.error(f"Error creating subscription for {obj_in.subscriber_url}: {e}", exc_info=True)
        await db.rollback()
        raise


async def update_subscription(
    db: AsyncSession, *, db_obj: Subscription, obj_in: SubscriptionUpdate | Dict[str, Any]
) -> Subscription:
    """Update an existing subscription."""
    sub_id = db_obj.id
    logger.info(f"Updating subscription {sub_id}")
    try:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        if not update_data:
            logger.debug(f"No update data provided for subscription {sub_id}")
            return db_obj

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
            else:
                logger.warning(f"Attempted to update non-existent field '{field}' on subscription {sub_id}")

        # updated_at is handled by onupdate=func.now()
        db.add(db_obj) # Mark as dirty
        await db.commit()
        await db.refresh(db_obj)
        logger.info(f"Subscription {sub_id} updated successfully.")
        return db_obj
    except Exception as e:
        logger.error(f"Error updating subscription {sub_id}: {e}", exc_info=True)
        await db.rollback()
        raise


async def delete_subscription(db: AsyncSession, *, subscription_id: UUID) -> Optional[Subscription]:
    """Delete a subscription by ID."""
    logger.info(f"Deleting subscription {subscription_id}")
    try:
        db_obj = await get_subscription(db, subscription_id=subscription_id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
            logger.info(f"Subscription {subscription_id} deleted successfully.")
            return db_obj # Return the deleted object
        else:
            logger.warning(f"Attempted to delete non-existent subscription {subscription_id}")
            return None
    except Exception as e:
        logger.error(f"Error deleting subscription {subscription_id}: {e}", exc_info=True)
        await db.rollback()
        raise 