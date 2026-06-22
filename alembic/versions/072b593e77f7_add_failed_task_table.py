"""Add failed_tasks table (Celery dead-letter queue)

Revision ID: 072b593e77f7
Revises: 66c9856bf81a
Create Date: 2026-06-22 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '072b593e77f7'
down_revision: Union[str, Sequence[str], None] = '66c9856bf81a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'failed_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('task_name', sa.String(length=255), nullable=False),
        sa.Column('task_id', sa.String(length=64), nullable=True),
        sa.Column('args_json', sa.JSON(), nullable=True),
        sa.Column('kwargs_json', sa.JSON(), nullable=True),
        sa.Column('exception_message', sa.Text(), nullable=True),
        sa.Column('traceback', sa.Text(), nullable=True),
        sa.Column('retries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='DEAD_LETTERED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_failed_tasks_task_name'), 'failed_tasks', ['task_name'], unique=False)
    op.create_index(op.f('ix_failed_tasks_task_id'), 'failed_tasks', ['task_id'], unique=False)
    op.create_index(op.f('ix_failed_tasks_status'), 'failed_tasks', ['status'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_failed_tasks_status'), table_name='failed_tasks')
    op.drop_index(op.f('ix_failed_tasks_task_id'), table_name='failed_tasks')
    op.drop_index(op.f('ix_failed_tasks_task_name'), table_name='failed_tasks')
    op.drop_table('failed_tasks')
