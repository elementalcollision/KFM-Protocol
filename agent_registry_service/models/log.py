from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base_class import Base
from .agent import LifecycleStateEnum # Import the Enum from agent model

class StateTransitionLog(Base):
    # __tablename__ will be generated as 'state_transition_logs' by Base class

    id = Column(BigInteger, primary_key=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.unique_id", ondelete="CASCADE"), nullable=False, index=True)
    previous_state = Column(
        SAEnum(LifecycleStateEnum, name="lifecycle_state_enum", create_type=False),
        nullable=True # Allow NULL for initial state
    )
    new_state = Column(
        SAEnum(LifecycleStateEnum, name="lifecycle_state_enum", create_type=False),
        nullable=False
    )
    transition_timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    triggering_agent_id = Column(UUID(as_uuid=True), nullable=True)
    triggering_user_id = Column(String(255), nullable=True)
    justification = Column(Text, nullable=True)

    # Define relationship back to Agent
    agent = relationship("Agent", back_populates="state_transitions") 