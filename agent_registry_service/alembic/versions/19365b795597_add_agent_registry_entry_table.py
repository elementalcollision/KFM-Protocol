"""Add agent_registry_entry table

Revision ID: 19365b795597
Revises: 
Create Date: 2025-05-02 20:45:16.243720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '19365b795597'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Creates the agent_registry_entries table and indexes."""
    op.create_table('agent_registry_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('state', sa.Enum('STABLE', 'EXPERIMENTAL', name='agentstate'), nullable=False),
        sa.Column('capabilities', postgresql.ARRAY(sa.String()), server_default='{}', nullable=False),
        sa.Column('metadata', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_registry_entries_type'), 'agent_registry_entries', ['type'], unique=False)
    op.create_index(op.f('ix_agent_registry_entries_state'), 'agent_registry_entries', ['state'], unique=False)
    op.create_index('ix_agent_registry_entry_type_state', 'agent_registry_entries', ['type', 'state'], unique=False)
    # Optional GIN index (uncomment if complex capability queries are common)
    # op.create_index('ix_agent_registry_entry_capabilities_gin', 'agent_registry_entries', ['capabilities'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    """Drops the agent_registry_entries table and indexes."""
    # op.drop_index('ix_agent_registry_entry_capabilities_gin', table_name='agent_registry_entries', postgresql_using='gin') # Optional GIN index
    op.drop_index('ix_agent_registry_entry_type_state', table_name='agent_registry_entries')
    op.drop_index(op.f('ix_agent_registry_entries_state'), table_name='agent_registry_entries')
    op.drop_index(op.f('ix_agent_registry_entries_type'), table_name='agent_registry_entries')
    op.drop_table('agent_registry_entries')
    # Downgrade enum type if necessary (often handled separately or requires raw SQL)
    # op.execute("DROP TYPE agentstate;")
