"""Add subscription table

Revision ID: 51a6e7a20318
Revises: 19365b795597
Create Date: 2025-05-02 22:30:19.308766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '51a6e7a20318'
down_revision: Union[str, None] = '19365b795597'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Creates the subscriptions table."""
    op.create_table('subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscriber_url', sa.String(), nullable=False, comment='Webhook URL to send notifications to'),
        sa.Column('criteria', sa.JSON(), nullable=False, comment='JSON object defining the discovery criteria for this subscription'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_notified_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp of the last successful notification'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_is_active'), 'subscriptions', ['is_active'], unique=False)
    # op.create_index('ix_subscription_subscriber_url', 'subscriptions', ['subscriber_url'], unique=False) # Optional index


def downgrade() -> None:
    """Drops the subscriptions table."""
    # op.drop_index('ix_subscription_subscriber_url', table_name='subscriptions') # Optional index
    op.drop_index(op.f('ix_subscriptions_is_active'), table_name='subscriptions')
    op.drop_table('subscriptions')
