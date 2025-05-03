from uuid import UUID, uuid4
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """
    Base message structure for all API communications.
    """
    request_id: UUID = Field(default_factory=uuid4, description="Unique identifier for this request", example="b3b1a2c4-5e6f-4d7a-8c9e-123456789abc")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp in UTC", example="2024-06-01T12:00:00Z")
    source_service: str = Field(..., description="Identifier of the calling service/client", example="api-gateway")
    target_service: str = Field(..., description="Identifier of the destination service", example="agent-registry")
    api_version: str = Field(default="v1", description="API version", example="v1")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class RequestData(BaseMessage):
    """
    Generic request data model with payload.
    """
    payload: Dict[str, Any] = Field(..., description="Request payload", example={"foo": "bar"})


class ResponseData(BaseMessage):
    """
    Generic response data model with payload.
    """
    payload: Dict[str, Any] = Field(..., description="Response payload", example={"result": "ok"})


class ErrorDetail(BaseModel):
    """
    Detailed error information for failed API requests.
    """
    field: Optional[str] = Field(None, description="Field that caused the error, if applicable", example="payload.foo")
    code: str = Field(..., description="Error code for programmatic handling", example="invalid_request")
    message: str = Field(..., description="Human-readable error message", example="The 'foo' field is required.")


class ErrorResponse(BaseMessage):
    """
    Standardized error response returned by the API.
    """
    error: ErrorDetail = Field(..., description="Error details")
    status_code: int = Field(..., description="HTTP status code", example=400) 