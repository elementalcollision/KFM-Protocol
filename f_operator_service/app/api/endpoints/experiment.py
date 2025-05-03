import logging
from typing import List, Optional, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from f_operator_service import schemas
from f_operator_service.db.session import get_db
from f_operator_service.services.experiment_service import ExperimentService
from f_operator_service.services.feature_flag_service import FeatureFlagService
from f_operator_service.services.metrics_service import ExperimentMetricsService
from f_operator_service.services.sandbox_service import SandboxService
# from f_operator_service.app.api import deps # For security dependencies - adjust import path

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency Injection Setup (Example - adapt as needed) ---
# Placeholder dependencies - replace with actual instantiation/injection in main app setup
# Assume these services are instantiated elsewhere and provided via FastAPI's Depends

# Placeholder for actual service instantiation
# These functions would typically retrieve pre-configured singleton instances
# or create instances based on request scope. For simplicity, they are basic here.

# TODO: Replace these placeholders with proper dependency injection setup in main.py/core
async def get_feature_flag_service_dep() -> FeatureFlagService:
    # In a real app, this would likely get a singleton instance
    # Requires config source (e.g., settings) passed during instantiation
    return FeatureFlagService() 

async def get_metrics_service_dep() -> ExperimentMetricsService:
    # Needs configuration for metrics endpoint
    # settings = get_settings()
    # return ExperimentMetricsService(metrics_endpoint=settings.METRICS_API_ENDPOINT)
    return ExperimentMetricsService(metrics_endpoint="http://prometheus:9090") # Example placeholder

async def get_sandbox_service_dep() -> SandboxService:
    # Requires config source
    return SandboxService()

async def get_experiment_service_dep(
    db: AsyncSession = Depends(get_db),
    ff_service: FeatureFlagService = Depends(get_feature_flag_service_dep),
    metrics_service: ExperimentMetricsService = Depends(get_metrics_service_dep),
    sandbox_service: SandboxService = Depends(get_sandbox_service_dep)
) -> ExperimentService:
    # Pass db session per-request
    # TODO: Pass config/settings if needed by the service
    return ExperimentService(db, ff_service, metrics_service, sandbox_service)
# --- End Dependency Setup Example --- 


@router.post(
    "/", 
    response_model=schemas.ExperimentResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create Experiment Definition",
    description="Define a new experiment configuration.",
    tags=["Experiments"]
)
async def create_experiment_definition(
    experiment_in: schemas.ExperimentCreate,
    exp_service: ExperimentService = Depends(get_experiment_service_dep),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth
):
    logger.info(f"Received request to create experiment: {experiment_in.name}")
    try:
        experiment = await exp_service.create_experiment(experiment_in=experiment_in)
        return experiment
    except ValueError as ve:
         logger.warning(f"Validation error creating experiment '{experiment_in.name}': {ve}")
         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except Exception as e:
        logger.error(f"Error creating experiment '{experiment_in.name}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create experiment")


@router.get(
    "/", 
    response_model=List[schemas.ExperimentResponse], # TODO: Add pagination response schema
    summary="List Experiments",
    description="Retrieve a list of defined experiments, optionally filtering by status.",
    tags=["Experiments"]
)
async def list_experiment_definitions(
    status_filter: Optional[schemas.ExperimentStatusEnum] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    exp_service: ExperimentService = Depends(get_experiment_service_dep),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth
):
    logger.info(f"Listing experiments with status filter: {status_filter}")
    try:
        experiments, total = await exp_service.list_experiments(skip=skip, limit=limit, status=status_filter)
        # TODO: Return proper paginated response object including total
        return experiments 
    except Exception as e:
        logger.error(f"Error listing experiments: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list experiments")


@router.get(
    "/{experiment_id}", 
    response_model=schemas.ExperimentResponse,
    summary="Get Experiment Details",
    description="Retrieve the details of a specific experiment definition.",
    tags=["Experiments"]
)
async def get_experiment_definition(
    experiment_id: int,
    exp_service: ExperimentService = Depends(get_experiment_service_dep),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth
):
    logger.info(f"Getting details for experiment {experiment_id}")
    experiment = await exp_service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Experiment {experiment_id} not found")
    return experiment


@router.put(
    "/{experiment_id}", 
    response_model=schemas.ExperimentResponse,
    summary="Update Experiment Definition",
    description="Update the configuration of an experiment (only allowed in DRAFT state).",
    tags=["Experiments"]
)
async def update_experiment_definition(
    experiment_id: int,
    update_data: schemas.ExperimentUpdate,
    exp_service: ExperimentService = Depends(get_experiment_service_dep),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth + permissions
):
    logger.info(f"Updating experiment {experiment_id}")
    try:
        updated_experiment = await exp_service.update_experiment_config(experiment_id, update_data)
        if not updated_experiment:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Experiment {experiment_id} not found")
        return updated_experiment
    except ValueError as ve: # Handles state check errors
         logger.warning(f"Validation error updating experiment {experiment_id}: {ve}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating experiment {experiment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update experiment")

# --- Experiment Lifecycle Endpoints --- 

@router.post(
    "/{experiment_id}/start", 
    response_model=schemas.ExperimentResponse,
    summary="Start Experiment",
    description="Starts a defined experiment, activating its feature flag override.",
    tags=["Experiments"]
)
async def start_experiment(
    experiment_id: int,
    action_in: Optional[schemas.ExperimentActionRequest] = None, # Optional reason
    exp_service: ExperimentService = Depends(get_experiment_service_dep),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth + permissions
):
    logger.info(f"Attempting to start experiment {experiment_id}")
    try:
        reason = action_in.reason if action_in else None
        started_experiment = await exp_service.start_experiment(experiment_id, reason=reason)
        return started_experiment
    except ValueError as ve:
        logger.warning(f"Failed to start experiment {experiment_id}: {ve}")
        # Could be 404 or 400 based on error type
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error starting experiment {experiment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start experiment")

@router.post(
    "/{experiment_id}/pause", 
    response_model=schemas.ExperimentResponse,
    summary="Pause Experiment",
    description="Pauses a running experiment, deactivating its feature flag override.",
    tags=["Experiments"]
)
async def pause_experiment(
    experiment_id: int,
    action_in: Optional[schemas.ExperimentActionRequest] = None,
    exp_service: ExperimentService = Depends(get_experiment_service_dep),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth + permissions
):
    logger.info(f"Attempting to pause experiment {experiment_id}")
    try:
        reason = action_in.reason if action_in else None
        paused_experiment = await exp_service.pause_experiment(experiment_id, reason=reason)
        return paused_experiment
    except ValueError as ve:
        logger.warning(f"Failed to pause experiment {experiment_id}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error pausing experiment {experiment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to pause experiment")

@router.post(
    "/{experiment_id}/resume", 
    response_model=schemas.ExperimentResponse,
    summary="Resume Experiment",
    description="Resumes a paused experiment, reactivating its feature flag override.",
    tags=["Experiments"]
)
async def resume_experiment(
    experiment_id: int,
    action_in: Optional[schemas.ExperimentActionRequest] = None,
    exp_service: ExperimentService = Depends(get_experiment_service_dep),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth + permissions
):
    logger.info(f"Attempting to resume experiment {experiment_id}")
    try:
        reason = action_in.reason if action_in else None
        resumed_experiment = await exp_service.resume_experiment(experiment_id, reason=reason)
        return resumed_experiment
    except ValueError as ve:
        logger.warning(f"Failed to resume experiment {experiment_id}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error resuming experiment {experiment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to resume experiment")

@router.post(
    "/{experiment_id}/conclude", 
    response_model=schemas.ExperimentResponse,
    summary="Conclude Experiment",
    description="Concludes an experiment, analyzes results, and handles feature flag state.",
    tags=["Experiments"]
)
async def conclude_experiment(
    experiment_id: int,
    conclude_in: schemas.ExperimentConcludeRequest,
    exp_service: ExperimentService = Depends(get_experiment_service_dep),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth + permissions
):
    logger.info(f"Attempting to conclude experiment {experiment_id}")
    try:
        concluded_experiment = await exp_service.conclude_experiment(
            experiment_id,
            success=conclude_in.success, # Optional manual override
            reason=conclude_in.reason
        )
        return concluded_experiment
    except ValueError as ve:
        logger.warning(f"Failed to conclude experiment {experiment_id}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error concluding experiment {experiment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to conclude experiment")

@router.post(
    "/{experiment_id}/cancel", 
    response_model=schemas.ExperimentResponse,
    summary="Cancel Experiment",
    description="Cancels an experiment before it concludes naturally.",
    tags=["Experiments"]
)
async def cancel_experiment(
    experiment_id: int,
    action_in: schemas.ExperimentActionRequest, # Reason required
    exp_service: ExperimentService = Depends(get_experiment_service_dep),
    # current_user: User = Depends(deps.get_current_active_user) # TODO: Add auth + permissions
):
    logger.info(f"Attempting to cancel experiment {experiment_id}")
    if not action_in or not action_in.reason:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason is required to cancel an experiment.")
    try:
        cancelled_experiment = await exp_service.cancel_experiment(experiment_id, reason=action_in.reason)
        return cancelled_experiment
    except ValueError as ve:
        logger.warning(f"Failed to cancel experiment {experiment_id}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error cancelling experiment {experiment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cancel experiment")

# Optional: Endpoint to get experiment results/analysis
# @router.get("/{experiment_id}/results", tags=["Experiments"], ...) 