"""Add is_pinned, is_muted, is_deleted columns to conversations

Revision ID: 3b6e8f2c91a7
Revises: 9f1c2a7b4d3e
Create Date: 2026-06-23 00:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3b6e8f2c91a7'
down_revision: Union[str, Sequence[str], None] = '9f1c2a7b4d3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('is_muted', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.create_index(batch_op.f('ix_conversations_is_pinned'), ['is_pinned'], unique=False)
        batch_op.create_index(batch_op.f('ix_conversations_is_deleted'), ['is_deleted'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_conversations_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_conversations_is_pinned'))
        batch_op.drop_column('is_deleted')
        batch_op.drop_column('is_muted')
        batch_op.drop_column('is_pinned')
