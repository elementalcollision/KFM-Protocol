from sqlalchemy import Column, String, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base_class import Base

class AgentMetadata(Base):
    # __tablename__ will be generated as 'agent_metadata' by Base class

    id = Column(BigInteger, primary_key=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.unique_id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)
    value = Column(JSONB, nullable=True)
    value_type = Column(String(50), nullable=True)

    # Define relationship back to Agent
    agent = relationship("Agent", back_populates="metadata")

    # Note: UNIQUE constraint (agent_id, key) needs to be created via Alembic
    # migration script explicitly or using __table_args__ if preferred.
    # Example using __table_args__:
    # from sqlalchemy import UniqueConstraint
    # __table_args__ = (UniqueConstraint('agent_id', 'key', name='unique_agent_key'),) 