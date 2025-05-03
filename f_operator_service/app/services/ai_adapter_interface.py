from abc import ABC, abstractmethod
from typing import Dict, Any
from uuid import UUID

from f_operator_service.schemas.ai_adaptation import (
    AIModelInfo,
    TrainingJobRequest,
    TrainingJobStatus,
    ModelMetadata
)

class AIAdapterInterface(ABC):
    """Abstract base class for AI model adaptation platform adapters."""

    @abstractmethod
    async def trigger_training_job(self, request: TrainingJobRequest) -> TrainingJobStatus:
        """Submit a training/fine-tuning job to the underlying platform."""
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> TrainingJobStatus:
        """Get the current status and metrics of a training job."""
        pass

    @abstractmethod
    async def get_model_metadata(self, model_id: str) -> ModelMetadata:
        """Retrieve metadata for a specific model version."""
        pass

    @abstractmethod
    async def register_model(self, metadata: ModelMetadata) -> AIModelInfo:
        """Register a newly trained model version with its metadata."""
        pass

    @abstractmethod
    async def validate_model(self, model_id: str) -> bool:
        """Perform basic validation checks on a model (e.g., can it be loaded?)."""
        pass

    # Potentially add methods for:
    # - Listing available models
    # - Deleting models/jobs
    # - Getting evaluation results

    # Potentially add methods for:
    # - Listing available models
    # - Deleting models/jobs
    # - Getting evaluation results 