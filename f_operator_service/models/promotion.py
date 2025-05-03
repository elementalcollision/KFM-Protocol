from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from f_operator_service.db.base import Base
from enum import Enum as PyEnum
from datetime import datetime

class AgentLevel(PyEnum):
    EXPERIMENTAL = "EXPERIMENTAL"
    CANDIDATE = "CANDIDATE"
    STABLE = "STABLE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"

class PromotionStatus(PyEnum):
    INITIATED = "INITIATED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"

class EvidenceType(PyEnum):
    DOCUMENT = "DOCUMENT"
    LINK = "LINK"
    NOTE = "NOTE"
    OTHER = "OTHER"

class ChecklistItemStatus(PyEnum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    WAIVED = "WAIVED"

class PromotionReview(Base):
    __tablename__ = "promotion_reviews"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    requested_level = Column(Enum(AgentLevel), nullable=False)
    current_status = Column(Enum(PromotionStatus), default=PromotionStatus.INITIATED, nullable=False)
    initiator_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    evidence_items = relationship("PromotionEvidence", back_populates="review", cascade="all, delete-orphan")
    checklist_items = relationship(
        "PromotionChecklistItem",
        back_populates="review",
        cascade="all, delete-orphan"
    )
    # agent = relationship("Agent", back_populates="promotion_reviews") # Uncomment if Agent model exists
    # initiator = relationship("User") # Uncomment if User model exists

class PromotionEvidence(Base):
    __tablename__ = "promotion_evidence"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(PG_UUID(as_uuid=True), ForeignKey("promotion_reviews.id"), nullable=False)
    criteria_id = Column(PG_UUID(as_uuid=True), nullable=False)
    evidence_type = Column(Enum(EvidenceType), nullable=False)
    description = Column(Text, nullable=False)
    attachments = Column(Text, nullable=True)  # Store as JSON string or separate table if needed
    submitted_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    review = relationship("PromotionReview", back_populates="evidence_items")
    # submitter = relationship("User") # Uncomment if User model exists 

class PromotionChecklistItem(Base):
    __tablename__ = "promotion_checklist_items"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(PG_UUID(as_uuid=True), ForeignKey("promotion_reviews.id"), nullable=False)
    criteria_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Optional, for mapping to evidence/criteria
    description = Column(Text, nullable=False)
    required = Column(Boolean, default=True, nullable=False)
    status = Column(Enum(ChecklistItemStatus), default=ChecklistItemStatus.PENDING, nullable=False)
    evidence_submitted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    review = relationship("PromotionReview", back_populates="checklist_items")

# Update PromotionReview to include checklist_items relationship
PromotionReview.checklist_items = relationship(
    "PromotionChecklistItem",
    back_populates="review",
    cascade="all, delete-orphan"
) 