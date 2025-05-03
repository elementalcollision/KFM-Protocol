from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from uuid import UUID
from datetime import datetime

class ProvenanceRecordBase(BaseModel):
    entity_id: UUID
    operation_type: str
    operation_id: UUID
    timestamp: Optional[datetime] = None
    user_id: UUID
    parent_entity_id: Optional[UUID] = None
    parameters: Dict[str, Any]
    outcome_status: str
    outcome_details: Optional[Dict[str, Any]] = None
    approval_status: Optional[str] = None
    approver_id: Optional[UUID] = None
    approval_timestamp: Optional[datetime] = None
    approval_notes: Optional[str] = None

class ProvenanceRecordCreate(ProvenanceRecordBase):
    pass

class ProvenanceRecordUpdate(BaseModel):
    outcome_status: Optional[str] = None
    outcome_details: Optional[Dict[str, Any]] = None
    approval_status: Optional[str] = None
    approver_id: Optional[UUID] = None
    approval_timestamp: Optional[datetime] = None
    approval_notes: Optional[str] = None

class ProvenanceRecordInDBBase(ProvenanceRecordBase):
    id: UUID
    class Config:
        from_attributes = True

class ProvenanceRecord(ProvenanceRecordInDBBase):
    pass 