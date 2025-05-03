from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, Boolean, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from f_operator_service.db.base import Base
from enum import Enum as PyEnum
from datetime import datetime
from .promotion import AgentLevel

class TemplateStatus(PyEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"

class CriteriaType(PyEnum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    OPTIONAL = "OPTIONAL"

class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_level = Column(Enum(AgentLevel), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(Enum(TemplateStatus), default=TemplateStatus.DRAFT, nullable=False)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    criteria = relationship("ChecklistCriteria", back_populates="template", cascade="all, delete-orphan")
    # creator = relationship("User") # Uncomment if User model exists

class ChecklistCriteria(Base):
    __tablename__ = "checklist_criteria"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(PG_UUID(as_uuid=True), ForeignKey("checklist_templates.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    criteria_type = Column(Enum(CriteriaType), default=CriteriaType.REQUIRED, nullable=False)
    order = Column(Integer, nullable=False)  # For maintaining criteria order within template
    evidence_required = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    template = relationship("ChecklistTemplate", back_populates="criteria")

    # Ensure criteria order is unique within a template
    __table_args__ = (
        UniqueConstraint('template_id', 'order', name='uix_template_criteria_order'),
    ) 