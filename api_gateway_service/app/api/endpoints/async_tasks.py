from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, HttpUrl
from typing import Dict, Any, Optional
from uuid import uuid4
from app.models.task import AsyncTask, TaskStatus
from app.services import task_store
from app.services.task_queue import enqueue_task
import asyncio
from app.core.config import get_settings
from app.schemas.base import ErrorResponse

router = APIRouter()

def get_api_key(request: Request):
    settings = get_settings()
    allowed_keys = settings.get_api_key_set()
    key = request.headers.get("x-api-key")
    if key not in allowed_keys:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

# In-memory event queue for SSE
sse_event_queue = asyncio.Queue()

def publish_task_event(event: dict):
    try:
        sse_event_queue.put_nowait(event)
    except Exception:
        pass

async def event_stream():
    while True:
        event = await sse_event_queue.get()
        yield f"data: {event}\n\n"

class AsyncJobRequest(BaseModel):
    """
    Request body for submitting an asynchronous job.
    """
    payload: Dict[str, Any] = Field(..., description="Input payload for the async job", example={"foo": "bar"})

class AsyncJobResponse(BaseModel):
    """
    Response returned after submitting an async job.
    """
    task_id: str = Field(..., alias="taskId", description="ID of the created async task", example="b3b1a2c4-5e6f-4d7a-8c9e-123456789abc")
    status: str = Field(..., description="Initial status of the async task", example="pending")

class AsyncTaskStatusResponse(BaseModel):
    """
    Response containing the status and result of an async task.
    """
    task_id: str = Field(..., alias="taskId", description="ID of the async task", example="b3b1a2c4-5e6f-4d7a-8c9e-123456789abc")
    status: str = Field(..., description="Current status of the async task", example="running")
    result: Any = Field(None, description="Result of the task if successful", example={"output": "value"})
    error: Optional[str] = Field(None, description="Error message if the task failed", example="Timeout occurred")
    retries: int = Field(0, description="Number of times the task has been retried", example=0)
    max_retries: int = Field(3, description="Maximum number of retries allowed", example=3)

class WebhookRegistrationRequest(BaseModel):
    """
    Request body for registering a webhook URL for async task completion notification.
    """
    webhook_url: HttpUrl = Field(..., description="HTTPS URL to notify when the async task completes", example="https://example.com/webhook")

@router.get("/tasks/events", responses={
    401: {"description": "Invalid or missing API key", "model": ErrorResponse}
})
async def sse_task_events(dep=Depends(get_api_key)):
    """
    Server-Sent Events (SSE) stream for async task status updates.

    Authentication: Requires a valid X-API-Key header.
    
    Returns a real-time event stream of task status changes for connected clients.
    
    Error Responses:
      - 401: Invalid or missing API key
    
    Example:
      curl -H "X-API-Key: <your-key>" http://localhost:8000/api/v1/tasks/events
    """
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.post("/async/{service}/{operation}", response_model=AsyncJobResponse, responses={
    400: {"description": "Service and operation are required", "model": ErrorResponse},
    401: {"description": "Invalid or missing API key", "model": ErrorResponse}
})
async def submit_async_job(service: str, operation: str, request: AsyncJobRequest, dep=Depends(get_api_key)):
    """
    Submit an asynchronous job for a backend service operation.

    Authentication: Requires a valid X-API-Key header.
    
    Creates a new async task, enqueues it for background processing, and returns the task ID and initial status.
    
    Error Responses:
      - 400: Service and operation are required
      - 401: Invalid or missing API key
    
    Example:
      curl -X POST -H "X-API-Key: <your-key>" -H "Content-Type: application/json" \
        -d '{"payload": {"foo": "bar"}}' \
        http://localhost:8000/api/v1/async/agent-registry/list_agents
    """
    # Basic validation (expand as needed)
    if not service or not operation:
        raise HTTPException(status_code=400, detail="Service and operation are required.")
    # Create AsyncTask
    task = AsyncTask()
    await task_store.create_task(task)
    await enqueue_task(str(task.id))
    publish_task_event({"taskId": str(task.id), "status": task.status})
    return AsyncJobResponse(taskId=str(task.id), status=task.status)

@router.get("/tasks/{task_id}", response_model=AsyncTaskStatusResponse, responses={
    401: {"description": "Invalid or missing API key", "model": ErrorResponse},
    404: {"description": "Task not found", "model": ErrorResponse}
})
async def get_task_status(task_id: str, dep=Depends(get_api_key)):
    """
    Get the status and result of an asynchronous task.

    Authentication: Requires a valid X-API-Key header.
    
    Returns the current status, result, error, and retry information for the specified task.
    
    Error Responses:
      - 401: Invalid or missing API key
      - 404: Task not found
    
    Example:
      curl -H "X-API-Key: <your-key>" http://localhost:8000/api/v1/tasks/<task_id>
    """
    task = await task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return AsyncTaskStatusResponse(
        taskId=str(task.id),
        status=task.status,
        result=task.result,
        error=task.error,
        retries=task.retries,
        max_retries=task.max_retries
    )

@router.post("/tasks/{task_id}/webhook", status_code=204, responses={
    400: {"description": "Webhook URL must use HTTPS", "model": ErrorResponse},
    401: {"description": "Invalid or missing API key", "model": ErrorResponse},
    404: {"description": "Task not found", "model": ErrorResponse}
})
async def register_webhook(task_id: str, req: WebhookRegistrationRequest, dep=Depends(get_api_key)):
    """
    Register a webhook URL for async task completion notification.

    Authentication: Requires a valid X-API-Key header.
    
    Registers a webhook URL to be called when the specified async task completes. Only HTTPS URLs are allowed.
    
    Error Responses:
      - 400: Webhook URL must use HTTPS
      - 401: Invalid or missing API key
      - 404: Task not found
    
    Example:
      curl -X POST -H "X-API-Key: <your-key>" -H "Content-Type: application/json" \
        -d '{"webhook_url": "https://example.com/webhook"}' \
        http://localhost:8000/api/v1/tasks/<task_id>/webhook
    """
    task = await task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Only allow HTTPS URLs
    if not str(req.webhook_url).startswith("https://"):
        raise HTTPException(status_code=400, detail="Webhook URL must use HTTPS.")
    task.webhook_url = str(req.webhook_url)
    await task_store.update_task(task)
    return None 