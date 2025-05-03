import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum as SqlEnum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from .base_class import Base  # Assuming base_class.py is in the same directory


class AgentState(str, enum.Enum):
    STABLE = "STABLE"
    EXPERIMENTAL = "EXPERIMENTAL"
    # Add other states as needed: PENDING, OFFLINE, ERROR, DECOMMISSIONED


class AgentRegistryEntryModel(Base):
    # Table name will be generated as 'agent_registry_entries' by Base class
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False, index=True)
    state = Column(SqlEnum(AgentState), nullable=False, default=AgentState.EXPERIMENTAL, index=True)
    capabilities = Column(ARRAY(String), nullable=False, default=[], server_default='{}')
    metadata_ = Column("metadata", JSON, nullable=False, default={}, server_default='{}') # Use metadata_ to avoid potential conflicts
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Create indexes for common query patterns
    __table_args__ = (
        Index('ix_agent_registry_entry_type_state', 'type', 'state'),
        # Add GIN index for capabilities array if needed for complex array queries
        # Index('ix_agent_registry_entry_capabilities_gin', 'capabilities', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<AgentRegistryEntry(id={self.id}, type='{self.type}', state='{self.state}')>" 