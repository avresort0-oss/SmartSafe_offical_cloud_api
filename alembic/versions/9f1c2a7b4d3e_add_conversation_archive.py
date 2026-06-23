"""Add is_archived column to conversations (Inbox archive feature)

Revision ID: 9f1c2a7b4d3e
Revises: 072b593e77f7
Create Date: 2026-06-23 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9f1c2a7b4d3e'
down_revision: Union[str, Sequence[str], None] = '072b593e77f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.create_index(batch_op.f('ix_conversations_is_archived'), ['is_archived'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('conversations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_conversations_is_archived'))
        batch_op.drop_column('is_archived')
