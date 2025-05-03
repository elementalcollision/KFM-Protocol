from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from uuid import UUID
import logging
from pathlib import Path
from datetime import datetime
import uuid as uuid_pkg

# Assuming GitService is in the same directory or properly discoverable
from .git_service import GitService, GitServiceError 
from f_operator_service.core.config import get_settings # Need settings for GitService
from .ai_adapter_interface import AIAdapterInterface # Import AI interface
from .ai_adapters import HuggingFaceAdapter, SagemakerAdapter # Import placeholders
from f_operator_service.schemas.ai_adaptation import TrainingJobRequest # Import schema
from .agent_registry_client import AgentRegistryClient
from .policy_engine_client import PolicyEngineClient

logger = logging.getLogger(__name__)

# Placeholder mapping of AI frameworks to adapter classes
# TODO: Implement proper dependency injection
AI_ADAPTERS: Dict[str, Type[AIAdapterInterface]] = {
    "transformers": HuggingFaceAdapter,
    "sagemaker": SagemakerAdapter,
    # Add other frameworks here
}

class AdaptationInterface(ABC):
    """Abstract base class for different adaptation strategies."""
    # Inject settings potentially, or specific services
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def adapt(self, agent_id: UUID, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the adaptation operation.

        Args:
            agent_id: The ID of the agent to adapt.
            parameters: Specific parameters for this adaptation type.

        Returns:
            A dictionary containing the result of the adaptation (e.g., new version ID, status).
        """
        pass

class CodeAdaptationService(AdaptationInterface):
    """Service for code-based adaptation using Git and policy validation."""
    def __init__(self):
        super().__init__()
        settings = get_settings()
        self.git_service = GitService(settings)
        self.agent_registry_client = AgentRegistryClient(
            base_url=settings.AGENT_REGISTRY_URL,
            auth_token=settings.AGENT_REGISTRY_TOKEN
        )
        self.policy_engine_client = PolicyEngineClient(
            base_url=settings.POLICY_ENGINE_URL,
            auth_token=settings.POLICY_ENGINE_TOKEN
        )

    async def adapt(self, agent_id: UUID, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Fetch agent details
        agent = await self.agent_registry_client.get_agent(str(agent_id))
        if not agent:
            return {"error": f"Agent {agent_id} not found in registry."}

        # 2. Validate adaptation with Policy Engine (optional)
        validation_request = {
            "operation": "adaptation",
            "agent_id": str(agent_id),
            "parameters": parameters
        }
        policy_result = await self.policy_engine_client.validate_operation(validation_request)
        if not policy_result.get("allowed", True):
            return {"error": "Adaptation not allowed by policy engine.", "policy_result": policy_result}

        # 3. Proceed with adaptation (placeholder)
        # ... existing adaptation logic ...
        return {"status": "adaptation started", "agent": agent, "policy_result": policy_result}

class AIModelAdaptationService(AdaptationInterface):
    """Service for AI model adaptation (e.g., fine-tuning, retraining)."""
    def __init__(self):
        super().__init__()
        # Store instantiated adapters - could be done via dependency injection
        self.adapters: Dict[str, AIAdapterInterface] = { 
            name: adapter_cls() for name, adapter_cls in AI_ADAPTERS.items()
        }
        
    async def adapt(self, agent_id: UUID, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Triggers an AI model training/adaptation job via the appropriate adapter."""
        framework = parameters.get("framework")
        model_id_to_adapt = parameters.get("model_id") # Model ID to adapt/fine-tune
        dataset_uri = parameters.get("dataset_uri")
        hyperparams = parameters.get("hyperparameters", {})
        compute_config = parameters.get("compute_config", {})
        # ... extract other relevant params ...

        if not framework or framework not in self.adapters:
            raise ValueError(f"Unsupported or missing AI framework specified: {framework}")
        if not model_id_to_adapt:
             raise ValueError("Missing required parameter: model_id")
        if not dataset_uri:
            raise ValueError("Missing required parameter: dataset_uri")
            
        adapter = self.adapters[framework]
        self.logger.info(f"Using {framework} adapter for AI model adaptation of agent {agent_id}")

        try:
            # Create the training job request from parameters
            training_request = TrainingJobRequest(
                model_id=model_id_to_adapt,
                dataset_uri=dataset_uri,
                hyperparameters=hyperparams,
                compute_config=compute_config,
                # Pass other relevant parameters from adaptation request
                validation_dataset_uri=parameters.get("validation_dataset_uri"),
                output_location_uri=parameters.get("output_location_uri")
            )
            
            # Trigger the job via the adapter
            job_status = await adapter.trigger_training_job(training_request)
            self.logger.info(f"Triggered AI training job {job_status.job_id} with status {job_status.status}")

            # Return job ID and initial status
            return {
                "status": "AI_ADAPTATION_STARTED",
                "job_id": job_status.job_id,
                "initial_job_status": job_status.status,
                "message": job_status.message
            }
            
        except Exception as e:
            self.logger.error(f"Failed to trigger AI adaptation for agent {agent_id} using {framework}: {e}", exc_info=True)
            return {"status": "FAILED", "error": f"Failed to trigger {framework} job: {str(e)}"}

# Add other interface implementations as needed (e.g., for configuration changes, data structure evolution) 