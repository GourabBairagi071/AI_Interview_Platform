"""add anti_cheating_events table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-02 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'anti_cheating_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interview_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), server_default='LOW', nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('duration', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence_reference', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anti_cheating_events_interview_id'), 'anti_cheating_events', ['interview_id'], unique=False)
    op.create_index(op.f('ix_anti_cheating_events_event_type'), 'anti_cheating_events', ['event_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_anti_cheating_events_event_type'), table_name='anti_cheating_events')
    op.drop_index(op.f('ix_anti_cheating_events_interview_id'), table_name='anti_cheating_events')
    op.drop_table('anti_cheating_events')
