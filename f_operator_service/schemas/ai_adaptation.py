from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List, Literal
from uuid import UUID
from datetime import datetime

class AIModelInfo(BaseModel):
    """Basic information about an AI model."""
    model_id: str = Field(..., description="Unique identifier for the model (e.g., path, URI, internal ID)")
    framework: Literal["transformers", "sagemaker", "tensorflow", "pytorch", "custom"] = Field(..., description="ML Framework used")
    version: str = Field(..., description="Model version identifier")
    base_model_id: Optional[str] = Field(None, description="ID of the base model this was adapted from")
    creation_date: Optional[datetime] = Field(default_factory=datetime.utcnow)

class TrainingJobRequest(BaseModel):
    """Schema for requesting an AI model training/fine-tuning job."""
    model_id: str = Field(..., description="Identifier of the model to be trained/adapted")
    dataset_uri: str = Field(..., description="URI of the training dataset (e.g., S3 path, local path, dataset ID)")
    hyperparameters: Dict[str, Any] = Field(default_factory=dict, description="Hyperparameters for the training job")
    compute_config: Dict[str, Any] = Field(default_factory=dict, description="Configuration for compute resources (e.g., instance type, count)")
    validation_dataset_uri: Optional[str] = Field(None, description="URI of the validation dataset")
    output_location_uri: Optional[str] = Field(None, description="URI where the trained model should be saved")
    # Add framework specific parameters if needed

class TrainingJobStatus(BaseModel):
    """Schema representing the status of a training job."""
    job_id: str = Field(..., description="Unique identifier for the training job")
    status: Literal["PENDING", "QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "STOPPED"] = Field(..., description="Current status of the job")
    message: Optional[str] = Field(None, description="Optional message providing more details about the status")
    metrics: Optional[Dict[str, float]] = Field(default_factory=dict, description="Metrics collected during/after training (e.g., loss, accuracy)")
    output_model_id: Optional[str] = Field(None, description="Identifier of the resulting model if job succeeded")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class ModelMetadata(BaseModel):
    """Comprehensive metadata associated with a trained/adapted model."""
    model_info: AIModelInfo
    lineage: List[str] = Field(default_factory=list, description="List of parent model IDs tracing back to the original base model")
    training_job_id: Optional[str] = Field(None, description="ID of the job that produced this model version")
    training_params: Optional[TrainingJobRequest] = Field(None, description="Parameters used for the training job")
    evaluation_metrics: Optional[Dict[str, float]] = Field(default_factory=dict, description="Metrics from evaluating the model on a test set")
    deployment_status: Optional[str] = Field(None, description="Current deployment status (e.g., 'not_deployed', 'staging', 'production')")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict) 