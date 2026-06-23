"""Create auto reply rules table

Revision ID: c6be37db20c1
Revises: 20260331_01
Create Date: 2026-04-05 01:52:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c6be37db20c1'
down_revision: Union[str, Sequence[str], None] = '20260331_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'auto_reply_rules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), sa.ForeignKey('workspaces.id'), nullable=False),
        sa.Column('trigger_keyword', sa.String(length=255), nullable=False),
        sa.Column('trigger_type', sa.String(length=50), nullable=False, server_default='exact'),
        sa.Column('response_text', sa.String(length=2000), nullable=False),
        sa.Column('attachment_path', sa.String(length=511), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('meta_account_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('auto_reply_rules')
