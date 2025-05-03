import asyncio
import logging
import json
import aio_pika
from typing import Optional, Callable, Coroutine, Any, List

from resource_manager_service.core.config import settings
# Import Kubernetes client and exceptions
from .k8s_client import KubernetesClient, K8sResourceNotFoundError, K8sClientError

logger = logging.getLogger(__name__)

# Define the standard label key
AGENT_ID_LABEL = "kfm.aiprotocol.com/agent-id"

class EventListener:
    """Listens for KFM events and triggers resource management actions."""

    def __init__(self, k8s_client: KubernetesClient): # Inject K8s client
        self.connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None
        self.queue: Optional[aio_pika.abc.AbstractQueue] = None
        self.consumer_tag: Optional[str] = None
        self._is_running = False
        self.k8s_client = k8s_client # Store injected client

    async def connect(self):
        """Establishes connection to RabbitMQ and sets up consumer."""
        try:
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10) # Adjust prefetch as needed

            exchange = await self.channel.declare_exchange(
                settings.KFM_EVENT_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
            )

            self.queue = await self.channel.declare_queue(
                settings.RESOURCE_EVENT_QUEUE, durable=True
            )

            await self.queue.bind(exchange, routing_key=settings.RESOURCE_EVENT_ROUTING_KEY)
            logger.info(f"Connected to RabbitMQ. Exchange '{settings.KFM_EVENT_EXCHANGE}' declared. Queue '{settings.RESOURCE_EVENT_QUEUE}' declared and bound with key '{settings.RESOURCE_EVENT_ROUTING_KEY}'.")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ or setup consumer: {e}", exc_info=True)
            await self.disconnect() # Ensure cleanup if connection fails
            raise

    async def disconnect(self):
        """Closes the RabbitMQ connection gracefully."""
        logger.info("Disconnecting from RabbitMQ...")
        if self.channel and not self.channel.is_closed:
            try:
                await self.channel.close()
                logger.info("RabbitMQ channel closed.")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ channel: {e}", exc_info=True)
        if self.connection and not self.connection.is_closed:
            try:
                await self.connection.close()
                logger.info("RabbitMQ connection closed.")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}", exc_info=True)
        self.connection = None
        self.channel = None
        self.queue = None
        self.consumer_tag = None

    async def _handle_agent_archived(self, agent_id: str, namespace: str = "default"):
        """Handles the AgentArchived event by scaling down Deployments/StatefulSets."""
        # Assuming agent resources live in a predictable namespace or we get it from event/registry
        # For now, using "default" as a placeholder - THIS NEEDS ADJUSTMENT
        target_namespace = namespace # TODO: Determine the actual namespace
        
        # Attempt to scale down Deployment (common case)
        deployment_name = f"agent-{agent_id}" # Assuming a naming convention
        try:
            # Note: k8s client methods are blocking, run in executor for async context
            # This requires adapting the K8sClient methods or running this handler differently.
            # For simplicity here, assuming the k8s_client methods were made async properly.
            await self.k8s_client.patch_namespaced_deployment_scale(
                name=deployment_name, 
                namespace=target_namespace, 
                replicas=0
            )
            logger.info(f"Scaled down Deployment '{deployment_name}' for archived agent {agent_id}")
        except K8sResourceNotFoundError:
            logger.warning(f"Deployment '{deployment_name}' not found for agent {agent_id}. Checking StatefulSet...")
            # TODO: Attempt to scale down StatefulSet if Deployment wasn't found
            pass
        except K8sClientError as e:
            logger.error(f"Failed to scale down Deployment '{deployment_name}' for agent {agent_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error handling AgentArchived for {agent_id}: {e}", exc_info=True)

    async def _handle_agent_killed(self, agent_id: str, namespace: str = "default"):
        """Handles the AgentKilled event by deleting associated resources."""
        target_namespace = namespace # TODO: Determine actual namespace
        label_selector = f"{AGENT_ID_LABEL}={agent_id}"
        logger.warning(f"Deleting resources for killed agent {agent_id} in namespace {target_namespace} with label selector: {label_selector}")

        resources_to_delete = {
            "Deployment": self.k8s_client.apps_v1_api.list_namespaced_deployment,
            "StatefulSet": self.k8s_client.apps_v1_api.list_namespaced_stateful_set, # If agents can be StatefulSets
            "Service": self.k8s_client.core_v1_api.list_namespaced_service,
            "ConfigMap": self.k8s_client.core_v1_api.list_namespaced_config_map,
            "Secret": self.k8s_client.core_v1_api.list_namespaced_secret,
            "PersistentVolumeClaim": self.k8s_client.core_v1_api.list_namespaced_persistent_volume_claim # TODO: Add policy check for PVC deletion
        }
        
        delete_functions = {
            "Deployment": self.k8s_client.delete_namespaced_deployment,
            "StatefulSet": self.k8s_client.apps_v1_api.delete_namespaced_stateful_set,
            "Service": self.k8s_client.core_v1_api.delete_namespaced_service,
            "ConfigMap": self.k8s_client.core_v1_api.delete_namespaced_config_map,
            "Secret": self.k8s_client.core_v1_api.delete_namespaced_secret,
            "PersistentVolumeClaim": self.k8s_client.core_v1_api.delete_namespaced_persistent_volume_claim
        }

        for kind, list_func in resources_to_delete.items():
            try:
                # Note: list functions are blocking, need proper async handling
                # Assuming list functions were adapted or run in executor
                res_list = await asyncio.to_thread(list_func, namespace=target_namespace, label_selector=label_selector)
                for item in res_list.items:
                    item_name = item.metadata.name
                    delete_func = delete_functions.get(kind)
                    if delete_func:
                        logger.info(f"Deleting {kind} '{item_name}' for agent {agent_id}")
                        try:
                            # Note: delete functions are blocking
                            await asyncio.to_thread(
                                delete_func, 
                                name=item_name, 
                                namespace=target_namespace, 
                                body=client.V1DeleteOptions(propagation_policy='Foreground')
                            )
                        except ApiException as e:
                            if e.status == 404:
                                logger.warning(f"{kind} '{item_name}' already deleted.")
                            else:
                                logger.error(f"Failed to delete {kind} '{item_name}: {e.status} - {e.reason}")
                        except Exception as e_inner:
                            logger.error(f"Unexpected error deleting {kind} '{item_name}: {e_inner}", exc_info=True)
                    else:
                        logger.warning(f"No delete function found for kind '{kind}'")
            except ApiException as e:
                logger.error(f"API Error listing {kind}s for agent {agent_id}: {e.status} - {e.reason}")
            except Exception as e:
                logger.error(f"Unexpected error listing {kind}s for agent {agent_id}: {e}", exc_info=True)

    async def _process_message(self, message: aio_pika.abc.AbstractIncomingMessage):
        """Processes a single incoming message."""
        async with message.process(): # Auto-ack on success, nack on exception
            try:
                body = message.body.decode()
                logger.debug(f"Received message: {body}")
                event_data = json.loads(body)
                
                event_type = event_data.get("event_type")
                agent_id = event_data.get("agent_id")

                if not event_type or not agent_id:
                    logger.warning(f"Received invalid message format: {body}")
                    return # Acknowledge and ignore

                # --- Reclamation Logic --- 
                if event_type == "AgentArchived":
                    await self._handle_agent_archived(agent_id)
                elif event_type == "AgentKilled":
                    await self._handle_agent_killed(agent_id)
                else:
                    logger.debug(f"Ignoring event type: {event_type}")

            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON message body: {message.body}")
                # Message will be nack'd by context manager
            except Exception as e:
                logger.error(f"Error processing message for agent {agent_id if 'agent_id' in locals() else 'unknown'}: {e}", exc_info=True)
                # Message will be nack'd by context manager

    async def start_consuming(self):
        """Starts consuming messages from the queue."""
        if not self.channel or not self.queue:
            logger.error("Cannot start consuming, channel or queue not initialized.")
            return
        
        if self._is_running:
            logger.warning("Consumer already running.")
            return

        try:
            logger.info(f"Starting event consumer on queue '{settings.RESOURCE_EVENT_QUEUE}'")
            self.consumer_tag = await self.queue.consume(self._process_message)
            self._is_running = True
            logger.info("Event consumer started.")
            # Keep running until stopped
            await asyncio.Future() 
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled.")
        except Exception as e:
            logger.error(f"Event consumer error: {e}", exc_info=True)
        finally:
            await self.stop_consuming()

    async def stop_consuming(self):
        """Stops the message consumer gracefully."""
        if self.consumer_tag and self.channel and not self.channel.is_closed:
            logger.info("Stopping event consumer...")
            try:
                await self.channel.cancel(self.consumer_tag)
                logger.info("Event consumer stopped.")
            except Exception as e:
                logger.error(f"Error stopping consumer: {e}", exc_info=True)
        self.consumer_tag = None
        self._is_running = False
        await self.disconnect() # Also disconnect when stopping consumer

    def is_running(self) -> bool:
        return self._is_running 