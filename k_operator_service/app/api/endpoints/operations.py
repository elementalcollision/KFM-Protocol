import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Body

# Project specifics
from k_operator_service.schemas.k_operations import (
    AgentOperationRequest,
    BatchOperationResponse,
    OperationStatus
)
from k_operator_service.clients.agent_registry import AgentRegistryClient, AgentRegistryError
from k_operator_service.app.security.deps import check_permission, get_current_active_user
# from k_operator_service.core.config import settings # If needed for client URL
from k_operator_service.events.publisher import EventPublisher, get_event_publisher, EventPublisherError
from k_operator_service.schemas.events import (
    AgentDeprecatedEvent,
    AgentArchivedEvent,
    AgentDeletionRequestedEvent
)
from k_operator_service.schemas.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency for Agent Registry Client (can be refined with settings)
async def get_agent_registry_client() -> AgentRegistryClient:
    # In a real app, you might configure the base URL via settings
    # return AgentRegistryClient(base_url=settings.AGENT_REGISTRY_SERVICE_URL)
    return AgentRegistryClient()

@router.post(
    "/deprecate",
    response_model=BatchOperationResponse,
    summary="Deprecate one or more agents",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(check_permission("k_operator:deprecate"))]
)
async def deprecate_agents(
    request: AgentOperationRequest = Body(...),
    client: AgentRegistryClient = Depends(get_agent_registry_client),
    publisher: EventPublisher = Depends(get_event_publisher)
):
    """
    Sets the state of the specified agents to DEPRECATED in the Agent Registry
    and publishes an event on success.

    Requires `k_operator:deprecate` permission.
    """
    results: List[OperationStatus] = []
    successful_ids: List[str] = []
    for agent_id in request.agent_ids:
        try:
            await client.set_agent_state(agent_id, "DEPRECATED", request.context)
            results.append(OperationStatus(agent_id=agent_id, success=True, message="State transitioned to DEPRECATED"))
            logger.info(f"Successfully set agent {agent_id} state to DEPRECATED.")
            successful_ids.append(agent_id)
        except AgentRegistryError as e:
            logger.warning(f"Failed to deprecate agent {agent_id}: {e.status_code} - {e.detail}")
            results.append(OperationStatus(agent_id=agent_id, success=False, message=f"Failed: {e.status_code} - {e.detail}"))
        except Exception as e:
            logger.error(f"Unexpected error deprecating agent {agent_id}: {e}", exc_info=True)
            results.append(OperationStatus(agent_id=agent_id, success=False, message=f"Unexpected server error: {e}"))

    # Publish events for successfully deprecated agents
    for agent_id in successful_ids:
        try:
            event = AgentDeprecatedEvent(agent_id=agent_id, context=request.context)
            await publisher.publish_event(event, routing_key="agent.deprecated")
        except EventPublisherError as e:
            # Log failure but don't fail the whole request, as state change succeeded
            logger.error(f"Failed to publish deprecation event for agent {agent_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error publishing deprecation event for agent {agent_id}: {e}", exc_info=True)

    # Determine overall status code - return 207 Multi-Status if any failed?
    # For now, return 200 OK and let client inspect results.
    return BatchOperationResponse(results=results)

@router.post(
    "/archive",
    response_model=BatchOperationResponse,
    summary="Archive one or more agents",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(check_permission("k_operator:archive"))]
)
async def archive_agents(
    request: AgentOperationRequest = Body(...),
    client: AgentRegistryClient = Depends(get_agent_registry_client),
    publisher: EventPublisher = Depends(get_event_publisher)
):
    """
    Sets the state of the specified agents to ARCHIVED in the Agent Registry
    and publishes an event on success.

    Requires `k_operator:archive` permission.
    Agents should typically be in DEPRECATED state first.
    """
    results: List[OperationStatus] = []
    successful_ids: List[str] = []
    for agent_id in request.agent_ids:
        try:
            # Note: Agent Registry's state machine should enforce valid transitions (e.g., DEPRECATED -> ARCHIVED)
            await client.set_agent_state(agent_id, "ARCHIVED", request.context)
            results.append(OperationStatus(agent_id=agent_id, success=True, message="State transitioned to ARCHIVED"))
            logger.info(f"Successfully set agent {agent_id} state to ARCHIVED.")
            successful_ids.append(agent_id)
        except AgentRegistryError as e:
            logger.warning(f"Failed to archive agent {agent_id}: {e.status_code} - {e.detail}")
            results.append(OperationStatus(agent_id=agent_id, success=False, message=f"Failed: {e.status_code} - {e.detail}"))
        except Exception as e:
            logger.error(f"Unexpected error archiving agent {agent_id}: {e}", exc_info=True)
            results.append(OperationStatus(agent_id=agent_id, success=False, message=f"Unexpected server error: {e}"))

    # Publish events for successfully archived agents
    for agent_id in successful_ids:
        try:
            event = AgentArchivedEvent(agent_id=agent_id, context=request.context)
            await publisher.publish_event(event, routing_key="agent.archived")
        except EventPublisherError as e:
            logger.error(f"Failed to publish archive event for agent {agent_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error publishing archive event for agent {agent_id}: {e}", exc_info=True)

    return BatchOperationResponse(results=results)

@router.delete(
    "/delete",
    response_model=BatchOperationResponse,
    summary="Delete one or more agents",
    status_code=status.HTTP_200_OK, # Or 207 Multi-Status? Stick with 200 for now.
    dependencies=[Depends(check_permission("k_operator:delete"))]
)
async def delete_agents(
    # Although DELETE typically uses path/query params, using a body
    # for consistency with other batch operations here.
    request: AgentOperationRequest = Body(...),
    client: AgentRegistryClient = Depends(get_agent_registry_client),
    publisher: EventPublisher = Depends(get_event_publisher),
    # Get current user for audit logging *after* permission check
    current_user: User = Depends(get_current_active_user)
):
    """
    Deletes the specified agents via the Agent Registry,
    logs the action for audit, and publishes an event on success.

    Requires `k_operator:delete` permission.
    Agents should typically be in ARCHIVED state first.
    """
    results: List[OperationStatus] = []
    successful_ids: List[str] = []
    # Audit log prefix for this batch operation
    audit_prefix = f"[AUDIT] User '{current_user.id}' attempted deletion for agents: {request.agent_ids}"
    logger.info(f"{audit_prefix} with context: {request.context}")

    for agent_id in request.agent_ids:
        try:
            logger.info(f"{audit_prefix} - Processing agent {agent_id}...")
            # Note: Agent Registry API should enforce preconditions (e.g., must be ARCHIVED)
            await client.delete_agent(agent_id)
            # Log success before adding to results
            success_msg = "Deletion initiated successfully via Agent Registry"
            logger.info(f"{audit_prefix} - SUCCESS for agent {agent_id}: {success_msg}")
            results.append(OperationStatus(agent_id=agent_id, success=True, message=success_msg))
            successful_ids.append(agent_id)
        except AgentRegistryError as e:
            # Log failure before adding to results
            error_msg = f"Deletion failed: {e.status_code} - {e.detail}"
            logger.warning(f"{audit_prefix} - FAILED for agent {agent_id}: {error_msg}")
            # Handle 404 as potentially 'already deleted' or 'not found' - still a failure from K-Op perspective?
            # Let's treat it as failure for now.
            results.append(OperationStatus(agent_id=agent_id, success=False, message=error_msg))
        except Exception as e:
            # Log unexpected error before adding to results
            error_msg = f"Unexpected server error: {e}"
            logger.error(f"{audit_prefix} - UNEXPECTED ERROR for agent {agent_id}: {error_msg}", exc_info=True)
            results.append(OperationStatus(agent_id=agent_id, success=False, message=error_msg))

    # Publish events for successfully deleted agents
    for agent_id in successful_ids:
        try:
            event = AgentDeletionRequestedEvent(
                agent_id=agent_id,
                context=request.context,
                triggering_user=current_user.id # Include user in event
            )
            # Use a more specific routing key if needed, e.g., agent.deletion.confirmed
            await publisher.publish_event(event, routing_key="agent.deleted")
        except EventPublisherError as e:
            logger.error(f"Failed to publish deletion event for agent {agent_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error publishing deletion event for agent {agent_id}: {e}", exc_info=True)

    return BatchOperationResponse(results=results) 