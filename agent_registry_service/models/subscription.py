import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from agent_registry_service.db.base import Base # Adjust import based on actual base location


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscriber_url = Column(String, nullable=False, comment="Webhook URL to send notifications to")
    criteria = Column(JSON, nullable=False, comment="JSON object defining the discovery criteria for this subscription")
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True, comment="Timestamp of the last successful notification")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Optional: Add index on subscriber_url if needed for lookups
    # __table_args__ = (Index('ix_subscription_subscriber_url', 'subscriber_url'),)

    def __repr__(self):
        return f"<Subscription(id={self.id}, url='{self.subscriber_url}', active={self.is_active})>" 