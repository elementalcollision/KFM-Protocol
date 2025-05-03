import uuid
from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base
from .enums import PromotionStatus, ApprovalStatus
# Assuming agent lifecycle states are defined elsewhere, possibly shared
# from agent_registry_service.models.agent import LifecycleStateEnum as AgentLevel # Example

class PromotionReview(Base):
    __tablename__ = "promotion_reviews"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Assuming agent ID is UUID, adjust if different
    agent_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True) 
    requested_level = Column(String, nullable=False) # Placeholder for AgentLevel enum
    current_status = Column(Enum(PromotionStatus), default=PromotionStatus.INITIATED, nullable=False, index=True)
    initiator_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    workflow_type = Column(String, default="default") # To select config
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    initiator = relationship("User") # Assuming User model exists
    approvals = relationship("PromotionApproval", back_populates="review", cascade="all, delete-orphan")
    # Add relationship to checklist items if needed

class PromotionApproval(Base):
    __tablename__ = "promotion_approvals"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(PG_UUID(as_uuid=True), ForeignKey("promotion_reviews.id", ondelete="CASCADE"), nullable=False)
    stakeholder_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False) # Specific role of this stakeholder in approval chain
    approval_order = Column(Integer, default=0) # For sequential approvals if needed
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    review = relationship("PromotionReview", back_populates="approvals")
    stakeholder = relationship("User") # Assuming User model exists

    # Indexes for query optimization
    __table_args__ = (
        Index("ix_promotion_approvals_review_id", "review_id"),
        Index("ix_promotion_approvals_stakeholder_id", "stakeholder_id"),
        Index("ix_promotion_approvals_status", "status"),
    ) 