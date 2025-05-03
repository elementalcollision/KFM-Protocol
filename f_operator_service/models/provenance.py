from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
import uuid
from f_operator_service.db.base import Base
from sqlalchemy.orm import relationship
from typing import Optional

class ProvenanceRecord(Base):
    __tablename__ = "provenance_records"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False)
    operation_type = Column(String(50), nullable=False)  # e.g., 'adaptation', 'composition', 'experiment'
    operation_id = Column(PG_UUID(as_uuid=True), nullable=False)  # reference to specific operation record
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    parent_entity_id = Column(PG_UUID(as_uuid=True), nullable=True)
    parameters = Column(JSON, nullable=False)
    outcome_status = Column(String(20), nullable=False)  # 'success', 'failure', 'pending'
    outcome_details = Column(JSON, nullable=True)
    approval_status = Column(String(20), nullable=True)  # 'approved', 'rejected', 'pending', NULL for non-STABLE
    approver_id = Column(PG_UUID(as_uuid=True), nullable=True)
    approval_timestamp = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)

    # Optionally, add relationships to entity, user, etc. if those models exist 