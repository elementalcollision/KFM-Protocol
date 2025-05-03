from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    """
    Status of an asynchronous task.
    
    - pending: Task is queued and waiting to be processed.
    - running: Task is currently being processed.
    - success: Task completed successfully.
    - failed: Task failed after all retries.
    - cancelled: Task was cancelled by the user or system.
    """
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AsyncTask(BaseModel):
    """
    Represents an asynchronous background task submitted via the API.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the async task", example="b3b1a2c4-5e6f-4d7a-8c9e-123456789abc")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status of the task", example="pending")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation timestamp (UTC)", example="2024-06-01T12:00:00Z")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp (UTC)", example="2024-06-01T12:00:00Z")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Result of the task if successful", example={"output": "value"})
    error: Optional[str] = Field(default=None, description="Error message if the task failed", example="Timeout occurred")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL to notify on completion", example="https://example.com/webhook")
    retries: int = Field(default=0, description="Number of times the task has been retried", example=0)
    max_retries: int = Field(default=3, description="Maximum number of retries allowed", example=3)
    timeout_seconds: int = Field(default=30, description="Timeout in seconds for task execution", example=30)
    # Add additional metadata fields as needed

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        } 