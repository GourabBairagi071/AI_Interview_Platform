"""add practice progress table

Revision ID: e3f4a5b6c7d8
Revises: 6be3d557720b
Create Date: 2026-10-01 19:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = '6be3d557720b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'practice_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', sa.String(length=64), nullable=False),
        sa.Column('solved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('bookmarked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_answer', sa.Text(), nullable=True),
        sa.Column('last_attempted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_id', 'question_id', name='uq_user_question_practice'),
    )
    op.create_index(op.f('ix_practice_progress_user_id'), 'practice_progress', ['user_id'], unique=False)
    op.create_index(op.f('ix_practice_progress_question_id'), 'practice_progress', ['question_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_practice_progress_question_id'), table_name='practice_progress')
    op.drop_index(op.f('ix_practice_progress_user_id'), table_name='practice_progress')
    op.drop_table('practice_progress')
