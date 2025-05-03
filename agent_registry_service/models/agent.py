import uuid
from sqlalchemy import Column, String, DateTime, text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base_class import Base # Relative import within the same package

# Define the Python Enum corresponding to the PostgreSQL ENUM type
import enum
class LifecycleStateEnum(str, enum.Enum):
    NEW = 'NEW'
    EXPERIMENTAL = 'EXPERIMENTAL'
    CANDIDATE = 'CANDIDATE'
    STABLE = 'STABLE'
    DEPRECATED = 'DEPRECATED'
    ARCHIVED = 'ARCHIVED'
    KILLED = 'KILLED'

class Agent(Base):
    # __tablename__ will be generated as 'agents' by Base class

    unique_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(255), nullable=False)
    version = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=True)
    maintainer = Column(String(255), nullable=True)
    lifecycle_state = Column(
        SAEnum(LifecycleStateEnum, name="lifecycle_state_enum", create_type=False),
        nullable=False,
        default=LifecycleStateEnum.NEW,
        server_default=LifecycleStateEnum.NEW.value # Use value for server default
    )
    creation_timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(), # Use func.now() for server-side default
        nullable=False
    )

    # Define relationships (lazy loaded by default)
    metadata = relationship("AgentMetadata", back_populates="agent", cascade="all, delete-orphan")
    state_transitions = relationship("StateTransitionLog", back_populates="agent", cascade="all, delete-orphan")

    # Note: CHECK constraints from SQL are typically enforced by validation
    # in Pydantic schemas (application layer) rather than directly in the model,
    # although SQLAlchemy has ways to add them if needed. 