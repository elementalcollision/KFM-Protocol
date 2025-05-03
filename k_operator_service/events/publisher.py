import asyncio
import logging
import json
from typing import Dict, Any, Optional

import aio_pika
from aio_pika import Message, ExchangeType
from pydantic import BaseModel

# Placeholder for RabbitMQ connection URL (replace with actual config loading)
# from k_operator_service.core.config import settings
RABBITMQ_URL = "amqp://guest:guest@localhost/" # Placeholder
KFM_EVENTS_EXCHANGE = "kfm_events"

logger = logging.getLogger(__name__)

class EventPublisherError(Exception):
    """Custom exception for event publishing errors."""
    pass

class EventPublisher:
    """Handles connecting to RabbitMQ and publishing events."""
    _connection: Optional[aio_pika.RobustConnection] = None
    _channel: Optional[aio_pika.Channel] = None
    _exchange: Optional[aio_pika.Exchange] = None

    def __init__(self, rabbitmq_url: str = RABBITMQ_URL, exchange_name: str = KFM_EVENTS_EXCHANGE):
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name

    async def connect(self):
        """Establishes connection to RabbitMQ and declares the exchange."""
        if self._connection and not self._connection.is_closed:
            logger.debug("Already connected to RabbitMQ.")
            return

        try:
            logger.info(f"Connecting to RabbitMQ at {self.rabbitmq_url}...")
            self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self._channel = await self._connection.channel()
            # Declare a topic exchange (flexible routing based on routing key)
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True # Ensure exchange survives broker restarts
            )
            logger.info(f"Connected to RabbitMQ and declared exchange '{self.exchange_name}'.")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}", exc_info=True)
            self._connection = None
            self._channel = None
            self._exchange = None
            raise EventPublisherError(f"RabbitMQ connection failed: {e}") from e

    async def close(self):
        """Closes the RabbitMQ connection gracefully."""
        if self._connection and not self._connection.is_closed:
            logger.info("Closing RabbitMQ connection...")
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._exchange = None
            logger.info("RabbitMQ connection closed.")

    async def publish_event(self, event: BaseModel, routing_key: str):
        """Publishes a Pydantic model as a JSON message to the exchange.

        Args:
            event: The Pydantic model instance representing the event.
            routing_key: The routing key for the message (e.g., 'agent.deprecated').
        """
        if not self._connection or self._connection.is_closed or not self._channel or not self._exchange:
            logger.warning("Attempted to publish event while not connected. Trying to reconnect...")
            try:
                await self.connect()
                if not self._exchange: # Check again after reconnect attempt
                     raise EventPublisherError("Cannot publish event: Connection or exchange not available.")
            except EventPublisherError as e:
                 logger.error(f"Failed to reconnect before publishing: {e}")
                 raise # Re-raise the specific error

        try:
            # Serialize the Pydantic model to JSON
            # Use pydantic's json method with default=str for non-serializable types like datetime
            message_body = event.model_dump_json().encode()

            message = Message(
                body=message_body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT # Make messages persistent
            )

            logger.debug(f"Publishing event with routing key '{routing_key}' to exchange '{self.exchange_name}'")
            await self._exchange.publish(message, routing_key=routing_key)
            logger.info(f"Event '{routing_key}' published successfully.")

        except Exception as e:
            logger.error(f"Failed to publish event: {e}", exc_info=True)
            # Depending on the error, might want to retry or raise
            raise EventPublisherError(f"Failed to publish event: {e}") from e

# --- Dependency for FastAPI --- #

# Global instance (or manage via app state/lifespan)
publisher = EventPublisher()

async def lifespan(app):
    # Connect on startup
    await publisher.connect()
    yield
    # Disconnect on shutdown
    await publisher.close()

async def get_event_publisher() -> EventPublisher:
    """FastAPI dependency to get the event publisher instance."""
    # Basic check, assumes lifespan management handles connection
    if not publisher._connection or publisher._connection.is_closed:
         logger.warning("Event publisher connection not ready, attempting connection...")
         try:
            # Attempt connection if not ready (e.g., if lifespan failed)
            await publisher.connect()
         except Exception:
             logger.error("Failed to establish connection in dependency")
             # Decide how to handle this - raise 503? Return None and let endpoint handle?
             # For now, let's raise an error so the request fails clearly
             raise HTTPException(status_code=503, detail="Event publishing service unavailable")

    return publisher 