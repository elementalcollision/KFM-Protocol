import asyncio
import logging
import json
from typing import Dict, Any

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from agent_registry_service import crud, schemas
from agent_registry_service.models import Subscription
from agent_registry_service.schemas import AgentRegistryEntry, SubscriptionCriteria, AgentState, CapabilityMatchType
from agent_registry_service.services.notification_service import NotificationService
# Assuming a session factory or dependency for DB access
from agent_registry_service.db.session import AsyncSessionLocal 

logger = logging.getLogger(__name__)

AGENT_EVENT_CHANNEL = "agent_registry_events"

class SubscriptionService:
    """Listens to agent change events and notifies subscribers."""

    def __init__(
        self, 
        redis_client: redis.Redis, 
        notification_service: NotificationService,
        db_session_factory = AsyncSessionLocal # Factory to create sessions
    ):
        self.redis_client = redis_client
        self.notification_service = notification_service
        self.db_session_factory = db_session_factory
        self._listener_task: Optional[asyncio.Task] = None
        logger.info("Initialized SubscriptionService.")

    async def start_listener(self):
        """Starts the background task listening to Redis Pub/Sub."""
        if self._listener_task and not self._listener_task.done():
            logger.warning("Listener task already running.")
            return
        logger.info(f"Starting Redis Pub/Sub listener on channel: {AGENT_EVENT_CHANNEL}")
        self._listener_task = asyncio.create_task(self._run_listener())
        self._listener_task.add_done_callback(self._listener_done_callback)

    def _listener_done_callback(self, task: asyncio.Task):
        """Callback to handle listener task completion/errors."""
        try:
            task.result() # Raise exception if task failed
            logger.info("Redis listener task finished gracefully.")
        except asyncio.CancelledError:
            logger.info("Redis listener task was cancelled.")
        except Exception:
            logger.exception("Redis listener task failed unexpectedly. Restarting...")
            # Simple restart logic - consider more robust handling (backoff, max retries)
            asyncio.create_task(self.start_listener()) 

    async def stop_listener(self):
        """Stops the background listener task."""
        if self._listener_task and not self._listener_task.done():
            logger.info("Stopping Redis Pub/Sub listener...")
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass # Expected
            logger.info("Redis Pub/Sub listener stopped.")
        self._listener_task = None

    async def _run_listener(self):
        """The core background task listening for events."""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(AGENT_EVENT_CHANNEL)
        logger.info(f"Subscribed to Redis channel: {AGENT_EVENT_CHANNEL}")
        
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10) # Timeout to allow cancellation check
                if message and message.get("type") == "message":
                    logger.debug(f"Received message: {message['data']}")
                    await self._process_event(message['data'])
                await asyncio.sleep(0.01) # Prevent tight loop if no messages
            except redis.ConnectionError:
                logger.error("Redis connection error in listener. Attempting to reconnect...")
                await asyncio.sleep(5) # Wait before retrying subscription
                try: 
                    await pubsub.subscribe(AGENT_EVENT_CHANNEL)
                    logger.info("Re-subscribed to Redis channel after connection error.")
                except Exception as e:
                    logger.error(f"Failed to re-subscribe after connection error: {e}")
                    await asyncio.sleep(10) # Longer wait if re-subscribe fails
            except Exception as e:
                logger.exception(f"Error in Redis listener loop: {e}")
                await asyncio.sleep(5) # Wait before continuing

    async def _process_event(self, message_data: str):
        """Process a single event message received from Redis."""
        try:
            event = json.loads(message_data)
            event_type = event.get("event_type")
            agent_id = event.get("agent_id")
            agent_data = event.get("agent_data") # Full data for create/update

            if not event_type or not agent_id:
                logger.warning(f"Received invalid event message: {message_data}")
                return

            # Fetch active subscriptions within a new DB session scope
            async with self.db_session_factory() as db:
                active_subscriptions = await crud.get_active_subscriptions(db)
                logger.debug(f"Processing event '{event_type}' for agent {agent_id} against {len(active_subscriptions)} subscriptions.")

                matched_subs = []
                for sub in active_subscriptions:
                    try:
                        # Parse subscription criteria
                        criteria = SubscriptionCriteria.model_validate(sub.criteria)
                        # Match event against criteria
                        if self._event_matches_criteria(event_type, agent_data, criteria):
                            matched_subs.append(sub)
                    except Exception as e:
                        logger.error(f"Error processing subscription {sub.id} criteria: {e}", exc_info=True)

                if matched_subs:
                    logger.info(f"Event matched {len(matched_subs)} subscriptions. Triggering notifications.")
                    # Trigger notifications concurrently
                    notification_tasks = [
                        self._send_notification_for_sub(sub, event)
                        for sub in matched_subs
                    ]
                    await asyncio.gather(*notification_tasks, return_exceptions=True) # Log errors from gather if needed

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON message: {message_data}")
        except Exception as e:
            logger.exception(f"Error processing event: {e}")

    def _event_matches_criteria(
        self, 
        event_type: str, 
        agent_data: Optional[Dict], 
        criteria: SubscriptionCriteria
    ) -> bool:
        """Check if an agent event matches the subscription criteria."""
        # Note: agent_data is None for delete events
        
        # Simple check first: Does this event type match?
        # Assuming event types like 'agent_created', 'agent_updated', 'agent_deleted'
        # This needs to be standardized with the publisher.
        # if event_type not in criteria.event_types: # Need event_types field in criteria schema
        #    return False 
            
        if event_type == "agent_deleted":
            # For deletions, we only need the ID, matching might depend on stored criteria
            # Simplest: notify all subscribers interested in deletions? 
            # Or maybe match based on *last known* state/type if feasible?
            # For now, assume if subscribed to deletions, match is true.
            return True # Needs refinement based on desired deletion notification logic
            
        if not agent_data:
            return False # Cannot match create/update without agent data
            
        # Filter by type
        if criteria.type and agent_data.get("type") != criteria.type:
            return False

        # Filter by state
        if criteria.state and agent_data.get("state") != criteria.state.value:
            return False

        # Filter by capabilities
        if criteria.capabilities:
            agent_caps = set(c.lower() for c in agent_data.get("capabilities", []))
            required_caps = set(c.lower() for c in criteria.capabilities)
            
            if criteria.capability_match_type == CapabilityMatchType.EXACT and not required_caps.issubset(agent_caps):
                return False
            if criteria.capability_match_type == CapabilityMatchType.ANY and required_caps.isdisjoint(agent_caps):
                return False
            # TODO: Implement fuzzy match if needed

        # Filter by metadata
        if criteria.metadata_filters:
            agent_meta = agent_data.get("metadata_", {}) # Assuming Pydantic model alias or direct field name
            for key, value in criteria.metadata_filters.items():
                if agent_meta.get(key) != value:
                    return False

        # If all checks passed
        return True

    async def _send_notification_for_sub(self, subscription: Subscription, event_payload: Dict):
        """Send notification for a specific subscription."""
        try:
            logger.info(f"Sending notification to {subscription.subscriber_url} for subscription {subscription.id}")
            await self.notification_service.send_webhook_notification(
                url=str(subscription.subscriber_url), # Ensure URL is string
                payload=event_payload # Send the original event payload
            )
            # Optionally update last_notified_at on success?
            # async with self.db_session_factory() as db:
            #    await crud.update_subscription(db, db_obj=subscription, obj_in={"last_notified_at": datetime.utcnow()})
        except Exception as e:
            logger.error(f"Failed to send notification for subscription {subscription.id} to {subscription.subscriber_url}: {e}")
            # Error is logged by NotificationService due to tenacity reraise=True


# Example usage (dependency injection pattern in main.py lifespan)
# async def lifespan(app: FastAPI):
#     # ... init redis, notification service ...
#     sub_service = SubscriptionService(redis_client, notification_service, AsyncSessionLocal)
#     await sub_service.start_listener()
#     app.state.subscription_service = sub_service 
#     yield
#     await sub_service.stop_listener()
#     # ... close redis ... 